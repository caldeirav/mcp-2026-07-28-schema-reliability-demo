"""FastMCP strict server: JSON Schema 2020-12 transfer_funds on 127.0.0.1:8001/mcp."""

from __future__ import annotations

from typing import Any

import protocol_compat  # noqa: F401  # accept Mcp-Protocol-Version 2026-07-28
from fastmcp import FastMCP
from jsonschema.exceptions import ValidationError
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData

from ledger import Ledger
from schema_loader import load_schema
from tooling import assemble_arguments, tool_with_schema
from validation import format_validation_error, validate_payload

STRICT_SCHEMA = load_schema("transfer_funds.strict.json")
LEDGER = Ledger()

mcp = FastMCP("banking-strict")

_DESCRIPTION = (
    "Record a simulated bank transfer. transfer_type is internal or wire. "
    "Amounts over 10000 require compliance_approval_code CMP-DEMO-2026. "
    "Wire transfers require iban and swift."
)


def transfer_funds(
    transfer_type: str | None = None,
    source_account: str | None = None,
    destination_account: str | None = None,
    iban: str | None = None,
    swift: str | None = None,
    amount: float | None = None,
    compliance_approval_code: str | None = None,
) -> dict[str, Any]:
    """Move simulated funds. Arguments must match the 2020-12 schema."""
    arguments = assemble_arguments(
        transfer_type=transfer_type,
        source_account=source_account,
        destination_account=destination_account,
        iban=iban,
        swift=swift,
        amount=amount,
        compliance_approval_code=compliance_approval_code,
    )
    try:
        validate_payload(arguments, STRICT_SCHEMA)
    except ValidationError as exc:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=format_validation_error(exc),
            )
        ) from exc
    try:
        confirmation = LEDGER.record(arguments)
    except ValueError as exc:
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=str(exc))
        ) from exc
    return confirmation.as_dict()


mcp.add_tool(tool_with_schema(transfer_funds, STRICT_SCHEMA, _DESCRIPTION))


def main() -> None:
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8001,
        path="/mcp",
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
