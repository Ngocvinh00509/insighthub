# Day 5 submission evidence and screencast

This checklist separates evidence actually collected from evidence that still
needs a live Slack/Kubernetes/Prometheus run. Never manufacture a screenshot,
timestamp, audit event, or result. Store runtime captures under
`evidence/day5/runtime/` locally; that directory is ignored by Git so it cannot
accidentally publish secrets or screenshots with sensitive data.

## Evidence checklist

| Artifact | Requirement | Evidence to collect | Path | Status |
| --- | --- | --- | --- | --- |
| Slack event delivery | Slack Bot LIVE | Slack App Event Subscriptions page showing a verified request URL with the URL redacted; one successful `app_mention` delivery ID | `evidence/day5/runtime/slack-event-delivery.png` | INCOMPLETE |
| Health conversation | health intent | Screenshot of the message and bot reply; corresponding Prometheus query result and audit event with the same request ID | `evidence/day5/runtime/health-{request_id}.png` | INCOMPLETE |
| Ingestion conversation | ingestion count | Screenshot of the message and reply; Prometheus result for `ingestion_jobs_24h`; audit event | `evidence/day5/runtime/ingestion-{request_id}.png` | INCOMPLETE |
| Pod triage conversation | pods errors | Screenshot of the message and reply; Kubernetes MCP call/result and audit event | `evidence/day5/runtime/pods-{request_id}.png` | INCOMPLETE |
| Kubernetes MCP trace | Kubernetes MCP | Inspector/client trace of the configured read-only `list_pods` call, namespace, timestamp and result summary | `evidence/day5/runtime/kubernetes-mcp-{request_id}.json` | INCOMPLETE |
| Prometheus MCP trace | Prometheus MCP | Inspector/client trace for fixed health and ingestion query IDs; no arbitrary PromQL | `evidence/day5/runtime/prometheus-mcp-{request_id}.json` | INCOMPLETE |
| HTTP security test | signature verification | Test output for valid, invalid, expired, modified-body, missing-header and replay cases; redact headers/body if captured | `evidence/day5/runtime/slack-security-tests.txt` | PARTIAL |
| ACK timing | ACK < 3 seconds | Timestamp/latency measurement from a signed Slack event to HTTP 200 ACK; include method and environment | `evidence/day5/runtime/ack-latency-{request_id}.json` | INCOMPLETE |
| Queue trace | durable queue/dedup/retry | Redis/ARQ job ID, one duplicate delivery result, and retry sequence with sanitized worker logs | `evidence/day5/runtime/queue-{event_id}.txt` | INCOMPLETE |
| Permission tests | 3-tier permission | Test output plus one live allowed READ and one denied operation audit event | `evidence/day5/runtime/permission-{request_id}.json` | PARTIAL |
| Approval trace | approval binding | Pending request, distinct approver, expiry, exact action/argument hash (not raw sensitive args), one-time execution audit chain | `evidence/day5/runtime/approval-{request_id}.json` | INCOMPLETE |
| Audit trail | structured audit log | Sanitized JSON records correlated by request ID for each demo action | `evidence/day5/runtime/audit-{request_id}.jsonl` | INCOMPLETE |
| RBAC verification | least privilege | `kubectl auth can-i` output for get/list pods = yes and delete pods = no, with context/namespace shown | `evidence/day5/runtime/rbac-can-i.txt` | INCOMPLETE |
| Automated tests | regression tests | Exact command and result: ChatOps suite, MCP suite, and Day 5 verifier | `evidence/day5/runtime/test-results.txt` | PARTIAL |

`PARTIAL` means a local test exists but does not prove a live integration. Do
not change it to PASS until the listed runtime capture exists and is correlated.

## Safe collection commands

Run these only against the intended lab context. Do not paste environment
variables, Secret manifests, tokens, signing secrets, webhook URLs, or raw
Slack request bodies into evidence.

```powershell
kubectl config current-context
kubectl -n insighthub-dev get pods,svc,serviceaccount,role,rolebinding
kubectl auth can-i get pods --as=system:serviceaccount:insighthub-dev:insighthub-chatops-readonly -n insighthub-dev
kubectl auth can-i list pods --as=system:serviceaccount:insighthub-dev:insighthub-chatops-readonly -n insighthub-dev
kubectl auth can-i delete pods --as=system:serviceaccount:insighthub-dev:insighthub-chatops-readonly -n insighthub-dev
kubectl -n insighthub-dev logs deployment/insighthub-chatops-worker --since=10m
python -m pytest chatops-bot/tests -q -p no:cacheprovider
node --test tools/mcp/test/core.test.mjs
python scripts/verify.py day5 --evidence-dir evidence --json
```

Before saving logs, remove lines containing `Authorization`, `Bearer`, `xox`,
`SLACK_`, webhook URLs, signing secrets, or raw payloads. Keep request IDs,
event IDs, timestamps, action names, decisions, durations and error categories.

## Short screencast script (about three minutes)

1. **Architecture — 20 seconds.** Show the diagram or Helm resources: Slack
   Events → signature verification → Redis/ARQ → worker → intent router →
   read-only Kubernetes/Prometheus MCP → Slack reply/audit. Explain that ACK
   happens before MCP work.
2. **Health — 25 seconds.** In Slack send `check health`. Show the bot's actual
   reply, then the matching fixed Prometheus MCP trace and audit request ID.
   Do not read out metric values before the live run.
3. **Ingestion count — 25 seconds.** Send `show ingestion count`. Show the
   actual reply and explain it reports the configured rolling 24-hour metric
   window. Show the matching fixed query ID, never an arbitrary PromQL field.
4. **Pod errors — 25 seconds.** Send `which pods have problems?`. Show the
   actual reply and a Kubernetes MCP `list_pods` trace. If there are no errors,
   say that the cluster reported none; do not stage a failure as a real one.
5. **Security — 20 seconds.** Show sanitized test output for invalid signature,
   old timestamp, modified body and replay rejection. State that verification
   uses the raw body and HMAC SHA-256 before JSON parsing.
6. **Permissions and approval — 20 seconds.** Show deterministic policy tests:
   a READ allow, a deny, and mutation requiring approval. Only show a live
   approval after it exists; otherwise clearly label this as local test proof.
7. **Audit and RBAC — 20 seconds.** Show one sanitized audit JSON event and
   `kubectl auth can-i` outputs: read is allowed, delete is denied.
8. **Evidence close-out — 15 seconds.** Show this checklist and the verifier
   result. State any remaining `INCOMPLETE` item explicitly.

## Redaction checklist before recording

- Collapse or crop browser address bars when they contain Slack webhook or
  request URLs.
- Never open Kubernetes Secret data, `.env`, terminal history containing an
  export command, or Slack App OAuth/token pages.
- Blur Slack user identifiers if the recording will be public.
- Keep only safe correlation metadata: timestamp, request/event ID, intent,
  action, decision, duration, backend name and sanitized outcome.
