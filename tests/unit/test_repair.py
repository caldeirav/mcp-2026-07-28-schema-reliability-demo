"""Unit tests for -32602 classification, fingerprints, and identical-retry guard."""

from __future__ import annotations

from repair import (
    COMPLIANCE_CODE,
    ERROR_32602,
    ERROR_OPAQUE,
    apply_compliance_from_prompt,
    classify_rpc_error,
    fingerprint,
    identical_retry_forbidden,
)


def test_classifies_32602() -> None:
    assert classify_rpc_error({"error": {"code": -32602, "message": "x"}}, True) == ERROR_32602


def test_classifies_opaque_tool_error() -> None:
    assert (
        classify_rpc_error({"result": {"isError": True, "content": []}}, True) == ERROR_OPAQUE
    )


def test_fingerprint_stable() -> None:
    a = {"amount": 1, "transfer_type": "internal"}
    b = {"transfer_type": "internal", "amount": 1}
    assert fingerprint(a) == fingerprint(b)


def test_identical_retry_forbidden_on_32602() -> None:
    args = {"amount": 12500, "transfer_type": "internal"}
    fp = fingerprint(args)
    assert identical_retry_forbidden(fp, args, ERROR_32602)
    assert not identical_retry_forbidden(fp, {**args, "compliance_approval_code": COMPLIANCE_CODE}, ERROR_32602)


def test_apply_compliance_from_prompt_copies_published_code() -> None:
    prompt = "Use CMP-DEMO-2026 please"
    args = {"transfer_type": "internal", "amount": 12500}
    updated = apply_compliance_from_prompt(args, prompt)
    assert updated["compliance_approval_code"] == COMPLIANCE_CODE
    assert fingerprint(updated) != fingerprint(args)
