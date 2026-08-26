"""MCP 2026-07-28 headers: required names present, no Mcp-Session-Id."""

from __future__ import annotations

from mcp_client import mcp_headers


def test_required_headers_present() -> None:
    headers = mcp_headers("tools/call", "transfer_funds")
    assert headers["Mcp-Protocol-Version"] == "2026-07-28"
    assert headers["Mcp-Method"] == "tools/call"
    assert headers["Mcp-Name"] == "transfer_funds"
    assert "application/json" in headers["Accept"]
    assert "text/event-stream" in headers["Accept"]
    assert "Mcp-Session-Id" not in headers
    assert not any(k.lower() == "mcp-session-id" for k in headers)
