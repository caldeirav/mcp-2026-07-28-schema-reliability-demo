"""SSE / Streamable HTTP body parsing for the MCP client."""

from __future__ import annotations

from mcp_client import parse_mcp_http_body


def test_parse_plain_json() -> None:
    payload = parse_mcp_http_body('{"jsonrpc":"2.0","error":{"code":-32602,"message":"x"}}')
    assert payload["error"]["code"] == -32602


def test_parse_sse_message() -> None:
    body = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","result":{"isError":true,'
        '"content":[{"type":"text","text":"transfer rejected"}]}}\n\n'
    )
    payload = parse_mcp_http_body(body)
    assert payload["result"]["isError"] is True
