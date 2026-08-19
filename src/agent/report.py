"""Labeled comparison report for stdout."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComparisonReport:
    contract_mode: str
    error_kind: str
    repair_attempts: int
    transfer_recorded: bool
    transfer_id: str | None = None

    def format(self) -> str:
        recorded = "yes" if self.transfer_recorded else "no"
        tid = self.transfer_id or "-"
        return (
            f"[{self.contract_mode}] error_kind={self.error_kind} "
            f"repair_attempts={self.repair_attempts} recorded={recorded} "
            f"transfer_id={tid}"
        )
