# InsightHub Threat Model — STRIDE / OWASP LLM Top 10

## Scope, assets, and trust boundaries

InsightHub accepts browser/API questions and uploaded documents, ingests them asynchronously,
retrieves ready chunks from PostgreSQL, and sends prompts to a configured LLM provider. The
optional LiteLLM gateway handles virtual keys, provider routing, budgets, and telemetry.
ChatOps accepts Slack events, queues authenticated events through Redis/ARQ, and calls
configured Kubernetes or Prometheus MCP processes. The principal trust boundaries are:

- browser or Slack → API / ChatOps ingress;
- uploaded document corpus → retrieved RAG context → model;
- API → LLM provider or LiteLLM;
- ChatOps worker → configured MCP process → Kubernetes/Prometheus;
- services → PostgreSQL, Redis, logs, and secret injection mechanism.

Assets include user/document data and PII, prompts and model responses, provider and Slack
credentials, Kubernetes permissions, queue integrity/availability, and provider budget.
Impact ratings below describe plausible production impact, not a claim that an attack has
occurred. “Implemented” means code/configuration exists in this repository; it does not
prove that the control is enabled or effective in a deployed environment. Runtime evidence
must be collected separately.

| Threat | STRIDE categories | OWASP LLM mapping |
|---|---|---|
| Poisoned RAG document | Tampering, Elevation of Privilege | LLM01 Prompt Injection |
| Direct jailbreak / prompt leakage | Spoofing, Information Disclosure | LLM01 Prompt Injection; LLM07 System Prompt Leakage |
| PII exfiltration | Information Disclosure | LLM02 Sensitive Information Disclosure |
| ChatOps infrastructure mutation | Spoofing, Tampering, Elevation of Privilege | LLM06 Excessive Agency |
| Financial denial of service | Denial of Service | LLM10 Unbounded Consumption |
| Dependency/MCP compromise | Tampering, Elevation of Privilege | LLM supply-chain risk (OWASP LLM Top 10) |
| Slack replay / ingress abuse | Spoofing, Tampering, Denial of Service | Supporting control for LLM01/LLM06 |

## Threat 1 — Indirect prompt injection via poisoned RAG document

### Description

An uploaded document contains instructions intended for the model, such as requests to
ignore policy, reveal other data, or claim actions were taken. Retrieved text is placed in
the same model request as the user's question and may influence generation.

### Impact Level

**HIGH**

### Attack Vector

An attacker with document-upload access submits a poisoned TXT, Markdown, or PDF, waits for
ingestion to mark it ready, and asks a query likely to retrieve the malicious chunk. The
fixture at `security/sample-docs/poisoned-doc.md` demonstrates a test payload; it is not
evidence of a live attack or successful retrieval.

### Mitigation Strategy

- `api/app/services/llm.py` separates retrieved text under `<context>` and the question
  under `<user_query>`, escapes interpolated text, and tells the model the context is
  untrusted data, not instructions. This is a prompt-layer mitigation, not a security
  boundary by itself.
- Upload validation and asynchronous ingestion bound file types/size and only retrieve
  documents in `ready` state (`api/app/routers/documents.py`,
  `api/app/services/retrieval.py`). They do not detect every malicious instruction.
- `security/promptfooconfig.yaml` declares indirect-injection/RAG-poisoning probes. A test
  requires explicitly ingesting the fixture and running the red-team evaluation; the
  config alone is not a passing result.
- No RAG text is granted tool execution authority by the API path. Keep upload access
  restricted and treat all retrieved content as untrusted.

Residual risk: there is no deterministic classifier that guarantees poisoned document
content is harmless. Retrieved context is also included in the API response, so callers
must have appropriate document access controls before using sensitive corpora.

## Threat 2 — Direct jailbreak and system-prompt leakage

### Description

A user crafts a question to override system instructions, extract hidden prompt text, or
coerce the model into disclosing operational details.

### Impact Level

**HIGH**

### Attack Vector

An attacker calls `POST /chat` with direct jailbreak phrases, Unicode lookalikes, invisible
characters, or multi-turn extraction attempts designed to bypass simple pattern matching.

### Mitigation Strategy

- `api/app/core/guardrails.py` applies NFKC normalization, removes Unicode control/format
  characters (while retaining ordinary newlines/tabs), rejects configured direct-injection
  phrases, and checks input before retrieval/provider invocation.
