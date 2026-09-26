# InsightHub threat model

## Scope and trust boundaries

InsightHub accepts untrusted documents and questions, stores embeddings in PostgreSQL,
retrieves ready document chunks, and sends a constructed prompt to an LLM provider.
ChatOps accepts Slack events and can query bounded read-only MCP services. LiteLLM is an
optional gateway for scoped virtual keys and spend tracking. The principal trust
boundaries are: browser/Slack to API, document corpus to RAG prompt, API to LLM provider,
ChatOps to MCP, and LiteLLM to provider/billing systems.

Risk ratings use the highest plausible impact if the threat is exploited in a production
deployment. A control described as configurable is not evidence that it is enabled in a
specific environment.

## Threat 1 — Indirect prompt injection through a poisoned RAG document

### Description

An attacker uploads or otherwise introduces a document whose text tells the model to
ignore policy, reveal data, call tools, or alter its answer. Retrieval can place that text
next to the user question, making it appear authoritative to a model.

### Impact Level

**HIGH**

### Attack Vector

The attacker submits a permitted `.txt`, `.md`, or `.pdf` document, waits for ingestion
to mark it ready, then asks a query crafted to retrieve the malicious chunk. The included
`security/sample-docs/poisoned-doc.md` is a non-production fixture for this scenario.

### Mitigation Strategy

- `api/app/services/llm.py` wraps retrieved data in `<context>` and the question in
  `<user_query>`.
- The hardened system prompt states that context is untrusted data, never instructions,
  and prohibits executing or disclosing instructions found in documents.
- Document ingestion enforces file type, size, extraction, and chunking constraints; it
  does not grant documents tool or infrastructure authority.
- Promptfoo red-team configuration includes `indirect-prompt-injection` and
  `rag-poisoning` probes. The poisoned fixture must be explicitly uploaded in a lab before
  it can exercise retrieval.

Residual risk remains because natural-language instructions cannot be made safe solely by
prompt text. Production deployments should restrict upload authorization and review
untrusted corpus sources.

## Threat 2 — Direct jailbreak and system-prompt leakage

### Description

A user attempts to override model instructions directly, for example by asking it to
ignore previous instructions, reveal its system prompt, or adopt a privileged role.

### Impact Level

**HIGH**

### Attack Vector

Requests reach `POST /chat` with zero-width or bidi control characters, Unicode variants,
or known instruction-override phrases intended to evade simple matching and influence the
provider model.

### Mitigation Strategy

- `api/app/services/security.py` normalizes input with NFKC, removes control/format
  characters, normalizes whitespace, and rejects configured direct-jailbreak patterns.
- The chat route sanitizes before embeddings, retrieval, and provider invocation.
- The system prompt explicitly disallows revealing system prompts and credentials.
- Optional `GUARDRAIL_PROVIDER=llama_guard` invokes an OpenAI-compatible Llama Guard
  endpoint before the application provider; unavailable or non-`SAFE` verdicts fail
  closed.
- Promptfoo coverage includes `system-prompt-override`, `jailbreak`, and
  `prompt-extraction`.

The deterministic phrase list is intentionally not treated as a complete jailbreak
detector; the external guardrail and regression testing are defense-in-depth controls.

## Threat 3 — PII and sensitive-data exfiltration in chat output

### Description

Retrieved documents, provider responses, errors, or a compromised prompt can expose email
addresses, phone numbers, payment numbers, tokens, or other sensitive text in a response.

### Impact Level

**CRITICAL**

### Attack Vector

An attacker asks for a private document, persuades the model to repeat context verbatim,
or causes an upstream service to return a credential-shaped value. Data could then reach a
browser or Slack response.

### Mitigation Strategy

- `api/app/services/security.py` redacts common email, telephone, payment-card, and
  API-token-shaped values from generated output before it is returned.
- Provider exceptions are translated to fixed `ServiceError` responses; provider bodies,
  credentials, and raw tracebacks are not exposed to clients.
- The RAG MCP service projects document IDs/status only and omits filename/content for its
  read-only tool output.
- ChatOps Block Kit rendering redacts token and secret-shaped text before posting Slack
  messages.
- Promptfoo coverage includes `pii:direct` and `pii:session`.

Regex redaction cannot classify all sensitive business content. Authorization, document
classification, and provider-side retention controls remain required for production data.

## Threat 4 — Unauthorized infrastructure mutation through ChatOps

### Description

