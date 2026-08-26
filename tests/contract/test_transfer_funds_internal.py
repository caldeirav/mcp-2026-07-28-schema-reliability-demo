"""Contract tests: internal transfer_funds against JSON Schema 2020-12."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1].parent
    / "src"
    / "mcp"
    / "schemas"
    / "transfer_funds.strict.json"
)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_valid_internal_under_threshold(validator: Draft202012Validator) -> None:
    payload = {
        "transfer_type": "internal",
        "source_account": "ACC1001",
        "destination_account": "ACC2002",
        "amount": 10000,
    }
    validator.validate(payload)


def test_internal_does_not_require_iban(validator: Draft202012Validator) -> None:
    payload = {
        "transfer_type": "internal",
        "source_account": "ACC1001",
        "destination_account": "ACC2002",
        "amount": 50.25,
    }
    validator.validate(payload)


def test_missing_transfer_type_fails(validator: Draft202012Validator) -> None:
    payload = {
        "source_account": "ACC1001",
        "destination_account": "ACC2002",
        "amount": 100,
    }
    errors = list(validator.iter_errors(payload))
    assert errors


def test_invalid_transfer_type_fails(validator: Draft202012Validator) -> None:
    payload = {
        "transfer_type": "swift",
        "source_account": "ACC1001",
        "destination_account": "ACC2002",
        "amount": 100,
    }
    errors = list(validator.iter_errors(payload))
    assert errors
