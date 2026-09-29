# [Day 4] Observability source review - not ready for acceptance

## Summary

The working tree contains static observability source for API/worker metrics,
Redis and PostgreSQL exporters, ServiceMonitor discovery, rules, a 9-panel
RED/USE dashboard, safe Alertmanager Slack configuration, and MLOps notes. It
does not contain accepted runtime evidence.

## Static checks observed

- Helm lint and render local/dev/staging: passed in this session.
- Staging render: ServiceMonitor statically matches API, worker, Redis exporter
  and PostgreSQL exporter on `http-metrics`; web uses kubelet/cAdvisor.
- Dashboard JSON: 9 panels with PromQL targets.
- Prometheus values: 15d retention plus requests/limits.
- Python syntax, relevant YAML/JSON parsing, cost guard and `git diff --check`: passed.
- `promtool`: unavailable. Full Python unit suite: blocked because host Python lacks `httpx`.

## Review blockers

- `insighthub-dev` is absent; no targets are UP or observed.
- No dashboard screenshot, one-hour baseline, three complete incident/recovery
  sequences, or Slack firing/resolved permalink.
- Existing RCA reports are explicitly simulated and do not meet the required
  live-citation schema.
- No actual coding-host Prometheus MCP call evidence.
- Rule tests need latency and HTTP-error alert coverage.

## Acceptance decision and close plan

Do not merge or describe this as Day 04 L3 complete based on verifier output.
`specification_review_required=true` makes full review and runtime evidence
mandatory. No commit was created, no PR opened and no remote push performed.

Run the approved disposable lab; collect targets, baseline, sequential incidents
and recovery evidence; validate rules with promtool; capture authorized Slack/MCP
traces; bind all evidence to a settled fingerprint; then repeat the review.
