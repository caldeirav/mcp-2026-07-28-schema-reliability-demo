"""Contract tests: amount > 10000 requires const CMP-DEMO-2026."""

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


def _internal(**extra):
    payload = {
        "transfer_type": "internal",
        "source_account": "ACC1001",
        "destination_account": "ACC2002",
        "amount": 10000.01,
    }
    payload.update(extra)
    return payload


def test_over_threshold_without_code_fails() -> None:
    assert list(VALIDATOR.iter_errors(_internal()))


def test_over_threshold_invented_code_fails() -> None:
    assert list(VALIDATOR.iter_errors(_internal(compliance_approval_code="HACKED")))


def test_over_threshold_published_code_passes() -> None:
    VALIDATOR.validate(_internal(compliance_approval_code="CMP-DEMO-2026"))


def test_exactly_10000_does_not_require_code() -> None:
    VALIDATOR.validate(
        {
            "transfer_type": "internal",
            "source_account": "ACC1001",
            "destination_account": "ACC2002",
            "amount": 10000,
        }
    )
