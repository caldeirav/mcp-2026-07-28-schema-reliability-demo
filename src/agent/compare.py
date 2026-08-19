"""Comparison CLI: --contract legacy|strict|both (never from .env)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import load_settings
from graph import run_repair_loop
from report import ComparisonReport

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROMPT = _ROOT / "prompts" / "high_value_internal.txt"
_MODES = ("legacy", "strict", "both")


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare legacy vs strict transfer_funds contracts")
    parser.add_argument(
        "--contract",
        required=True,
        help="legacy | strict | both",
    )
    parser.add_argument("--prompt", type=Path, default=_DEFAULT_PROMPT)
    args = parser.parse_args(argv)
    if args.contract not in _MODES:
        raise SystemExit("invalid --contract; use legacy, strict, or both")
    return args


def _modes(contract: str) -> tuple[str, ...]:
    if contract == "both":
        return ("legacy", "strict")
    return (contract,)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    settings = load_settings()
    prompt_path: Path = args.prompt
    if not prompt_path.is_file():
        raise SystemExit(f"prompt file not found: {prompt_path}")
    prompt = prompt_path.read_text(encoding="utf-8")
    reports: list[ComparisonReport] = []
    for mode in _modes(args.contract):
        report = run_repair_loop(mode, prompt, settings)
        reports.append(report)
        print(report.format())
    return 0


if __name__ == "__main__":
    sys.exit(main())
