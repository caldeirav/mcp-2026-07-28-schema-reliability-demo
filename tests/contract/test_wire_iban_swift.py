"""Contract tests: wire oneOf IBAN/SWIFT patterns; no MOD-97 checksum."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1].parent
    / "src"
    / "mcp"
    / "schemas"
    / "transfer_funds.strict.json"
)
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))

# Pattern-valid; would fail ISO 13616 MOD-97 (check digits 00).
PATTERN_VALID_BAD_CHECKSUM = "DE00ZZ012345678901"


def test_valid_wire_records_shape() -> None:
    VALIDATOR.validate(
        {
            "transfer_type": "wire",
            "source_account": "ACC1001",
            "iban": "DE91100000000123456789",
            "swift": "COBADEFFXXX",
            "amount": 250.50,
        }
    )


def test_malformed_iban_fails() -> None:
    errors = list(
        VALIDATOR.iter_errors(
            {
                "transfer_type": "wire",
                "source_account": "ACC1001",
                "iban": "not-an-iban",
                "swift": "COBADEFF",
                "amount": 10,
            }
        )
    )
    assert errors


def test_internal_shape_labeled_wire_fails() -> None:
    errors = list(
        VALIDATOR.iter_errors(
            {
                "transfer_type": "wire",
                "source_account": "ACC1001",
                "destination_account": "ACC2002",
                "amount": 10,
            }
        )
    )
    assert errors


def test_pattern_valid_checksum_invalid_iban_is_accepted() -> None:
    VALIDATOR.validate(
        {
            "transfer_type": "wire",
            "source_account": "ACC1001",
            "iban": PATTERN_VALID_BAD_CHECKSUM,
            "swift": "COBADEFF",
            "amount": 10,
        }
    )
