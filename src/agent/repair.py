"""Classify MCP tool results and forbid identical -32602 retries."""

from __future__ import annotations

import hashlib
import json
from typing import Any

ERROR_NONE = "none"
ERROR_32602 = "-32602"
ERROR_OPAQUE = "opaque"
ERROR_OTHER = "other"

COMPLIANCE_CODE = "CMP-DEMO-2026"


def fingerprint(arguments: dict[str, Any]) -> str:
    canonical = json.dumps(arguments, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def classify_rpc_error(payload: dict[str, Any] | None, http_ok: bool) -> str:
    if payload is None:
        return ERROR_OTHER
    err = payload.get("error")
    if isinstance(err, dict) and err.get("code") == -32602:
        return ERROR_32602
    result = payload.get("result")
    if payload.get("isError") is True:
        return ERROR_OPAQUE
    if isinstance(result, dict) and result.get("isError"):
        return ERROR_OPAQUE
    if err:
        return ERROR_OTHER
    if not http_ok:
        return ERROR_OTHER
    return ERROR_NONE


def identical_retry_forbidden(
    previous_fingerprint: str | None,
    arguments: dict[str, Any],
    error_kind: str,
) -> bool:
    if error_kind != ERROR_32602 or not previous_fingerprint:
        return False
    return fingerprint(arguments) == previous_fingerprint


def apply_compliance_from_prompt(arguments: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Copy the published demo code from the prompt into a changed payload."""
    if COMPLIANCE_CODE not in prompt:
        return dict(arguments)
    updated = dict(arguments)
    updated["compliance_approval_code"] = COMPLIANCE_CODE
    return updated
