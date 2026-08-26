"""First tools/call withholds compliance_approval_code so compare.sh is deterministic."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from config import Settings
from graph import first_tool_arguments, run_repair_loop
from mcp_client import ToolCallResult
from repair import COMPLIANCE_CODE, ERROR_32602, ERROR_NONE, ERROR_OPAQUE

SETTINGS = Settings(
    model_name="qwen/qwen3.8-27b",
    lm_studio_base_url="http://127.0.0.1:1234/v1",
    agentgateway_url="http://127.0.0.1:8080",
    otel_endpoint="http://127.0.0.1:4317",
    repair_budget=3,
    openai_api_key="lm-studio",
)

PROMPT = "Transfer 12500 internal ACC1001 to ACC2002. Code CMP-DEMO-2026."
LEGAL = {
    "transfer_type": "internal",
    "source_account": "ACC1001",
    "destination_account": "ACC2002",
    "amount": 12500,
    "compliance_approval_code": COMPLIANCE_CODE,
}


class _ModelAlwaysIncludesCode:
    """Stand-in for a capable local model that copies CMP-DEMO-2026 immediately."""

    def bind_tools(self, _tools):
        return self

    def invoke(self, _messages):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "transfer_funds",
                    "id": "call-1",
                    "args": dict(LEGAL),
                }
            ],
        )


def _fake_call(url: str, arguments: dict) -> ToolCallResult:
    if "/mcp/legacy" in url:
        if arguments.get("compliance_approval_code") == COMPLIANCE_CODE:
            return ToolCallResult(
                ok=True,
                error_kind=ERROR_NONE,
                arguments=arguments,
                confirmation={"transfer_id": "legacy-legal"},
                url=url,
            )
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


def test_first_call_drops_compliance_code() -> None:
    with_code = first_tool_arguments(LEGAL, 0)
    assert "compliance_approval_code" not in with_code
    repaired = first_tool_arguments(LEGAL, 1)
    assert repaired["compliance_approval_code"] == COMPLIANCE_CODE


def test_capable_model_still_shows_legacy_opaque_strict_repair() -> None:
    llm = _ModelAlwaysIncludesCode()
    legacy = run_repair_loop(
        "legacy",
        PROMPT,
        SETTINGS,
        call_fn=_fake_call,
        llm=llm,
    )
    assert legacy.error_kind == ERROR_OPAQUE
    assert legacy.transfer_recorded is False
    assert legacy.repair_attempts == 0

    strict = run_repair_loop(
        "strict",
        PROMPT,
        SETTINGS,
        call_fn=_fake_call,
        llm=llm,
    )
    assert strict.error_kind == ERROR_NONE
    assert strict.transfer_recorded is True
    assert strict.repair_attempts >= 1
    assert strict.transfer_id == "tid-1"
