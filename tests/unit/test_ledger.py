"""Ledger unit tests. Gateway bypass is documented: this tests tool-layer defense in depth only."""

from __future__ import annotations

import pytest

from ledger import COMPLIANCE_CODE, Ledger


def test_records_internal_under_threshold() -> None:
    ledger = Ledger()
    row = ledger.record(
        {
            "transfer_type": "internal",
            "source_account": "ACC1001",
            "destination_account": "ACC2002",
            "amount": 100.00,
        }
    )
    assert row.transfer_type == "internal"
    assert ledger.count() == 1


def test_rejects_missing_discriminator() -> None:
    ledger = Ledger()
    with pytest.raises(ValueError):
        ledger.record(
            {
                "source_account": "ACC1001",
                "destination_account": "ACC2002",
                "amount": 100,
            }
        )
    assert ledger.count() == 0


def test_rejects_high_value_without_code() -> None:
    ledger = Ledger()
    with pytest.raises(ValueError, match="compliance"):
        ledger.record(
            {
                "transfer_type": "internal",
                "source_account": "ACC1001",
                "destination_account": "ACC2002",
                "amount": 10000.01,
            }
        )
    assert ledger.count() == 0


def test_rejects_invented_compliance_code() -> None:
    ledger = Ledger()
    with pytest.raises(ValueError, match="compliance"):
        ledger.record(
            {
                "transfer_type": "internal",
                "source_account": "ACC1001",
                "destination_account": "ACC2002",
                "amount": 10000.01,
                "compliance_approval_code": "HACKED",
            }
        )
    assert ledger.count() == 0


def test_records_high_value_with_published_code() -> None:
    ledger = Ledger()
    row = ledger.record(
        {
            "transfer_type": "internal",
            "source_account": "ACC1001",
            "destination_account": "ACC2002",
            "amount": 10000.01,
            "compliance_approval_code": COMPLIANCE_CODE,
        }
    )
    assert row.amount == 10000.01
