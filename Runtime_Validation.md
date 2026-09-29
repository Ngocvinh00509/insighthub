# Day 04 Runtime Validation

Status: **UNVERIFIED - do not label static checks as live success.**

The only current cluster observation is `kubectl get namespace insighthub-dev`
on 2026-09-29, which returned `NotFound`. No deployment, namespace creation,
secret read, test alert, provider call, or Slack post was performed for review.

| Gate | Current evidence | Result | Closure method |
| --- | --- | --- | --- |
| Namespace and ServiceMonitor | No `insighthub-dev` namespace | UNVERIFIED | In an approved disposable lab, capture namespace and ServiceMonitor YAML. |
| Five scrape sources | No Prometheus targets artifact | UNVERIFIED | Save `/api/v1/targets` with UTC time and component queries. |
| Dashboard | No screenshot/permalink | UNVERIFIED | During workload capture all 9 panels without error or `No data`. |
| Rules | `promtool` unavailable; no running PrometheusRule | UNVERIFIED | Run `promtool check/test rules`, then observe recording series. |
| Slack | Config only | UNVERIFIED | After authorization capture firing and resolved permalink/timestamp without webhook. |
| Baseline/recovery | No >=1h baseline or incident sequence | UNVERIFIED | Separately save baseline -> trigger -> firing -> recovery for latency, queue and 5xx. |
| RCA citations | Three reports are simulated and incompatible with verifier schema | FAIL AS LIVE EVIDENCE | Replace only after live finite samples and incident windows exist. |
| Prometheus MCP | Source/fixture tests only | UNVERIFIED | Capture authorized host call metadata and timestamp; never expose tokens. |

Sequence after explicit lab authorization: targets -> one-hour baseline -> latency
incident/recovery -> queue incident/recovery -> error incident/recovery -> Slack
firing/resolution -> evidence-bound RCA -> verifier and reviewer check. Missing
scrape or `redis_up=0` must remain unknown/unavailable, never queue depth zero.
