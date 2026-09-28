"""Read-only Prometheus exporter for the configured Redis/ARQ sorted-set queue."""

import asyncio
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from redis.asyncio import Redis

QUEUE_NAME = os.environ.get("INGESTION_QUEUE", "insighthub:ingestion")
REDIS_URL = os.environ.get("REDIS_URL", "")


async def queue_metrics() -> tuple[int, float, int]:
    """Return actual ARQ zset cardinality, oldest score age, and scrape success."""
    if not REDIS_URL:
        return 0, 0.0, 0
    client = Redis.from_url(REDIS_URL)
    try:
        depth = await client.zcard(QUEUE_NAME)
        oldest = await client.zrange(QUEUE_NAME, 0, 0, withscores=True)
        age = max(0.0, time.time() - oldest[0][1] / 1000) if oldest else 0.0
        return depth, age, 1
    finally:
        await client.aclose()


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path != "/metrics":
            self.send_error(404)
            return
        depth, age, success = asyncio.run(queue_metrics())
        queue = QUEUE_NAME.replace("\\", "\\\\").replace('"', '\\"')
        body = (
            "# HELP insighthub_queue_depth Pending ARQ jobs in the configured Redis queue.\n"
            "# TYPE insighthub_queue_depth gauge\n"
            f'insighthub_queue_depth{{queue="{queue}"}} {depth}\n'
            "# HELP insighthub_queue_oldest_job_age_seconds Age of the oldest pending ARQ job.\n"
            "# TYPE insighthub_queue_oldest_job_age_seconds gauge\n"
            f'insighthub_queue_oldest_job_age_seconds{{queue="{queue}"}} {age}\n'
            "# HELP insighthub_queue_scrape_success Whether the Redis queue query succeeded.\n"
            "# TYPE insighthub_queue_scrape_success gauge\n"
            f'insighthub_queue_scrape_success{{queue="{queue}"}} {success}\n'
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9115), MetricsHandler).serve_forever()
