"""Legacy description-only schema must admit illegal high-value payloads."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1].parent
    / "src"
    / "mcp"
    / "schemas"
    / "transfer_funds.legacy.json"
)
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_legacy_admits_high_value_without_code() -> None:
    VALIDATOR.validate(
        {
            "transfer_type": "internal",
            "source_account": "ACC1001",
            "destination_account": "ACC2002",
            "amount": 12500,
        }
    )


def test_legacy_admits_missing_discriminator() -> None:
    VALIDATOR.validate({"amount": 12500})
