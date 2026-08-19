# Quickstart: Enterprise Banking Fund Transfer Agent

Laptop demo. Loopback only. Does not start LM Studio or Jaeger.

## Prerequisites

- Python 3.12+
- `uv`
- LM Studio serving `qwen/qwen3.8-27b` at `http://127.0.0.1:1234/v1`
- OTLP collector (e.g. Jaeger all-in-one) at `http://127.0.0.1:4317`
- Network once to install the agentgateway binary

## Configure

```bash
cp .env.example .env
# MODEL_NAME=qwen/qwen3.8-27b
# LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
# AGENTGATEWAY_URL=http://127.0.0.1:8080
# OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
# AGENTGATEWAY_VERSION=<pinned>
# REPAIR_BUDGET=3
```

Contract mode is **not** in `.env`.

## Install

```bash
uv sync
./scripts/install_agentgateway.sh
```

## Run (three terminals)

```bash
./scripts/run_mcp.sh          # FastMCP strict :8001 and legacy :8002
./scripts/run_gateway.sh      # agentgateway -f src/gateway/config.yaml :8080
./scripts/compare.sh both     # runtime parameter: legacy | strict | both
```

Expect labeled stdout: legacy opaque fail (not recorded), then strict `-32602` repair copying `CMP-DEMO-2026`, transfer recorded. Inspect gateway traces in the collector for both MCP routes (and the LLM hop).

## Verify without the model

```bash
uv run pytest tests/contract tests/unit
```

Integration tests that need LM Studio + gateway are documented under `tests/integration`.
