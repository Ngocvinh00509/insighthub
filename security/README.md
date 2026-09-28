# Security, Governance, FinOps - bắt buộc Day 6

Học viên hoàn thiện Promptfoo50+ cases, initial/final reports, guardrails runtime, LiteLLM gateway+3 virtual keys/budgets, routing cho app/bot/coding agent, cost dashboard và threat model>=6 threats. [Spec mục10](../Running-Project-Specification-Student.md).

Config skeleton chỉ giúp bắt đầu; cần actual allowed/blocked, indirect injection qua ingestion/retrieval, budget/bypass tests. Dataset/eval tự viết bổ sung, không thay Promptfoo/guardrails/gateway.

## LiteLLM prompt-cache savings metric

LiteLLM Prometheus exports spend, input/output tokens and provider-reported
cached prompt tokens, but does not export a universal USD-saved counter. The
optional `litellm_prompt_cache_savings.py` callback emits
`insighthub_litellm_prompt_cache_savings_usd_total` from observed cached tokens
and an operator-maintained per-model price differential. Set
`LITELLM_PROMPT_CACHE_SAVINGS_USD_PER_MILLION_BY_MODEL` to a JSON map only after
checking the current provider's uncached-input minus cache-read rate. Leave it
empty when pricing is unknown; the dashboard then shows no savings series.

Aliases created by `bootstrap_litellm_keys.py` are `insighthub-app-key`
(InsightHub), `chatops-bot-key` (Bot), and `coding-workflow-key` (Coding). The
provisioned Day 4 Grafana dashboard filters to these aliases. LiteLLM runs under
the optional `litellm` Compose profile and Prometheus scrapes it over the
internal Compose network. The scrape port is not published separately.

Cấu hình hiện tại là scaffold, chưa đủ 50 ca. Ghi coverage mapping cho direct/indirect injection, RAG poisoning, PII và excessive agency. Dùng plugin IDs của bản pin; strategy cũ `prompt-injection` đã đổi thành `jailbreak-templates`. Nguồn: [plugins](https://www.promptfoo.dev/docs/red-team/plugins/), [migration strategy](https://www.promptfoo.dev/docs/red-team/strategies/prompt-injection/). Target HTTP gọi /chat chỉ kiểm tra câu hỏi; poisoning phải đi qua upload/retrieval bằng adapter học viên xây.
