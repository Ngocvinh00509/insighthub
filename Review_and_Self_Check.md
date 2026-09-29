# Day 04 Review and Self Check

Review date: 2026-09-29. Scope is specification section 8 and the verification
contract. This is an evidence review, not a runtime attestation. Current result:
**NOT ACCEPTED for Day 04 L3**.

`scripts/verify.py` sets `specification_review_required=true`; verifier PASS only
proves listed checks, not live targets, dashboard rendering, Slack delivery, host
MCP calls, or RCA causal quality. The worktree is dirty, so these hashes identify
files reviewed, not a source-to-evidence binding.

| Artifact | SHA-256 | Status |
| --- | --- | --- |
| dashboard | `5DA71152D2943BDC36BA289508E4F07750CEE77E8929601945A6F34D67C7217A` | Static only |
| rules | `CDE9F456FEB81A9149B7886B82BA8D7955A2D41C1E7188973875DFA9F1D77E64` | Static only |
| Alertmanager config | `326F84148885AD25C6FAAA99737C4843BA2AC70E2A5B8DF2E3560970956EE825` | Static only |
| MLOps notes | `465FF9FF5D95EE3B599ED88CBE88A1E69515574B188EC289D7BE98C1E89B0972` | Static pass |
| RCA 1 / 2 / 3 | `616C39D7249A75C1391015687C659D026ACC05A400FF7E1B0C0E1925539E60A5` / `19B34A0E7085827B6CE263D40377CDE95C38152FA29D5833A21C34384CEEC4D2` / `1DA172B0C97ACFFEA77BF20FB6DDBD589A45EB22F972F6D26B887183A474E35F` | Not live evidence |

| Requirement | Finding / impact | Status and closure evidence |
| --- | --- | --- |
| MH1 ServiceMonitor | Render selector is sound; no applied object. | NOT ACCEPTED; capture `kubectl get servicemonitor` in `insighthub-dev`. |
| MH2 five components | Static API/worker/exporter/web mapping; no target response. | NOT ACCEPTED; targets UP and per-component queries. |
| MH3 dashboard | JSON has 9 query panels, but no image/workload window proves data or no errors. | NOT ACCEPTED; screenshot and permalink. |
| MH4 recording rules | Rules exist, not applied/evaluated. | NOT ACCEPTED; applied rule plus recorded series. |
| MH5 three alerts | Three expressions exist; rule test covers queue only and `promtool` is absent. | NEEDS FIX; add latency/error tests and run promtool. |
| MH6 Slack | Safe Secret reference and `#alerts` config only. | NOT ACCEPTED; firing/resolved permalink and UTC timestamp. |
| MH7 latency RCA | `incident-1.json` declares simulated data; lacks contract window/samples. | NOT ACCEPTED; live baseline -> trigger -> firing -> recovery. |
| MH8 queue RCA | `incident-2.json` is simulated; no ZCARD/worker/Redis sequence. | NOT ACCEPTED; live backlog/drain evidence. |
| MH9 error RCA | `incident-3.json` is simulated; no controlled 5xx recovery. | NOT ACCEPTED; live error/recovery evidence. |
| MH10 finite citations | Legacy human-string evidence lacks `started_at`, `ended_at`, finite numeric samples and query-range match. | NOT ACCEPTED; reports from live Prometheus samples only. |
| MH11 quiz | Trainer-excluded. | EXCLUDED. |
| MH12 MLOps | Four blocks, ownership, lifecycle, release scenario and self-check present. | STATIC REVIEW PASS. |
| NFR baseline | No >=1h capture. | NOT ACCEPTED; UTC baseline before incidents. |
| NFR limits/retention | 15d and requests/limits configured. | STATIC PASS / RUNTIME REQUIRED. |
| NFR recording rules | Expensive p95 calculations recorded, unobserved. | STATIC PASS / RUNTIME REQUIRED. |
| NFR evidence-first | Simulated RCA cannot be presented as live evidence. | NOT ACCEPTED; bind samples/windows/fingerprint. |
| NFR bounded labels/cost | Bounded route labels; approved-model provider usage cost excludes embedding/infrastructure and is not billing. | STATIC PASS / RUNTIME REQUIRED. |

Findings to close:

1. `evidence/day4/README.md` says 13 panels while dashboard source has 9. Correct
   the checklist before capture; this is not runtime evidence.
2. Prometheus MCP source and fixture tests exist, but no authorized coding-host
   call trace exists. Token/RBAC or fixture tests do not prove a host call.
3. No dashboard image, Slack link, baseline/recovery capture, or source binding
   exists. These absences prevent acceptance, not source review.

Do not claim Day 04 milestone/L3 completion until every NOT ACCEPTED row has the
stated live evidence. Prompt logs and quiz are outside this trainer-scoped review.