- `api/app/services/llm.py` instructs the model not to reveal system prompts or credentials.
- An optional HTTP guardrail adapter is available through `GUARDRAIL_MODE=http` and
  `GUARDRAIL_URL`; failures/non-allow decisions fail closed. The default is local mode, so
  an external Bedrock/NeMo/Llama Guard service is **not** assumed to be deployed.
- `security/promptfooconfig.yaml` contains jailbreak and prompt-extraction evaluations;
  findings are not considered resolved until the evaluation is actually run and reviewed.

Residual risk: phrase matching and prompt wording cannot cover all jailbreaks. The optional
external guardrail has no deployment evidence in this repository state.

## Threat 3 — PII and sensitive-data exfiltration in chat output

### Description

The model may repeat sensitive content present in retrieved chunks, expose another user's
data, or return PII/credentials in its answer or context fields.

### Impact Level

**CRITICAL**

### Attack Vector

A user asks for verbatim content, uses prompt injection to elicit sensitive fields, or
retrieves a document containing personal data. A direct `/chat` response can include both
`answer` and retrieved `contexts`.

### Mitigation Strategy

- `api/app/core/guardrails.py` rejects generated answers matching a limited regex for
  email addresses, SSN-shaped values, or payment-card-shaped digit strings. This is
  implemented output screening, not comprehensive PII detection.
- `api/app/services/llm.py` directs the model not to reveal PII or credentials; this is
  defense in depth only.
- The API maps provider failures to fixed service errors rather than returning raw provider
  exceptions (`api/app/core/errors.py`, `api/app/core/providers.py`).
- `security/promptfooconfig.yaml` includes direct/session PII probes, but the config does
  not prove a clean evaluation.

Residual risk is **high**: the regex does not identify arbitrary sensitive business data,
does not reliably catch all token formats, and is applied to the generated answer—not the
returned `contexts` list. Document authorization/classification, data minimization, and
provider retention controls remain necessary before production use.

## Threat 4 — Unauthorized infrastructure mutation via ChatOps Bot

### Description

An unauthorized Slack user or compromised bot path attempts to change Kubernetes or other
infrastructure, including by exploiting broad MCP capabilities or bypassing approval.

### Impact Level

**CRITICAL**

### Attack Vector

An attacker forges/replays Slack events, abuses an authorized user's identity, crafts a
mutation request, or supplies arbitrary shell/tool arguments hoping the bot executes them.

### Mitigation Strategy

- `chatops-bot/app/security.py` verifies Slack HMAC-SHA256 over the raw request body,
  validates a five-minute timestamp window, and uses replay detection; ingress checks the
  shared Redis replay claim before enqueueing (`chatops-bot/app/main.py`,
  `chatops-bot/app/queue.py`).
- Intent authorization is deterministic and default-deny by configured Slack user ID
  (`chatops-bot/app/authorization.py`, `chatops-bot/app/config.py`). Unknown actions are
  rejected; READ/DIAGNOSTIC/MUTATION tiers are explicit.
- Current Slack handlers expose only health, ingestion, and pod-status read intents
  (`chatops-bot/app/handlers.py`). Kubernetes MCP RBAC in
  `deploy/helm/insighthub/templates/chatops.yaml` and `infra/k8s/chatops-rbac.yaml` grants
  namespace-scoped `get`, `list`, and `watch` on pods/events/deployments, not write verbs,
  Secret access, or cluster-admin.
- `chatops-bot/app/mcp_client.py` invokes an operator-configured argv without a shell and
  applies a short timeout. This does not establish trust in the configured executable.
- `chatops-bot/app/approval.py` implements one-time approval records bound to requester,
  action, argument hash, approver, and expiry, with self-approval denied by default.
  However, the current Slack handler has no mutation intent/execution path; the approval
  helper is not evidence that a live mutation workflow is deployed.
- Structured audit helpers exist in `chatops-bot/app/audit.py`; verify live log collection
  and retention separately.

Residual risk: no mutation should be enabled until approval is wired to an allowlisted
operation, a distinct least-privilege identity, atomic shared approval state for replicas,
and runtime-tested audit. Never expose arbitrary `kubectl` or shell execution.

## Threat 5 — Financial denial of service (FDOS) / API bill shock

### Description

Abusive or runaway requests can consume provider tokens, exhaust quotas, and create
unexpected LLM charges.

### Impact Level

