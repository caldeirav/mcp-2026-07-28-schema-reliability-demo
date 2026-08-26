"""Fail-fast environment loader. Contract mode is never read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
_REQUIRED = (
    "MODEL_NAME",
    "LM_STUDIO_BASE_URL",
    "AGENTGATEWAY_URL",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
)


@dataclass(frozen=True)
class Settings:
    model_name: str
    lm_studio_base_url: str
    agentgateway_url: str
    otel_endpoint: str
    repair_budget: int
    openai_api_key: str

    @property
    def chat_base_url(self) -> str:
        return f"{self.agentgateway_url.rstrip('/')}/v1"

    def mcp_url(self, contract_mode: str) -> str:
        if contract_mode not in {"legacy", "strict"}:
            raise ValueError("contract_mode must be legacy or strict")
        return f"{self.agentgateway_url.rstrip('/')}/mcp/{contract_mode}"


def load_settings() -> Settings:
    load_dotenv(_ROOT / ".env")
    missing = [name for name in _REQUIRED if not os.getenv(name)]
    if missing:
        raise SystemExit(f"missing required environment variables: {', '.join(missing)}")
    if os.getenv("CONTRACT_MODE"):
        raise SystemExit("CONTRACT_MODE must not be set; pass --contract on the CLI")
    budget_raw = os.getenv("REPAIR_BUDGET", "3")
    try:
        budget = int(budget_raw)
    except ValueError as exc:
        raise SystemExit("REPAIR_BUDGET must be an integer") from exc
    return Settings(
        model_name=os.environ["MODEL_NAME"],
        lm_studio_base_url=os.environ["LM_STUDIO_BASE_URL"],
        agentgateway_url=os.environ["AGENTGATEWAY_URL"],
        otel_endpoint=os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"],
        repair_budget=budget,
        openai_api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
    )
