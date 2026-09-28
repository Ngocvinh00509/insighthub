# Day 6 — AI prompt log

## Metadata

- Date: 2026-09-28
- Host: ChatGPT Codex
- Model: GPT-5 (exact version not exposed by the host)
- Scope: Promptfoo OWASP LLM red-team configuration and RAG prompt-injection/PII mitigations.

## Prompt 1 — Promptfoo red-team configuration

**Request:** Configure InsightHub `/chat` for OWASP LLM Top 10 red teaming,
including injection, RAG poisoning, PII, excessive agency and prompt leakage.

**Accepted:** Use current Promptfoo IDs `system-prompt-override`,
`indirect-prompt-injection`, `rag-poisoning`, `pii:direct`, `pii:session`,
`excessive-agency`, and `prompt-extraction`; use `jailbreak` as a strategy.
The configuration has 70 generated probes and references the committed poisoned
RAG fixture.

**Rejected:** Do not claim `harmful:injection` is a valid current plugin ID; do
not put provider keys or an Authorization header in YAML; do not call a fixture
scan a real red-team result.

## Prompt 2 — Harden RAG processing

**Request:** Block prompt injection and PII leakage before/after the provider,
while preserving the existing `/chat` API contract.

**Accepted:** Normalize Unicode, remove invisible/control characters, reject
known jailbreak patterns before retrieval, escape document/query data into
explicit `<context>` and `<user_query>` boundaries, and block PII-like provider
output. Add a configurable fail-closed HTTP guardrail adapter for a Bedrock,
NeMo, or Llama Guard service.

**Rejected:** Do not trust prompt instructions alone; do not silently bypass an
unavailable configured guardrail; do not log model/provider request bodies.

## Validation

- YAML parser: valid, 70 configured generated probes.
- New targeted security tests: pass during the API unit test run.
- Full unit discovery executed from local environment found a pre-existing
  `test_unit_worker` import failure (`worker` is unavailable on that host).
  It was not disabled or modified to manufacture a pass.
- A live Promptfoo final report remains required before claiming NO HIGH/NO
  CRITICAL findings.
