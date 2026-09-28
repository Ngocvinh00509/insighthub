import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import handlers


@pytest.fixture(autouse=True)
def allow_read_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHATOPS_READ_USERS", "U123")


class FakeMcpClient:
    def __init__(self, answers: dict[str, dict]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        return self.answers[arguments.get("query", name)]


def response_lines(reply: list[dict]) -> str:
    return reply[1]["text"]["text"]


def test_health_intent_uses_real_prometheus_mcp_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeMcpClient(
        {
            "insighthub_health": {"live": True, "ready": True, "databaseReady": True},
            "requests_5m": {"value": 18},
            "errors_5m": {"value": 1},
        }
    )
    monkeypatch.setattr(handlers, "prometheus_client", lambda: client)

    reply = asyncio.run(handlers.build_reply(handlers.classify_intent("Is InsightHub healthy?"), "U123"))

    assert "API live: ✅" in response_lines(reply)
    assert ("insighthub_health", {}) in client.calls
    assert ("prometheus_summary", {"query": "requests_5m"}) in client.calls
    assert ("prometheus_summary", {"query": "errors_5m"}) in client.calls


def test_ingestion_intent_uses_fixed_prometheus_counter_query(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeMcpClient({"ingestion_jobs_24h": {"value": 7}})
    monkeypatch.setattr(handlers, "prometheus_client", lambda: client)

    reply = asyncio.run(handlers.build_reply(handlers.classify_intent("show ingestion count"), "U123"))

    assert "7" in response_lines(reply)
    assert client.calls == [("prometheus_summary", {"query": "ingestion_jobs_24h"})]


def test_pods_intent_uses_kubernetes_mcp_without_hard_coded_pod_names(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        kubernetes_mcp_command=("kubernetes-mcp",),
        kubernetes_namespace="insighthub-dev",
        read_users=frozenset({"U123"}),
        diagnostic_users=frozenset(),
        mutation_users=frozenset(),
    )
    client = FakeMcpClient(
        {
            "list_pods": {
                "pods": [
                    {"name": "api-7b9d", "phase": "Running", "restartCount": 0},
                    {"name": "worker-3f2a", "phase": "Pending", "reason": "ImagePullBackOff", "restartCount": 1},
                ]
            },
        }
    )
    monkeypatch.setattr(handlers, "get_settings", lambda: settings)
    monkeypatch.setattr(handlers, "McpClient", lambda server: client)

    reply = asyncio.run(handlers.build_reply(handlers.classify_intent("which pods have problems?"), "U123"))

    assert "worker-3f2a" in response_lines(reply)
    assert "api-7b9d" not in response_lines(reply)
    assert ("list_pods", {"namespace": "insighthub-dev"}) in client.calls


def test_unknown_intent_does_not_call_backend() -> None:
    reply = asyncio.run(handlers.build_reply(handlers.classify_intent("delete all pods"), "U123"))

    assert "Hãy hỏi" in response_lines(reply)
