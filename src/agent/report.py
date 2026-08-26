"""Labeled comparison report for stdout."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


_ARG_ORDER = (
    "transfer_type",
    "source_account",
    "destination_account",
    "iban",
    "swift",
    "amount",
    "compliance_approval_code",
)
_RESP_MAX = 120


@dataclass(frozen=True)
class CallHop:
    """One tools/call round trip through the gateway."""

    url: str
    http_status: int | None
    rpc_code: str
    arguments: dict[str, Any]
    error_kind: str
    message: str
    transfer_id: str | None = None


@dataclass
class ComparisonReport:
    contract_mode: str
    error_kind: str
    repair_attempts: int
    transfer_recorded: bool
    transfer_id: str | None = None
    hops: list[CallHop] = field(default_factory=list)

    def format(self) -> str:
        recorded = "yes" if self.transfer_recorded else "no"
        tid = self.transfer_id or "-"
        lines = [
            f"[{self.contract_mode}] error_kind={self.error_kind} "
            f"repair_attempts={self.repair_attempts} recorded={recorded} "
            f"transfer_id={tid}"
        ]
        for index, hop in enumerate(self.hops, start=1):
            lines.append(f"  {index}. {_format_hop(hop)}")
        return "\n".join(lines)


def hop_from_tool_result(result: Any) -> CallHop:
    """Build a CallHop from a ToolCallResult (duck-typed to avoid import cycles)."""
    raw = result.raw if isinstance(getattr(result, "raw", None), dict) else {}
    err = raw.get("error") if isinstance(raw, dict) else None
    rpc = "-"
    if isinstance(err, dict) and err.get("code") is not None:
        rpc = str(err["code"])
    elif getattr(result, "error_kind", "") == "-32602":
        rpc = "-32602"
    confirmation = getattr(result, "confirmation", None) or {}
    tid = confirmation.get("transfer_id") if isinstance(confirmation, dict) else None
    return CallHop(
        url=str(getattr(result, "url", "") or ""),
        http_status=getattr(result, "http_status", None),
        rpc_code=rpc,
        arguments=dict(getattr(result, "arguments", None) or {}),
        error_kind=str(getattr(result, "error_kind", "") or "-"),
        message=str(getattr(result, "message", "") or ""),
        transfer_id=str(tid) if tid else None,
    )


def compact_args(arguments: dict[str, Any]) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for key in _ARG_ORDER:
        if key in arguments and arguments[key] is not None and arguments[key] != "":
            parts.append(f"{key}={arguments[key]}")
            seen.add(key)
    for key, value in arguments.items():
        if key in seen or value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    return "{" + ", ".join(parts) + "}"


def _format_hop(hop: CallHop) -> str:
    path = urlparse(hop.url).path or hop.url or "-"
    http = str(hop.http_status) if hop.http_status is not None else "-"
    resp = _compact_resp(hop)
    return (
        f"POST {path}  http={http}  rpc={hop.rpc_code}  "
        f"args={compact_args(hop.arguments)}  resp={resp}"
    )


def _compact_resp(hop: CallHop) -> str:
    if hop.transfer_id:
        return f"ok transfer_id={hop.transfer_id}"
    text = " ".join(hop.message.split())
    if not text:
        return "-"
    if len(text) > _RESP_MAX:
        text = text[: _RESP_MAX - 1] + "…"
    return f'"{text}"'
