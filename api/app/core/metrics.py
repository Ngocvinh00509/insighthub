"""Bounded labels; provider-reported tokens and word-based estimates are separate."""

from prometheus_client import Counter, Gauge, Histogram

http_requests_total = Counter(
    "insighthub_http_requests_total",
    "HTTP requests by route template",
    ["method", "endpoint", "status"],
)
rag_query_latency = Histogram(
    "insighthub_rag_query_latency_seconds",
    "RAG end-to-end latency",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
llm_call_latency = Histogram(
    "insighthub_llm_call_latency_seconds",
    "Generation latency including failures",
    buckets=(0.25, 0.5, 1, 2.5, 5, 10, 20, 60),
)
llm_tokens_total = Counter(
    "insighthub_llm_tokens_total",
    "Provider-reported LLM tokens, not billing totals",
    ["provider", "direction"],
)
llm_generation_estimated_cost_dollars_total = Counter(
    "insighthub_llm_generation_estimated_cost_dollars_total",
    "Estimated generation-only USD cost for the approved model with complete provider usage",
)
embedding_tokens_total = Counter(
    "insighthub_embedding_tokens_total",
    "Provider-reported embedding tokens",
    ["provider", "input_type"],
)
embedding_estimated_tokens_total = Counter(
    "insighthub_embedding_estimated_tokens_total",
    "Word-based estimates only when provider usage is unavailable",
    ["provider", "input_type"],
)
documents_total = Gauge(
    "insighthub_documents_total",
    "Documents by status refreshed at metrics scrape",
    ["status"],
)
ingestion_errors_total = Counter(
    "insighthub_ingestion_errors_total",
    "Failed processing attempts",
)
<<<<<<< Updated upstream
http_request_duration = Histogram(
    "insighthub_http_request_duration_seconds",
    "HTTP request duration by route template",
    ["method", "endpoint", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
ingestion_jobs_total = Counter(
    "insighthub_ingestion_jobs_total",
    "Ingestion worker job attempts by terminal attempt outcome",
    ["outcome"],
)
ingestion_job_duration = Histogram(
    "insighthub_ingestion_job_duration_seconds",
    "Wall-clock duration of an ingestion worker attempt",
    ["outcome"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
ingestion_retries_total = Counter(
    "insighthub_ingestion_retries_total",
    "Ingestion worker attempts deferred for retry",
)
ingestion_active_jobs = Gauge(
    "insighthub_ingestion_active_jobs",
    "Ingestion worker attempts currently executing",
)
=======
ingestion_queue_depth = Gauge(
    "insighthub_queue_depth",
    "Current number of pending ARQ jobs, sampled from the configured Redis sorted set",
    ["queue"],
)
worker_processing_seconds = Histogram(
    "insighthub_worker_processing_seconds",
    "Document processing duration in the ingestion worker",
    ["outcome"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 300),
)
worker_documents_total = Counter(
    "insighthub_worker_documents_total",
    "Completed ingestion worker document attempts",
    ["outcome"],
)
queue_depth_refresh_errors_total = Counter(
    "insighthub_queue_depth_refresh_errors_total",
    "Failed attempts to read the ARQ queue depth from Redis",
)

# Lab pricing approved for Day 4 on 2026-09-29. This is intentionally not a
# provider billing claim and excludes embeddings and infrastructure.
APPROVED_GENERATION_COST_MODEL = "gpt-5.6-sol"
APPROVED_INPUT_USD_PER_MILLION_TOKENS = 5.0
APPROVED_OUTPUT_USD_PER_MILLION_TOKENS = 30.0
>>>>>>> Stashed changes


def record_embedding_usage(provider, input_type, tokens, texts):
    if tokens is not None:
        embedding_tokens_total.labels(provider, input_type).inc(tokens)
    else:
        embedding_estimated_tokens_total.labels(provider, input_type).inc(
            sum(len(text.split()) / 0.75 for text in texts)
        )


def record_generation_estimated_cost(
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    """Record an estimate only for complete, provider-reported approved-model usage."""
    if (
        provider != "openai"
        or model != APPROVED_GENERATION_COST_MODEL
        or input_tokens is None
        or output_tokens is None
        or input_tokens < 0
        or output_tokens < 0
    ):
        return
    llm_generation_estimated_cost_dollars_total.inc(
        (
            input_tokens * APPROVED_INPUT_USD_PER_MILLION_TOKENS
            + output_tokens * APPROVED_OUTPUT_USD_PER_MILLION_TOKENS
        )
        / 1_000_000
    )
