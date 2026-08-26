"""Integration: compare both — legacy opaque vs strict -32602 repair (mocked MCP)."""

from __future__ import annotations

from config import Settings
from graph import run_repair_loop
from mcp_client import ToolCallResult
from repair import ERROR_32602, ERROR_NONE, ERROR_OPAQUE, COMPLIANCE_CODE


SETTINGS = Settings(
    model_name="qwen/qwen3.8-27b",
    lm_studio_base_url="http://127.0.0.1:1234/v1",
    agentgateway_url="http://127.0.0.1:8080",
    otel_endpoint="http://127.0.0.1:4317",
    repair_budget=3,
    openai_api_key="lm-studio",
)

PROMPT = "Transfer 12500 internal ACC1001 to ACC2002. Code CMP-DEMO-2026."
BASE = {
    "transfer_type": "internal",
    "source_account": "ACC1001",
    "destination_account": "ACC2002",
    "amount": 12500,
}


def _fake_call(url: str, arguments: dict) -> ToolCallResult:
    if "/mcp/legacy" in url:
        return ToolCallResult(
            ok=False,
            error_kind=ERROR_OPAQUE,
            arguments=arguments,
            message="transfer rejected",
            url=url,
        )
    if arguments.get("compliance_approval_code") == COMPLIANCE_CODE:
        return ToolCallResult(
            ok=True,
            error_kind=ERROR_NONE,
            arguments=arguments,
            confirmation={"transfer_id": "tid-1", "amount": 12500, "transfer_type": "internal"},
            url=url,
        )
    return ToolCallResult(
        ok=False,
        error_kind=ERROR_32602,
        arguments=arguments,
        message="(root): required: compliance_approval_code",
        url=url,
    )


def test_both_legacy_opaque_strict_repairs() -> None:
    legacy = run_repair_loop(
        "legacy",
        PROMPT,
        SETTINGS,
        call_fn=_fake_call,
        initial_arguments=BASE,
    )
    assert legacy.error_kind == ERROR_OPAQUE
    assert legacy.transfer_recorded is False
    assert legacy.repair_attempts == 0

    strict = run_repair_loop(
        "strict",
        PROMPT,
        SETTINGS,
        call_fn=_fake_call,
        initial_arguments=BASE,
    )
    assert strict.error_kind == ERROR_NONE
    assert strict.transfer_recorded is True
    assert strict.repair_attempts >= 1
    assert strict.transfer_id == "tid-1"
