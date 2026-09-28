"""Safe failure classes used by the durable ChatOps worker."""


class RetryableSlackProcessingError(RuntimeError):
    """A transient MCP or Slack delivery failure that may be retried."""


class PermanentSlackProcessingError(RuntimeError):
    """A configuration or request failure that retries cannot correct."""
