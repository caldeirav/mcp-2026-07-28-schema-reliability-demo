"""JSON Schema 2020-12 validation for transfer_funds payloads."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from schema_loader import load_schema

STRICT_SCHEMA = load_schema("transfer_funds.strict.json")
LEGACY_SCHEMA = load_schema("transfer_funds.legacy.json")


def validate_payload(payload: Any, schema: dict[str, Any]) -> None:
    Draft202012Validator(schema).validate(payload)


def strict_errors(payload: Any) -> list[str]:
    validator = Draft202012Validator(STRICT_SCHEMA)
    return [e.message for e in validator.iter_errors(payload)]


def format_validation_error(exc: ValidationError) -> str:
    path = ".".join(str(p) for p in exc.absolute_path) or "(root)"
    return f"{path}: {exc.message}"
