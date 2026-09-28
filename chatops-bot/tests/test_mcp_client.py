import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mcp_client import McpClient, McpError, McpServer


class Writer:
    def write(self, data: bytes) -> None:
        pass

    async def drain(self) -> None:
        pass


class Reader:
    def __init__(self, lines: list[bytes] | None = None, hang: bool = False) -> None:
        self.lines = lines or []
        self.hang = hang

    async def readline(self) -> bytes:
        if self.hang:
            await asyncio.sleep(10)
        return self.lines.pop(0) if self.lines else b""


class Process:
    def __init__(self, reader: Reader) -> None:
        self.stdin = Writer()
        self.stdout = reader
        self.returncode = None

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode or 0


def client() -> McpClient:
    return McpClient(McpServer(("fake-mcp",), {}))


def test_mcp_unavailable_backend_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable(*args, **kwargs):
        raise OSError("connection details must not escape")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unavailable)
    with pytest.raises(McpError, match="MCP_UNAVAILABLE"):
        asyncio.run(client().call_tool("insighthub_health", {}))


def test_mcp_timeout_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    async def spawn(*args, **kwargs):
        return Process(Reader(hang=True))

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr("app.mcp_client.MCP_TIMEOUT_SECONDS", 0.01)
    with pytest.raises(McpError, match="MCP_UNAVAILABLE"):
        asyncio.run(client().call_tool("insighthub_health", {}))


def test_mcp_invalid_response_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [
        b'{"jsonrpc":"2.0","id":1,"result":{}}\n',
        b'{"jsonrpc":"2.0","id":2,"result":{"structuredContent":"not-an-object"}}\n',
    ]

    async def spawn(*args, **kwargs):
        return Process(Reader(lines))

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(McpError, match="MCP_UNAVAILABLE"):
        asyncio.run(client().call_tool("insighthub_health", {}))
