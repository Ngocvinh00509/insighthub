# Day 5 — AI prompt log

## Metadata

- Date: 2026-09-28
- Host: ChatGPT Codex
- Model: GPT-5 (exact model version was not exposed by the host)
- Scope: InsightHub Day 5 ChatOps security, async processing, MCP intents,
  authorization, approval, audit, RBAC, Helm and submission evidence.

## Prompt 1 — Audit before implementation

**Request:** Audit the existing ChatOps bot against the Day 5 specification:
Slack live delivery, three intents, MCP integration, raw-body signature,
ACK/queue/retry, permission tiers, approval, audit, RBAC, tests and evidence.

**Accepted decisions:**

- Treat starter/skeleton code and unit doubles as insufficient for a LIVE claim.
- Reuse Redis/ARQ for durable asynchronous work rather than FastAPI in-process
  background work.
- Keep Kubernetes and Prometheus access bounded to named MCP capabilities; do
  not permit arbitrary shell commands or PromQL from Slack.

**Rejected decisions:**

- Do not mark Day 5 complete from source-only evidence.
- Do not deploy to an unrelated Kubernetes context merely to create evidence.
- Do not commit ignored runtime evidence, `.env`, tokens or webhook URLs.

## Prompt 2 — Implement secure Slack processing

**Request:** Implement Slack raw-body HMAC signature verification, timestamp and
replay checks, immediate ACK after durable enqueue, ARQ worker retry/dedup, and
tests for security and asynchronous processing.

**Accepted decisions:**

- Verify `v0:{timestamp}:{raw_body}` using HMAC-SHA256 and constant-time
  comparison before parsing JSON or responding to URL verification.
- Reject absent/invalid signatures, stale timestamps, malformed payloads and
  replayed deliveries.
- Use a stable Redis/ARQ job ID based on Slack `event_id`; do MCP and Slack
  reply work only in the worker.
- Add a Redis `SET NX EX` replay claim so replicas fail closed when shared replay
  protection is unavailable.

**Rejected decisions:**

- Do not use deprecated Slack verification tokens as primary authentication.
- Do not acknowledge a request when Redis cannot accept the work.
- Do not log raw request bodies, authorization headers or secrets.

**Validation actually run:**

- `python -m pytest chatops-bot/tests/test_security.py chatops-bot/tests/test_async_processing.py -q -p no:cacheprovider` — 14 passed.

## Prompt 3 — Implement safe operational capabilities and evidence contract

**Request:** Implement health, ingestion count and pod-error intents through
fixed MCP operations; deterministic three-tier authorization; approval binding;
structured audit logs; least-privilege Helm/RBAC; and Day 5 verifier/evidence
support.

**Accepted decisions:**

- Use fixed Prometheus query IDs and report ingestion as a rolling 24-hour
  window rather than falsely describing a five-minute counter as "today".
- Require a Slack user identity and server-side permission mapping; default deny.
- Bind approval to requester, approver, allowlisted action, canonical argument
  hash, expiry and one-time consumption.
- Keep RBAC read-only for pods, events and deployments; no `cluster-admin`.
- Label local verifier evidence as fixture/local instead of LIVE evidence.

**Rejected decisions:**

- Do not hard-code metric values, pod names, credentials or approval results.
- Do not bypass approval for mutation actions.
- Do not claim Slack/Kubernetes/MCP runtime verification without a real lab run.

**Validation actually run:**

- `python -m pytest chatops-bot/tests -q -p no:cacheprovider` — 41 passed.
- `node --test tools/mcp/test/core.test.mjs` — 16 passed.
- `helm lint deploy/helm/insighthub --set chatops.enabled=true --set chatops.existingSecret=chatops-runtime-secrets` — passed.
- Helm render plus `kubectl apply --dry-run=client` — passed.
- `python scripts/verify.py day5 --evidence-dir evidence --json` — INCOMPLETE;
  local/fixture contract exists but LIVE Slack/Kubernetes/Prometheus evidence is
  still required.

## Diff summary

- Added secure Slack request verification, Redis/ARQ queue worker, retry,
  deduplication and structured audit logging.
- Added read-only intent routing to fixed Prometheus and Kubernetes MCP calls.
- Added deterministic permission/approval primitives and least-privilege RBAC.
- Added Helm resources, automated tests, verifier-contract tests and submission
  evidence/screencast runbook.
