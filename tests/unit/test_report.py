"""Compact comparison stdout: summary line plus per-call hops."""

from __future__ import annotations

from mcp_client import ToolCallResult
from repair import ERROR_32602, ERROR_NONE, ERROR_OPAQUE
from report import CallHop, ComparisonReport, compact_args, hop_from_tool_result


def test_compact_args_stable_order() -> None:
    rendered = compact_args(
        {
            "amount": 12500,
            "compliance_approval_code": "CMP-DEMO-2026",
            "transfer_type": "internal",
            "destination_account": "ACC2002",
            "source_account": "ACC1001",
        }
    )
    assert rendered.startswith("{transfer_type=internal, source_account=ACC1001")
    assert "compliance_approval_code=CMP-DEMO-2026" in rendered


def test_format_includes_http_and_rpc() -> None:
    result = ToolCallResult(
        ok=False,
        error_kind=ERROR_32602,
        arguments={"transfer_type": "internal", "amount": 12500, "source_account": "ACC1001"},
        message="(root): 'compliance_approval_code' is a required property",
        raw={"error": {"code": -32602, "message": "invalid params"}},
        url="http://127.0.0.1:8080/mcp/strict",
        http_status=200,
    )
    hop = hop_from_tool_result(result)
    report = ComparisonReport(
        contract_mode="strict",
        error_kind=ERROR_32602,
        repair_attempts=1,
        transfer_recorded=False,
        hops=[hop],
    )
    text = report.format()
    assert text.startswith("[strict] error_kind=-32602 repair_attempts=1 recorded=no")
    assert "POST /mcp/strict" in text
    assert "http=200" in text
    assert "rpc=-32602" in text
    assert "amount=12500" in text
    assert "compliance_approval_code" in result.message


def test_format_success_hop_shows_transfer_id() -> None:
    hop = CallHop(
        url="http://127.0.0.1:8080/mcp/legacy",
        http_status=200,
        rpc_code="-",
        arguments={"transfer_type": "internal", "amount": 50},
        error_kind=ERROR_NONE,
        message="",
        transfer_id="tid-9",
    )
    report = ComparisonReport(
        contract_mode="legacy",
        error_kind=ERROR_OPAQUE,
        repair_attempts=0,
        transfer_recorded=False,
        hops=[hop],
    )
    line = report.format().splitlines()[1]
    assert "http=200" in line
    assert "rpc=-" in line
    assert "resp=ok transfer_id=tid-9" in line
