# agentgateway (standalone)

One process is both the **LLM gateway** (OpenAI-compatible `/v1/chat/completions`) and the **MCP gateway**. The **Admin UI** is on the admin listener, not on the data-plane port.

| Bind | Role |
|------|------|
| `127.0.0.1:8080` | Data plane (LLM + MCP) |
| `127.0.0.1:15000/ui/` | Admin UI (Gateway Overview, LLM Client Setup, MCP Tool Playground) |
| `127.0.0.1:1234/v1` | LM Studio upstream |
| `127.0.0.1:8001/mcp` | FastMCP strict (loopback only) |
| `127.0.0.1:8002/mcp` | FastMCP legacy (loopback only) |
| `127.0.0.1:4317` | Jaeger OTLP gRPC (`./scripts/run_jaeger.sh`, Podman) |
| `127.0.0.1:16686` | Jaeger UI |

`config.adminAddr` is pinned to `127.0.0.1:15000`. The UI is **not** attached to gateway `default`, so `:8080` stays LLM/MCP only.

The Admin UI treats MCP as enabled only when a top-level `mcp:` section exists, and LLM → Models lists named models rather than `*`. `config.yaml` therefore declares `mcp.targets` (`banking-strict`, `banking-legacy`) and `llm.models` name `qwen/qwen3.8-27b` so those appear on first open. Comparison traffic still uses routes `/mcp/strict` and `/mcp/legacy`.

## Install

From the repo root:

```bash
./scripts/install_agentgateway.sh
```

Uses `https://agentgateway.dev/install` with `--version` from `AGENTGATEWAY_VERSION` in `.env`.

## Run

```bash
./scripts/run_jaeger.sh
./scripts/run_mcp.sh
./scripts/run_gateway.sh
```

`run_gateway.sh` prints `Admin UI: http://127.0.0.1:15000/ui/` and executes `agentgateway -f src/gateway/config.yaml` (not `~/.config/agentgateway`).

## Policy

- `statefulMode: stateless` (no `Mcp-Session-Id` affinity)
- Native `mcp:` `prefixMode: always` so the federated `/mcp` playground lists `banking-strict_transfer_funds` vs `banking-legacy_transfer_funds`
- CEL `mcpAuthorization`: `transfer_funds` (or a prefixed form) or empty tool name (so `tools/list` / discover work in the playground)
- Routes `/mcp/strict` and `/mcp/legacy` are path-prefix matches (playground does not send `Mcp-Method` / `Mcp-Name`; the LangGraph client still does)
- CORS origins `http://127.0.0.1:15000` and `http://localhost:15000` for the Tool Playground
- OTLP traces from the gateway (`frontendPolicies.tracing`) to Jaeger `:4317`; inspect at `http://127.0.0.1:16686`
