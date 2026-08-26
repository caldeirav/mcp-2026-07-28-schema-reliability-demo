"""Assemble transfer_funds arguments without **kwargs (FastMCP forbids them)."""

from __future__ import annotations

from typing import Any

from fastmcp.tools import Tool


def assemble_arguments(
    transfer_type: str | None = None,
    source_account: str | None = None,
    destination_account: str | None = None,
    iban: str | None = None,
    swift: str | None = None,
    amount: float | None = None,
    compliance_approval_code: str | None = None,
) -> dict[str, Any]:
    raw = {
        "transfer_type": transfer_type,
        "source_account": source_account,
        "destination_account": destination_account,
        "iban": iban,
        "swift": swift,
        "amount": amount,
        "compliance_approval_code": compliance_approval_code,
    }
    return {key: value for key, value in raw.items() if value is not None}


def tool_with_schema(fn: Any, schema: dict[str, Any], description: str) -> Tool:
    tool = Tool.from_function(
        fn,
        name="transfer_funds",
        description=description,
    )
    tool.parameters = schema
    return tool
