"""Small, bounded MCP stdio client for the ChatOps read-only tools."""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

MCP_TIMEOUT_SECONDS = 2.0


class McpError(RuntimeError):
    """A safe, non-upstream-error result from an MCP call."""


@dataclass(frozen=True)
class McpServer:
    command: tuple[str, ...]
    environment: dict[str, str]


class McpClient:
    """Use an operator-configured stdio server without shell execution."""

    def __init__(self, server: McpServer) -> None:
        self._server = server

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        process: asyncio.subprocess.Process | None = None
        try:
            async with asyncio.timeout(MCP_TIMEOUT_SECONDS):
                process = await asyncio.create_subprocess_exec(
                    *self._server.command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    env={**os.environ, **self._server.environment},
                )
                await self._send(process, 1, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "insighthub-chatops", "version": "1.0"}})
                await self._receive(process, 1)
                await self._notify(process, "notifications/initialized", {})
                await self._send(process, 2, "tools/call", {"name": name, "arguments": arguments})
                response = await self._receive(process, 2)
            result = response.get("result")
            if not isinstance(result, dict) or result.get("isError"):
                raise McpError("MCP_UNAVAILABLE")
            structured = result.get("structuredContent")
            if isinstance(structured, dict):
                return structured
            content = result.get("content")
            if isinstance(content, list) and content and isinstance(content[0], dict) and isinstance(content[0].get("text"), str):
                parsed = json.loads(content[0]["text"])
                if isinstance(parsed, dict):
                    return parsed
            raise McpError("MCP_UNAVAILABLE")
        except (asyncio.TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise McpError("MCP_UNAVAILABLE") from exc
        finally:
            if process is not None and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=1)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()

    async def _send(self, process: asyncio.subprocess.Process, request_id: int, method: str, params: dict[str, Any]) -> None:
        assert process.stdin is not None
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}, separators=(",", ":")).encode() + b"\n")
        await process.stdin.drain()

    async def _notify(self, process: asyncio.subprocess.Process, method: str, params: dict[str, Any]) -> None:
        assert process.stdin is not None
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params}, separators=(",", ":")).encode() + b"\n")
        await process.stdin.drain()

    async def _receive(self, process: asyncio.subprocess.Process, request_id: int) -> dict[str, Any]:
        assert process.stdout is not None
        while True:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=MCP_TIMEOUT_SECONDS)
            if not line:
                raise McpError("MCP_UNAVAILABLE")
            message = json.loads(line)
            if message.get("id") == request_id:
                if "error" in message:
                    raise McpError("MCP_UNAVAILABLE")
                return message
