"""Ephemeral in-memory ledger. Never records an illegal payload.

Gateway-bypass note: unit tests import this module directly. Production traffic
MUST go through agentgateway; this module is tool-layer defense in depth.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

COMPLIANCE_CODE = "CMP-DEMO-2026"
ACCOUNT_RE = re.compile(r"^[A-Za-z0-9]{6,34}$")
IBAN_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$")
SWIFT_RE = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")


@dataclass(frozen=True)
class TransferConfirmation:
    transfer_id: str
    transfer_type: str
    amount: float
    destination_summary: str
    timestamp: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "transfer_type": self.transfer_type,
            "amount": self.amount,
            "destination_summary": self.destination_summary,
            "timestamp": self.timestamp,
        }


def _amount_ok(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    if value <= 0:
        return False
    scaled = round(float(value) * 100)
    return abs(float(value) * 100 - scaled) < 1e-9


def business_illegal_reason(payload: dict[str, Any]) -> str | None:
    """Return a reason if the payload must not be recorded; None if legal."""
    transfer_type = payload.get("transfer_type")
    if transfer_type not in {"internal", "wire"}:
        return "discriminator: transfer_type must be exactly internal or wire"
    amount = payload.get("amount")
    if not _amount_ok(amount):
        return "amount must be a finite number greater than 0 with at most two decimal places"
    source = payload.get("source_account")
    if not isinstance(source, str) or not ACCOUNT_RE.fullmatch(source):
        return "source_account must be 6-34 alphanumeric characters"
    if float(amount) > 10000:
        code = payload.get("compliance_approval_code")
        if not isinstance(code, str) or not code.strip() or code != COMPLIANCE_CODE:
            return "compliance: amounts over 10000 require compliance_approval_code CMP-DEMO-2026"
    if transfer_type == "internal":
        dest = payload.get("destination_account")
        if not isinstance(dest, str) or not ACCOUNT_RE.fullmatch(dest):
            return "internal transfers require destination_account"
    else:
        iban = payload.get("iban")
        swift = payload.get("swift")
        if not isinstance(iban, str) or not IBAN_RE.fullmatch(iban):
            return "wire transfers require a structural IBAN pattern"
        if not isinstance(swift, str) or not SWIFT_RE.fullmatch(swift):
            return "wire transfers require SWIFT/BIC of 8 or 11 alphanumeric characters"
        if payload.get("destination_account") and not iban:
            return "internal destination_account does not satisfy a wire request"
    return None


@dataclass
class Ledger:
    _rows: list[TransferConfirmation] = field(default_factory=list)

    def record(self, payload: dict[str, Any]) -> TransferConfirmation:
        reason = business_illegal_reason(payload)
        if reason:
            raise ValueError(reason)
        transfer_type = str(payload["transfer_type"])
        amount = float(payload["amount"])
        if transfer_type == "internal":
            destination = str(payload["destination_account"])
        else:
            destination = str(payload["iban"])
        confirmation = TransferConfirmation(
            transfer_id=str(uuid.uuid4()),
            transfer_type=transfer_type,
            amount=amount,
            destination_summary=destination,
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._rows.append(confirmation)
        return confirmation

    def count(self) -> int:
        return len(self._rows)
