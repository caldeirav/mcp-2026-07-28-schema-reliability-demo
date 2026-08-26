# Research: Enterprise Banking Fund Transfer Agent

## Decision: Dual LLM + MCP on one standalone agentgateway

**Decision**: Run a single **standalone** agentgateway process on `127.0.0.1:8080` as both the OpenAI-compatible LLM gateway and the MCP gateway. LangGraph `ChatOpenAI` targets the gateway (`http://127.0.0.1:8080/v1`). The gateway’s LLM upstream is LM Studio (`http://127.0.0.1:1234/v1`). MCP `tools/call` targets gateway routes `/mcp/strict` and `/mcp/legacy`, which proxy to FastMCP on loopback.

**Rationale**: The constitution requires all tool traffic through agentgateway and OTLP traces from the proxy. The user asked for local/standalone install as both LLM and MCP gateway, L7 `Mcp-Method` / `Mcp-Name` routing, and CEL policy. One data plane gives one trace source for chat completions and tool calls.

**Alternatives considered**:
- ChatOpenAI → LM Studio directly, tools → gateway: splits traces; rejected (SC-007 / FR-018 want gateway traces as source of truth).
- Kubernetes Gateway API install: too heavy for a laptop demo.
- Two agentgateway processes (LLM on 8080, MCP on another port): extra ops with no layering benefit.

## Decision: Automate standalone agentgateway install from the repo

**Decision**: `scripts/install_agentgateway.sh` installs the official binary if missing (`curl -sL https://agentgateway.dev/install | bash -s -- --version "$AGENTGATEWAY_VERSION"`). `scripts/run_gateway.sh` starts `agentgateway -f src/gateway/config.yaml`. Version is pinned in `.env` / `.env.example`. Config is versioned under `src/gateway/`, not `~/.config/agentgateway`.

**Rationale**: Demo operators must not hand-edit a global config. Official install script is the documented standalone path.

**Alternatives considered**:
- Docker-only gateway: works but the user asked for local/standalone binary.
- Assume `agentgateway` is already on PATH with no installer: fails first-run.

## Decision: FastMCP Streamable HTTP, explicit JSON Schema 2020-12 files

**Decision**: FastMCP Python server, `transport="http"`, `stateless_http=True`, path `/mcp`. Tool `transfer_funds` loads `inputSchema` from `src/mcp/schemas/transfer_funds.strict.json` (`$schema` 2020-12, `oneOf` + `if`/`then` + `$defs`). A second mount (or second FastMCP app on another loopback port) serves the same tool name with `transfer_funds.legacy.json` (properties + descriptions only). Schema files are the source of truth; FastMCP does not infer conditionals from type hints.

**Rationale**: Constitution II requires 2020-12 `if`/`then`, `oneOf`, `$defs`. Prefect FastMCP can register a Tool with an explicit `parameters` dict. Stateless HTTP matches MCP 2026-07-28 (no session store).

**Alternatives considered**:
- Pydantic-only inference: cannot express discriminator + amount `if`/`then` faithfully.
- MCP Python SDK without FastMCP: constitution stack is FastMCP.

## Decision: Gateway validates strict schema; legacy is weak at the edge

**Decision**: agentgateway MCP proxy on the **strict** route validates `tools/call` arguments against the advertised 2020-12 `inputSchema` and returns JSON-RPC **`-32602`** without invoking FastMCP when invalid. The **legacy** route uses the weak schema so illegal business payloads are admitted; FastMCP still **does not record** and returns an opaque (non-`-32602`) error. CEL `mcpAuthorization` allows `transfer_funds` and requires `Mcp-Method` / `Mcp-Name` headers that match the JSON-RPC method/name (coarse policy, not identity).

**Rationale**: Spec FR-009 / clarification session: never record illegal transfers; only strict path emits parseable `-32602`. Constitution: gateway is the enforcement point; FastMCP schema is the source of truth.

**Alternatives considered**:
- Validate only inside FastMCP: violates “gateway is the enforcement point” for the strict path.
- Record illegal transfers on legacy: rejected in clarify (option A).

## Decision: LangGraph StateGraph + ChatOpenAI via gateway

**Decision**: Custom `StateGraph` (not a black-box ReAct prebuilt as the only loop). State holds `messages` (`add_messages`), `contract_mode`, `repair_attempts`, `last_error_kind`, `last_payload_fingerprint`, `transfer_recorded`. Nodes: `model` (`ChatOpenAI` + bound MCP tools) → `tools` (MCP client through gateway) → `classify` (`-32602` vs opaque vs other) → `repair` (append validation payload; reject identical fingerprint) or `end`. `ChatOpenAI` uses `base_url=http://127.0.0.1:8080/v1`, `model` from `.env` (default `qwen/qwen3.8-27b`), dummy API key for LM Studio.

**Rationale**: Constitution III requires a dedicated bounded repair path, not “retry same tool call.” User specified ChatOpenAI and StateGraph.

**Alternatives considered**:
- `create_react_agent` only: harder to forbid identical-payload retries and to label ComparisonReport fields.
- Direct LM Studio `base_url` on ChatOpenAI: bypasses LLM gateway.

## Decision: Comparison script runtime parameter, not `.env`

**Decision**: CLI `python -m agent.compare --contract {legacy|strict|both}` (or `scripts/compare.sh`). `.env` holds URLs, model name, OTLP endpoint, repair budget, agentgateway version — never contract mode.

**Rationale**: Spec FR-016 / SC-006.

## Decision: Observability

**Decision**: Script prints labeled per-route stdout (mode, error kind, repair count, recorded). agentgateway `frontendPolicies.tracing` exports OTLP gRPC to the collector in `.env` (default `127.0.0.1:4317`). Collector is Jaeger all-in-one started by `./scripts/run_jaeger.sh` (Podman `podman run`, UI `:16686`). No agent-side tracer as source of truth.

**Rationale**: Spec FR-017, FR-018, SC-007.

## Decision: Language and libraries

**Decision**: Python 3.12+, `uv` + `pyproject.toml`. Libraries: `fastmcp`, `langgraph`, `langchain-openai`, `langchain-mcp-adapters` (or MCP Streamable HTTP client), `jsonschema` (2020-12) for contract tests, `pytest`.

**Rationale**: Matches FastMCP/LangGraph/ChatOpenAI. jsonschema validates fixtures independently of the gateway.

## Decision: Ports

| Process | Bind |
|---------|------|
| LM Studio (operator-started) | `127.0.0.1:1234` |
| agentgateway | `127.0.0.1:8080` |
| FastMCP strict | `127.0.0.1:8001/mcp` (loopback only) |
| FastMCP legacy | `127.0.0.1:8002/mcp` (loopback only) |
| OTLP collector (Jaeger) | `127.0.0.1:4317` (gRPC), UI `127.0.0.1:16686` |
| agentgateway admin UI | default (e.g. `15000`) if enabled; not required for the demo |

Agent never calls `:8001`/`:8002` except in documented unit tests of tool logic.