An attacker forges a Slack event, abuses an app mention, injects instructions into a bot
conversation, or obtains a bot credential in order to mutate Kubernetes or cloud state.

### Impact Level

**CRITICAL**

### Attack Vector

Requests target `POST /slack/events` with a replayed timestamp or forged signature. A
valid user can also request destructive operations through natural language or try to make
the bot invoke unbounded MCP tools.

### Mitigation Strategy

- ChatOps verifies Slack HMAC-SHA256 over the raw body and timestamp; requests older than
  300 seconds are rejected.
- Slack events are acknowledged separately from background processing, limiting request
  timeout/retry pressure.
- The configured InsightHub MCP service enforces a read-only allowlist, fixed loopback
  routes, bounded request sizes/timeouts, and does not expose shell, arbitrary URL, file,
  document-content, or mutation tools.
- Kubernetes RBAC manifests grant only `get`/`list` operations to the MCP service account.
- Confirmation tokens are one-time and expire; audit records include timestamp, user,
  tool, arguments, result summary, and approval state.

The current ChatOps implementation contains a read-only query boundary. Any future scale,
restart, rollback, or cloud mutation must use a separate identity and an authorization
workflow bound to the exact action.

## Threat 5 — Financial denial of service and API bill shock

### Description

Attackers or faulty workloads can trigger high token use, repeated provider retries, or
expensive models, rapidly consuming a shared API budget.

### Impact Level

**HIGH**

### Attack Vector

An exposed client loops long chat requests, submits oversized prompts, creates expensive
ChatOps traffic, or uses an accidentally shared provider credential directly instead of a
scoped gateway key.

### Mitigation Strategy

- API request models bound question length, `top_k`, and provider max tokens through
  validated settings.
- LiteLLM configuration defines separate virtual-key aliases for application, ChatOps, and
  coding workflows. The bootstrap applies per-key `max_budget` and `budget_duration`.
- LiteLLM uses PostgreSQL for spend/budget enforcement and configures retry/cooldown plus
  a chat fallback model group.
- The Grafana FinOps panels query LiteLLM spend/token/cache metrics by `api_key_alias` to
  detect unexpected burn rates.

Budgets are enforceable only when LiteLLM is running with its PostgreSQL database and the
application uses a scoped virtual key. Upstream provider budgets are an additional
necessary control.

## Threat 6 — Dependency supply-chain or unpinned MCP server compromise

### Description

A malicious or changed package, container image, MCP server, or transitive dependency can
gain access to prompts, credentials, local network services, or tool execution.

### Impact Level

**HIGH**

### Attack Vector

An operator runs `latest`, `npx` without a lockfile, an unreviewed MCP command, a mutable
container tag, or grants a vendor MCP server broad kubeconfig/Docker permissions.

### Mitigation Strategy

- Python requirements and the MCP Node package lock pin dependencies; project Docker
  images use pinned base images/digests where supplied.
- The local MCP server has a strict tool allowlist and rejects arbitrary shell, URL, and
  document-content access even if a client tries direct tool calls.
- Kubernetes MCP RBAC uses a dedicated service account with read-only `get`/`list` verbs;
  it does not grant cluster-admin or Secret access.
- LiteLLM is configured as a separately pinned image profile. Operators must review the
  pinned release before upgrade and retain a lock/evidence trail.

Image tags without an immutable digest and externally configured MCP commands remain
operator trust assumptions. They should be verified against a reviewed digest and least
privilege policy before production use.

## Threat 7 — Replay, tampering, and availability abuse at public ingress

### Description

Unauthenticated or malformed uploads and Slack events can consume resources, while replay
or tampering can cause duplicated or unauthorized work.

### Impact Level

**MEDIUM**

### Attack Vector

Attackers resend Slack payloads, submit malformed JSON, oversized uploads, or repeatedly
trigger ingestion jobs.

### Mitigation Strategy

- Slack signature verification uses constant-time comparison and a five-minute replay
  window before JSON parsing.
- Upload middleware enforces a bounded file size; ingestion uses document status,
  transactions, and identity/conflict checks to prevent duplicate chunk writes.
- Redis/ARQ separates document processing from the request path and maintains retry
  behavior rather than running unbounded in-process background work.
- API error handlers preserve fixed public error messages and bounded metrics labels.

## Review cadence

Review this model after a new provider, MCP server, document source, Slack capability,
LiteLLM model/key, or cloud deployment is introduced. Red-team findings must result in a
test, a mitigation decision, and a retest against the same dataset before being marked
resolved.
