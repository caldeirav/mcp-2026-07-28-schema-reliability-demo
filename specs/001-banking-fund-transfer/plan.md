# Implementation Plan: Enterprise Banking Fund Transfer Agent

**Branch**: `001-banking-fund-transfer` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-banking-fund-transfer/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Tasks are generated later by `/speckit-tasks`.

## Summary

Demonstrate that a small local model fails a legacy (description-only) `transfer_funds` contract and recovers on a JSON Schema 2020-12 contract when agentgateway returns JSON-RPC `-32602` and LangGraph repairs arguments. Architecture: LangGraph `StateGraph` + `ChatOpenAI` through agentgateway’s OpenAI-compatible API; agentgateway (standalone, `:8080`) as both LLM and MCP gateway with CEL policy, L7 `Mcp-Method`/`Mcp-Name` routing, and OTLP traces; FastMCP Streamable HTTP tools behind the gateway. A comparison script selects `legacy` | `strict` | `both` as a **runtime parameter**.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastMCP (HTTP/stateless), LangGraph, langchain-openai (`ChatOpenAI`), langchain-mcp-adapters (or MCP Streamable HTTP client), jsonschema (2020-12), pytest; agentgateway standalone binary (pinned version)

**Storage**: Ephemeral in-process simulated ledger (no production DB)

**Testing**: pytest — `tests/contract` (schemas + MCP 2026-07-28 headers), `tests/unit` (per layer; gateway bypass documented), `tests/integration` (agent → gateway → tool, `-32602` repair, compare `--contract both`)

**Target Platform**: macOS/Linux laptop; loopback only

**Project Type**: Multi-process demo (agent CLI + FastMCP + agentgateway); not a library

**Performance Goals**: Single-operator demo; repair budget 3; no throughput SLO

**Constraints**: MCP 2026-07-28 stateless Streamable HTTP; agentgateway `statefulMode: stateless`; no `Mcp-Session-Id` affinity; LM Studio already running; OTLP collector already running; `.env` for endpoints/model; contract mode is CLI-only

**Scale/Scope**: One tool (`transfer_funds`), two gateway routes, one comparison prompt family (high-value internal with `CMP-DEMO-2026` in the prompt)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` v1.0.0*

**I. MCP 2026-07-28 Stateless Compliance**
- [x] Design uses MCP 2026-07-28 Streamable HTTP only (no session affinity / `Mcp-Session-Id`)
- [x] Per-request `_meta` (protocol version + client capabilities) and `Mcp-Method` / `Mcp-Name` / protocol-version headers are specified
- [x] agentgateway remains in `statefulMode: stateless`

**II. JSON Schema 2020-12 Tool Validation**
- [x] Every FastMCP tool ships a JSON Schema 2020-12 input schema (`$schema` dialect 2020-12)
- [x] Conditional args use `if`/`then`; exclusive shapes use `oneOf`; shared fragments use `$defs`
- [x] No prose-only constraints that the schema cannot enforce (strict route); legacy route is intentionally prose-only for the comparison

**III. LangGraph Validation-Error Resilience**
- [x] JSON-RPC `-32602` from agentgateway is a recoverable graph path with a bounded retry limit
- [x] Retry MUST change arguments using the validation error payload (identical invalid payloads are forbidden)
- [x] Non-validation JSON-RPC errors are not classified as schema failures

**IV. Layered Separation of Concerns**
- [x] Agent orchestration, proxy governance, and MCP tool execution remain separate packages/modules
- [x] No layer implements another layer's responsibilities (policy, repair, or tool logic)
- [x] Tool traffic MUST pass through agentgateway (no undocumented bypass)

Post-design: still pass. Dual LLM+MCP on one gateway is still the proxy layer, not a fourth project. Legacy FastMCP still refuses to record; it does not implement LangGraph repair.

## Project Structure

### Documentation (this feature)

```text
specs/001-banking-fund-transfer/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md             # /speckit-tasks — not created here
```

### Source Code (repository root)

```text
src/
├── agent/                 # LangGraph StateGraph, ChatOpenAI, compare CLI
│   ├── graph.py
│   ├── state.py
│   ├── repair.py          # -32602 classify + fingerprint + budget
│   ├── llm.py             # ChatOpenAI → gateway :8080/v1
│   └── compare.py         # --contract legacy|strict|both
├── gateway/               # standalone agentgateway config + install helpers
│   ├── config.yaml
│   └── README.md
└── mcp/                   # FastMCP servers + 2020-12 schemas
    ├── server_strict.py
    ├── server_legacy.py
    ├── ledger.py          # in-memory simulated transfers
    └── schemas/
        ├── transfer_funds.strict.json
        └── transfer_funds.legacy.json

scripts/
├── install_agentgateway.sh
├── run_mcp.sh
├── run_gateway.sh
└── compare.sh

tests/
├── contract/
├── integration/
└── unit/

.env.example
```

**Structure Decision**: Three constitution layers under `src/agent`, `src/gateway`, `src/mcp`. Scripts automate standalone agentgateway install/run. FastMCP binds loopback only; agents call `:8080` only.

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

- **LLM path**: `ChatOpenAI(base_url=http://127.0.0.1:8080/v1, model=$MODEL_NAME)` → gateway `provider.custom` → `http://127.0.0.1:1234/v1`.
- **MCP path**: client sends 2026-07-28 headers (`Mcp-Method`, `Mcp-Name`, protocol version) and `_meta` on each POST. Gateway routes `/mcp/strict` vs `/mcp/legacy`. CEL allows `mcp.tool.name == "transfer_funds"` and requires matching headers.
- **Strict**: gateway schema-validates arguments → `-32602` or forward to FastMCP.
- **Legacy**: weak schema at gateway; FastMCP opaque reject, no record, no repair loop.
- **Repair**: classify `-32602` → feed error into messages → retry with changed args; fingerprint identical payloads as forbidden; budget from `.env` (default 3). Prompt already contains `CMP-DEMO-2026`.

## Gateway automation (standalone)

1. `scripts/install_agentgateway.sh` — if `command -v agentgateway` fails or version mismatches `AGENTGATEWAY_VERSION`, run the official installer with `--version`.
2. `src/gateway/config.yaml` — listener `:8080`; LLM backend LM Studio; two MCP backends; `statefulMode: stateless`; tracing to `$OTEL_EXPORTER_OTLP_ENDPOINT`; CEL `mcpAuthorization`; header matches on `Mcp-Method` / `Mcp-Name`.
3. `scripts/run_gateway.sh` — `agentgateway -f src/gateway/config.yaml` (never rely on `~/.config/agentgateway` for this demo).

## Complexity Tracking

No constitution violations. Dual LLM+MCP listeners are one proxy process.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