**HIGH**

### Attack Vector

A client loops `/chat` requests, submits maximum-length questions, repeatedly triggers
expensive model routes/retries, or obtains a shared upstream credential instead of a
scoped virtual key.

### Mitigation Strategy

- Chat request validation caps question length at 2,000 characters, `top_k` at 20, and
  configured generation tokens (`api/app/routers/chat.py`,
  `api/app/core/config.py`). These limits do not replace request rate limiting.
- Optional LiteLLM configuration defines PostgreSQL-backed key budgets and retry/cooldown
  behavior (`security/litellm-config.yaml`). `security/bootstrap_litellm_keys.py` defines
  separate aliases and budgets for InsightHub, ChatOps, and Coding.
- API/worker configuration can use scoped LiteLLM virtual keys, while upstream provider
  keys remain at the gateway (`docker-compose.yml`). Actual enforcement requires LiteLLM
  to be running, keys to be bootstrapped, and clients to use those keys; repository
  configuration alone does not prove this runtime state.
- The provisioned Grafana Day 4 dashboard includes LiteLLM spend/token panels by virtual
  key (`observability/grafana-dashboards/insighthub-day4.json`) when the proxy metrics are
  scraped. Monitoring detects burn; it does not itself cap spend.

Residual risk: direct provider credentials, missing rate limits, and provider-side spend
caps remain important controls. Do not treat dashboard alerts as budget enforcement.

## Threat 6 — Dependency supply chain / unpinned MCP server compromise

### Description

A compromised or unexpectedly changed dependency, container image, or MCP executable can
read prompts/secrets, access internal services, or return malicious tool output.

### Impact Level

**HIGH**

### Attack Vector

An attacker compromises an upstream package/image, exploits an unpinned update, or tricks
an operator into configuring a malicious MCP command with broad process or Kubernetes
access.

### Mitigation Strategy

- Python and Node dependency manifests/lockfiles pin dependency versions; the MCP package
  lockfile is `tools/mcp/package-lock.json`. Locked dependencies reduce drift but do not
  prove packages are vulnerability-free or provenance-verified.
- The built-in MCP server (`tools/mcp/src/server.mjs`, `tools/mcp/src/core.mjs`) registers
  a bounded tool allowlist and validates input/output; it does not expose arbitrary shell
  or URL access.
- ChatOps launches a configured JSON argv without shell interpolation and bounds MCP call
  time (`chatops-bot/app/config.py`, `chatops-bot/app/mcp_client.py`). The operator-supplied
  command itself is not pinned or authenticated by the client.
- Kubernetes permissions are namespace-scoped read-only RBAC as described in Threat 4.
- Some infrastructure images use immutable digests; LiteLLM and several development
  service images use version tags rather than digests. Image provenance/signature
  verification is not implemented here.

Residual risk: review MCP command ownership, executable path, package provenance, image
digest/signature, and vulnerability scan results before production deployment.

## Threat 7 — Slack replay, tampering, and ingress denial of service

### Description

Forged, modified, stale, duplicated, or malformed requests can trigger unauthorized or
repeated processing, or consume ingress/queue resources.

### Impact Level

**MEDIUM**

### Attack Vector

An attacker resends a captured Slack payload, modifies body bytes, omits signing headers,
or floods the endpoint with malformed requests.

### Mitigation Strategy

- ChatOps verifies the signature against the raw body before parsing the request and uses
  constant-time HMAC comparison (`chatops-bot/app/security.py`,
  `chatops-bot/app/main.py`). Stale timestamps and replay fingerprints are rejected.
- Authenticated events are deduplicated/enqueued through Redis/ARQ before the HTTP ACK;
  processing happens in the worker (`chatops-bot/app/queue.py`, `chatops-bot/worker.py`).
- API upload/request validation bounds payload size and shape. These controls do not equal
  an edge WAF or per-source rate limit.

Residual risk: verify ingress rate limiting, Redis availability/retention, and multi-replica
behavior in the target deployment. Do not infer an ACK latency SLO from unit tests alone.

## Review and evidence

Reassess this model when a provider, document source, MCP tool, Slack capability, model/key,
or deployment environment changes. For every mitigation marked configurable, gather
runtime evidence (effective settings, RBAC `can-i`, provider budget/key state, live MCP
calls, log retention, or red-team reports) before representing it as deployed. Track each
accepted residual risk with an owner and review date.
