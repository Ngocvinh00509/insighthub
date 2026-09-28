# Day 6 — AI Prompt Log

## Metadata

- Date: 2026-09-28
- Host: ChatGPT Codex
- Model: GPT-5 (exact version not exposed by the host)
- Scope: OWASP LLM red-team configuration, RAG security controls, LiteLLM/Grafana FinOps, and STRIDE threat modeling.
- Evidence note: This log records repository changes and checks actually observed. It does not claim a live Promptfoo result, live Grafana data, or AWS deployment.

## Prompt 1 — Promptfoo OWASP LLM red-team configuration

**Request:** Configure InsightHub `/chat` red teaming for direct and indirect
prompt injection, RAG poisoning, PII leakage, excessive agency, and prompt
extraction, including a poisoned-document fixture and at least 50 generated
cases.

**Accepted decisions:**

- Use supported Promptfoo plugin/strategy IDs and configure at least 50 generated
  probes; retain the poisoned RAG fixture as an explicit test input.
- Keep provider credentials and authorization headers out of the configuration.
- Treat a valid YAML/configuration as setup evidence only, not as a clean red-team
  result.

**Rejected decisions:**

- Do not assume `harmful:injection` is a supported plugin ID when the pinned tool
  expects a different plugin/strategy.
- Do not call fixture/static configuration a live `/chat` security scan.

**Validation recorded:**

- Promptfoo configuration was YAML-validated and configured for 70 probes.
- A live final report showing NO HIGH / NO CRITICAL remains unverified; no such
  result is claimed here.

## Prompt 2 — Harden RAG prompt and add guardrails

**Request:** Add Unicode/input sanitization, explicit untrusted `<context>` and
`<user_query>` prompt boundaries, output checks for PII-like values, and a
configurable HTTP guardrail adapter while preserving the existing API contract.

**Accepted decisions:**

- Normalize Unicode and remove control/format characters; reject known direct
  jailbreak patterns before retrieval/provider invocation.
- Escape retrieved document/question content and label RAG context as untrusted.
- Fail closed when an explicitly configured HTTP guardrail is unavailable or
  returns a non-allow decision.
- Keep provider/model request bodies out of logs.

**Rejected decisions:**

- Do not treat prompt wording or a finite phrase list as a complete prompt-
  injection defense.
- Do not silently skip a configured guardrail on failure.
- Do not claim comprehensive PII detection from regex-based output checks.

**Validation recorded:**

- Targeted API security tests passed during the earlier implementation run.
- Full local unit discovery had a pre-existing `test_unit_worker` import failure
  (`worker` unavailable in that host environment); the test was not disabled or
  weakened.
- Live Promptfoo final report remains outstanding.

## Prompt 3 — LiteLLM / Prometheus FinOps dashboard

**Request:** Add Grafana views for LiteLLM spend rate by InsightHub/Bot/Coding
virtual key, prompt/completion tokens, provider prompt-cache ratio, and estimated
cache savings; create a $50/month AWS Budget notification if the work is on AWS.

**Accepted decisions:**

- Scrape the optional LiteLLM `/metrics` endpoint over the private Compose
  network and scope dashboard series to the three configured key aliases.
- Present `$ /day` as a projected run-rate from recent spend, not as settled
  daily billing.
- Do not invent cache savings: emit an estimated USD metric only when an
  operator supplies the model-specific uncached-input minus cache-read price.
- Treat the AWS Budget as an external state change requiring an AWS lab context
  and a specified notification destination.

**Rejected decisions:**

- Do not use a wrong `namespace` label filter on LiteLLM series.
- Do not infer a universal USD cache-savings value from cached-token counts.
- Do not create an AWS Budget without confirmation that this is an AWS lab and
  without email/SNS or Slack notification target details.

**Validation actually run:**

- Python AST, Grafana dashboard JSON, Prometheus YAML, and LiteLLM YAML parsed
  successfully.
- `docker compose config --quiet` — passed.
- `git diff --check` — passed (Git emitted line-ending conversion warnings).
- Runtime was not verified: Docker API access returned permission denied, so no
  live Grafana/Prometheus/LiteLLM data was observed. No AWS Budget was created.

## Prompt 4 — STRIDE / OWASP LLM threat model

**Request:** Write `security/threat-model.md` with at least six threats and
`Description`, `Impact Level`, `Attack Vector`, and `Mitigation Strategy` for
each, covering poisoned RAG, jailbreak/prompt leakage, PII exfiltration,
ChatOps mutation, financial DoS, and MCP/dependency supply chain.

**Accepted decisions:**

- Include seven threats, map them to STRIDE and OWASP LLM categories, and assess
  severity based on plausible production impact.
- Distinguish repository implementation/configuration from controls whose
  activation or effectiveness requires runtime verification.
- Record concrete residual risk, including limited regex PII screening,
  optional external guardrail, read-only current ChatOps path, conditional
  LiteLLM budget enforcement, and unpinned external MCP command/image risks.
- Correct stale file references and avoid claiming runtime tests or evidence not
  available in this work.

**Rejected decisions:**

- Do not describe an approval helper as a live mutation workflow; current Slack
  handlers expose read intents only.
- Do not claim PII protection covers returned RAG contexts or arbitrary
  sensitive business data.
- Do not present config existence as proof of deployment.

**Validation actually run:**

- Reviewed referenced source/config files against the threat descriptions.
- `git diff --check -- security/threat-model.md` — passed (line-ending warning
  only).
- No threat-model-specific automated or runtime test was run.

## Diff summary

- Recorded the Day 6 Promptfoo setup and RAG prompt/input/output guardrail work;
  live red-team NO HIGH / NO CRITICAL remains outstanding.
- Added LiteLLM Prometheus scraping and FinOps panels to the provisioned Day 4
  dashboard, including an optional operator-priced prompt-cache savings metric.
- Updated `security/threat-model.md` to map seven threats to STRIDE/OWASP LLM and
  accurately state implemented, optional, and residual controls.
- Runtime Grafana verification and the conditional AWS Budget action remain
  incomplete/not performed; no synthetic evidence or PASS claim was added.
