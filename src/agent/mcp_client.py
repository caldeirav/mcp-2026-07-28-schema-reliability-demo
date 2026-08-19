"""MCP 2026-07-28 Streamable HTTP client. All calls go through agentgateway."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from repair import ERROR_32602, ERROR_NONE, ERROR_OPAQUE, ERROR_OTHER, classify_rpc_error

PROTOCOL = "2026-07-28"


@dataclass
class ToolCallResult:
    ok: bool
    error_kind: str
    arguments: dict[str, Any]
    message: str = ""
    confirmation: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    request_headers: dict[str, str] = field(default_factory=dict)
    url: str = ""


def mcp_headers(method: str, name: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Protocol-Version": PROTOCOL,
        "Mcp-Method": method,
        "Mcp-Name": name,
    }


def _meta() -> dict[str, Any]:
    return {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL,
        "io.modelcontextprotocol/clientInfo": {
            "name": "banking-fund-transfer-demo",
            "version": "0.1.0",
        },
        "io.modelcontextprotocol/clientCapabilities": {},
        "protocolVersion": PROTOCOL,
        "clientInfo": {"name": "banking-fund-transfer-demo", "version": "0.1.0"},
        "clientCapabilities": {},
    }


def parse_mcp_http_body(text: str) -> dict[str, Any]:
    """Parse a JSON-RPC object from JSON or Streamable HTTP SSE."""
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped.startswith("{") or stripped.startswith("["):
        loaded = json.loads(stripped)
        return loaded if isinstance(loaded, dict) else {}
    chunks: list[str] = []
    for line in stripped.splitlines():
        if line.startswith("data:"):
            chunks.append(line[5:].lstrip())
    blob = "\n".join(chunks).strip()
    if not blob:
        return {}
    loaded = json.loads(blob)
    return loaded if isinstance(loaded, dict) else {}


def _confirmation_from_result(result: dict[str, Any]) -> dict[str, Any] | None:
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and "transfer_id" in structured:
        return structured
    if "transfer_id" in result:
        return result
    for block in result.get("content") or []:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if not isinstance(text, str) or not text.lstrip().startswith("{"):
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "transfer_id" in parsed:
            return parsed
    return None


def _result_is_error(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("isError") or result.get("is_error"):
        return True
    for block in result.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            text = str(block.get("text") or "")
            if text.startswith("transfer rejected") or text.startswith("Error calling tool"):
                return True
    return False


def _looks_like_schema_error(message: str) -> bool:
    lowered = message.lower()
    return "error calling tool" in lowered and (
        "required" in lowered or "(root)" in lowered or "is not valid" in lowered
    )


def call_transfer_funds(
    gateway_mcp_url: str,
    arguments: dict[str, Any],
    *,
    client: httpx.Client | None = None,
) -> ToolCallResult:
    if ":8001" in gateway_mcp_url or ":8002" in gateway_mcp_url:
        raise RuntimeError("MCP client must not bypass agentgateway (:8001/:8002)")
    headers = mcp_headers("tools/call", "transfer_funds")
    body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": "transfer_funds",
            "arguments": arguments,
            "_meta": _meta(),
        },
        "_meta": _meta(),
    }
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.post(gateway_mcp_url, json=body, headers=headers)
    finally:
        if client is None:
            http.close()
    try:
        payload = parse_mcp_http_body(response.text)
    except (ValueError, json.JSONDecodeError):
        payload = {}
    if _result_is_error(payload.get("result")):
        payload = {**payload, "result": {**(payload.get("result") or {}), "isError": True}}
    kind = classify_rpc_error(payload if payload else None, response.is_success)
    confirmation = None
    message = ""
    if kind == ERROR_32602:
        err = payload.get("error") or {}
        message = str(err.get("message") or "invalid params")
    elif kind in {ERROR_OPAQUE, ERROR_OTHER}:
        err = payload.get("error") or {}
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        texts = []
        for block in (result or {}).get("content") or []:
            if isinstance(block, dict) and block.get("text"):
                texts.append(str(block["text"]))
        message = str(err.get("message") or " ".join(texts) or response.text)
        # FastMCP wraps McpError(INVALID_PARAMS) as isError text. Promote
        # schema-shaped failures to the -32602 repair path (legacy stays opaque).
        if kind == ERROR_OPAQUE and _looks_like_schema_error(message):
            kind = ERROR_32602
        if kind == ERROR_OTHER and response.is_success:
            confirmation = _confirmation_from_result(result or {})
            if confirmation:
                kind = ERROR_NONE
    elif kind == ERROR_NONE:
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        confirmation = _confirmation_from_result(result or {})
    ok = kind == ERROR_NONE and confirmation is not None
    if ok:
        kind = ERROR_NONE
    return ToolCallResult(
        ok=ok,
        error_kind=kind,
        arguments=arguments,
        message=message,
        confirmation=confirmation if isinstance(confirmation, dict) else None,
        raw=payload,
        request_headers=headers,
        url=gateway_mcp_url,
    )
