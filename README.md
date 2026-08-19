# mcp-2026-07-28-schema-reliability-demo

Laptop demo: a small local model fails a legacy (description-only) `transfer_funds` contract, then recovers on a JSON Schema 2020-12 contract when agentgateway returns JSON-RPC `-32602` and LangGraph repairs arguments.

Loopback only. Does not start LM Studio or Jaeger.

Governing principles (MCP 2026-07-28 stateless compliance, JSON Schema 2020-12 tool contracts, LangGraph `-32602` repair, and layered agent/gateway/tool separation) live in [`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Architecture

```text
                    --contract both
  compare CLI ──► LangGraph StateGraph
                     │
                     │ ChatOpenAI /v1/chat/completions
                     │ MCP Streamable HTTP /mcp/{strict|legacy}
                     ▼
              agentgateway :8080
              (CEL + L7 Mcp-Method/Mcp-Name + OTLP)
                     │                    │
                     │ LLM                │ MCP statefulMode: stateless
                     ▼                    ▼
              LM Studio :1234/v1    FastMCP :8001 strict
                                    FastMCP :8002 legacy
```

Contract mode is a **runtime CLI parameter**, never an environment variable.

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (this repo does not use pip)
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

Do not set `CONTRACT_MODE`. Pass `--contract` (or the first argument to `scripts/compare.sh`).

## Install

```bash
uv sync
./scripts/install_agentgateway.sh
```

Add or drop Python packages with `uv add` / `uv remove` (not pip). `uv.lock` is the lockfile.

Scripts already wrap `uv run` (`compare.sh`, `run_mcp.sh`).

## Run (three terminals)

```bash
./scripts/run_mcp.sh          # FastMCP strict :8001 and legacy :8002
./scripts/run_gateway.sh      # agentgateway -f src/gateway/config.yaml :8080
./scripts/compare.sh both     # runtime parameter: legacy | strict | both
```

`compare.sh` sets `PYTHONPATH` to `src/agent` and `src/mcp` (not `src/`, which would shadow the `mcp` PyPI package) and runs `python -m compare`.

Expect labeled stdout: legacy opaque fail (not recorded, no repair), then strict `-32602` repair copying `CMP-DEMO-2026` from the prompt, transfer recorded. Inspect gateway traces in the collector for both MCP routes (and the LLM hop).

## Verify without the model

```bash
uv run pytest tests/contract tests/unit tests/integration
```

Integration tests mock MCP/LLM. Live `compare.sh both` needs LM Studio, FastMCP, agentgateway, and the OTLP collector.

## Ports

| Process | Bind |
|---------|------|
| LM Studio (operator-started) | `127.0.0.1:1234` |
| agentgateway | `127.0.0.1:8080` |
| FastMCP strict | `127.0.0.1:8001/mcp` (loopback only) |
| FastMCP legacy | `127.0.0.1:8002/mcp` (loopback only) |
| OTLP collector | `127.0.0.1:4317` (assumed) |
