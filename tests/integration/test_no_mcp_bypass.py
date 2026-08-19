"""Tool traffic must target agentgateway, never FastMCP loopback ports."""

from __future__ import annotations

import pytest

from config import Settings
from mcp_client import call_transfer_funds


def test_settings_mcp_urls_use_gateway() -> None:
    settings = Settings(
        model_name="x",
        lm_studio_base_url="http://127.0.0.1:1234/v1",
        agentgateway_url="http://127.0.0.1:8080",
        otel_endpoint="http://127.0.0.1:4317",
        repair_budget=3,
        openai_api_key="k",
    )
    assert settings.mcp_url("strict") == "http://127.0.0.1:8080/mcp/strict"
    assert settings.mcp_url("legacy") == "http://127.0.0.1:8080/mcp/legacy"
    assert ":8001" not in settings.mcp_url("strict")
    assert ":8002" not in settings.mcp_url("legacy")


def test_client_rejects_loopback_bypass() -> None:
    with pytest.raises(RuntimeError, match="bypass"):
        call_transfer_funds("http://127.0.0.1:8001/mcp", {"amount": 1})
