# agentgateway (standalone)

One process is both the **LLM gateway** (OpenAI-compatible `/v1/chat/completions`) and the **MCP gateway**. The **Admin UI** is on the admin listener, not on the data-plane port.

| Bind | Role |
|------|------|
| `127.0.0.1:8080` | Data plane (LLM + MCP) |
| `127.0.0.1:15000/ui/` | Admin UI (Gateway Overview, LLM Client Setup, MCP Tool Playground) |
| `127.0.0.1:1234/v1` | LM Studio upstream |
| `127.0.0.1:8001/mcp` | FastMCP strict (loopback only) |
| `127.0.0.1:8002/mcp` | FastMCP legacy (loopback only) |
| `127.0.0.1:4317` | OTLP collector (assumed running) |

`config.adminAddr` is pinned to `127.0.0.1:15000`. The UI is **not** attached to gateway `default`, so `:8080` stays LLM/MCP only.

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

`run_gateway.sh` prints `Admin UI: http://127.0.0.1:15000/ui/` and executes `agentgateway -f src/gateway/config.yaml` (not `~/.config/agentgateway`).

## Policy

- `statefulMode: stateless` (no `Mcp-Session-Id` affinity)
- CEL `mcpAuthorization`: `transfer_funds` or empty tool name (so `tools/list` / discover work in the playground)
- Routes `/mcp/strict` and `/mcp/legacy` are path-prefix matches (playground does not send `Mcp-Method` / `Mcp-Name`; the LangGraph client still does)
- CORS origins `http://127.0.0.1:15000` and `http://localhost:15000` for the Tool Playground
- OTLP traces from the gateway (`frontendPolicies.tracing`)
