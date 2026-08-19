"""FastMCP legacy server: description-only schema on 127.0.0.1:8002/mcp.

Illegal payloads are not recorded. Failures are opaque ToolError strings,
not JSON-RPC -32602, so the agent must not start the schema-repair loop.
"""

from __future__ import annotations

from typing import Any

import protocol_compat  # noqa: F401  # accept Mcp-Protocol-Version 2026-07-28
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ledger import Ledger
from schema_loader import load_schema
from tooling import assemble_arguments, tool_with_schema

LEGACY_SCHEMA = load_schema("transfer_funds.legacy.json")
LEDGER = Ledger()

mcp = FastMCP("banking-legacy")

_DESCRIPTION = (
    "Record a simulated bank transfer. Use internal for same-bank or wire "
    "for international. Amounts over 10000 need a compliance approval code. "
    "Wire transfers need IBAN and SWIFT."
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
    """Move simulated funds. Follow the field descriptions."""
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
        confirmation = LEDGER.record(arguments)
    except (ValueError, TypeError) as exc:
        raise ToolError("transfer rejected") from exc
    return confirmation.as_dict()


mcp.add_tool(tool_with_schema(transfer_funds, LEGACY_SCHEMA, _DESCRIPTION))


def main() -> None:
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8002,
        path="/mcp",
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
