# agentgateway (standalone)

One process is both the **LLM gateway** (OpenAI-compatible `/v1/chat/completions`) and the **MCP gateway**.

| Bind | Role |
|------|------|
| `127.0.0.1:8080` | agentgateway (this config) |
| `127.0.0.1:1234/v1` | LM Studio upstream |
| `127.0.0.1:8001/mcp` | FastMCP strict (loopback only) |
| `127.0.0.1:8002/mcp` | FastMCP legacy (loopback only) |
| `127.0.0.1:4317` | OTLP collector (assumed running) |

## Install

From the repo root:

```bash
./scripts/install_agentgateway.sh
```

Uses `https://agentgateway.dev/install` with `--version` from `AGENTGATEWAY_VERSION` in `.env`.

## Run

```bash
./scripts/run_mcp.sh
./scripts/run_gateway.sh
```

`run_gateway.sh` executes `agentgateway -f src/gateway/config.yaml` (not `~/.config/agentgateway`).

## Policy

- `statefulMode: stateless` (no `Mcp-Session-Id` affinity)
- CEL `mcpAuthorization`: `mcp.tool.name == "transfer_funds"` plus non-empty `Mcp-Method` / `Mcp-Name`
- Routes `/mcp/strict` and `/mcp/legacy` match those headers
- OTLP traces from the gateway (`frontendPolicies.tracing`)
