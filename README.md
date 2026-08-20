# MCP 2026 tool reliability demo

A runnable comparison of **MCP as it is usually wired in a single application** versus **MCP 2026-07-28 as it has to behave behind an enterprise gateway**.

The workload is a simulated `transfer_funds` tool. The same agent, model, and prompt hit two contracts: a description-only (legacy) schema that is typical of early MCP integrations, and a JSON Schema 2020-12 (strict) schema enforced at [agentgateway](https://agentgateway.dev/). Illegal transfers are never recorded. Run locally on loopback; LM Studio and an OTLP collector are assumed already running.

## 1. Background: development-time MCP vs MCP 2026-07-28 at scale

During development, an MCP client and a single tool server are often the entire topology. A session-oriented Streamable HTTP flow (`initialize` / `initialized`, then `Mcp-Session-Id`) is acceptable: one process, one backend, no need for the proxy to classify traffic. Tool arguments are documented in natural language on `inputSchema`. If the model is large enough, or you iterate in the agent, that is enough to ship a prototype.

That topology does not survive horizontal scale:

- **Session affinity.** Protocol-level sessions force sticky routing or a distributed session store so consecutive calls land on the same replica. Round-robin L7 load balancing is not an option.
- **Opaque JSON-RPC.** All methods share one HTTP path. Without `Mcp-Method` / `Mcp-Name`, a gateway must parse bodies to authorize, rate-limit, or split traffic by tool—an operation that does not compose with TLS termination and compression.
- **Contracts that only the model reads.** JSON Schema Draft-07 subsets (and prose-only constraints) cannot express `if`/`then`, exclusive shapes (`oneOf`), or shared `$defs`. Invalid arguments either reach application code or fail without a structured error the agent can consume.

MCP **2026-07-28** (release candidate) is the protocol change that matches how HTTP APIs are already operated:

- Requests are **stateless**. Protocol version, client info, and capabilities travel per call in `_meta`. There is no `Mcp-Session-Id` affinity; `server/discover` replaces a sticky handshake for capability fetch.
- Streamable HTTP requires **L7 headers** (`Mcp-Method`, `Mcp-Name`, protocol version) so ingress can route and apply policy without unmarshalling JSON-RPC. Header/body mismatch is a reject.
- Tool `inputSchema` / `outputSchema` are full **JSON Schema 2020-12**. Conditionals, composition, and `$ref` are first-class; gateways can validate arguments and return JSON-RPC `-32602` (invalid params) before the tool runs.

This repository does not implement a mesh. It isolates those protocol and contract differences on one host so you can measure them.

## 2. The problem

In a single-app integration, tool reliability is often treated as a **model quality** issue: better prompting, a larger model, more retries. That hides two independent failures that appear as soon as a gateway and more than one replica exist.

**Contract failure.** Models emit JSON; they do not type-check against your domain. Conditional fields (compliance code only when `amount > 10000`), discriminators (`internal` vs `wire`), and identifier patterns are routinely omitted or mixed. If those rules live only in descriptions, the server may accept the object and fail later, or return an unstructured tool error. The agent cannot distinguish “invalid params” from “business reject,” and it has no payload to repair against. Retrying the same arguments is wasted work; recording the transfer would be a production incident.

**Topology failure.** A session-bound MCP server behind a generic reverse proxy cannot be scaled or governed like the rest of the HTTP fleet. Validation, authorization, and tracing get reimplemented in the agent or in each tool. At enterprise scale those belong at the data plane.

The demo workload is chosen because it encodes both: a high-value internal transfer requires `compliance_approval_code` const `CMP-DEMO-2026`; wire transfers require a different object shape (IBAN/SWIFT patterns, not internal destination accounts).

## 3. The approach

Keep **orchestration, governance, and execution** in separate processes. The agent never calls FastMCP on `:8001` / `:8002`.

| Process | Responsibility |
|---------|----------------|
| LangGraph agent | Tool selection and a bounded repair loop that treats `-32602` as recoverable. Identical invalid payloads are forbidden. Opaque (non-validation) errors do not start repair. |
| agentgateway `:8080` | LLM reverse proxy to LM Studio (`/v1`) and MCP reverse proxy (`/mcp/strict`, `/mcp/legacy`). Stateless MCP (`statefulMode: stateless`). Header matches and CEL allow `transfer_funds`. OTLP from this process is the source of truth for traces. |
| FastMCP | Two servers, one tool name. Strict loads JSON Schema 2020-12 (`if`/`then`, `oneOf`, `$defs`). Legacy loads a weak, description-only schema and returns an opaque reject without recording. |

Comparison is a **runtime parameter**, not configuration: `./scripts/compare.sh {legacy\|strict\|both}`. `.env` holds endpoints, model, repair budget, and gateway version only.

On **legacy**, an underspecified high-value call is not recorded; the error is opaque; repair does not run. On **strict**, the same class of payload is rejected as `-32602` with a named schema violation; the agent copies `CMP-DEMO-2026` from the user prompt (it must not invent a code) and retries with a changed fingerprint. That is the delta between “schema as documentation for one app” and “schema as an edge contract the agent can close.”

## 4. Run it

### Prerequisites

- Python 3.12+ and [`uv`](https://docs.astral.sh/uv/)
- [LM Studio](https://lmstudio.ai/) serving `qwen/qwen3.8-27b` at `http://127.0.0.1:1234/v1`
- Optional: OTLP collector (e.g. Jaeger) at `http://127.0.0.1:4317` — not started by this repo
- Network once for `./scripts/install_agentgateway.sh`

Loopback only.

### Install and configure

```bash
git clone https://github.com/caldeirav/mcp-2026-07-28-schema-reliability-demo.git
cd mcp-2026-07-28-schema-reliability-demo
uv sync
./scripts/install_agentgateway.sh
cp .env.example .env
```

```text
MODEL_NAME=qwen/qwen3.8-27b
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
AGENTGATEWAY_URL=http://127.0.0.1:8080
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
AGENTGATEWAY_VERSION=1.4.1
REPAIR_BUDGET=3
```

Do not set `CONTRACT_MODE`. Package changes: `uv add` / `uv remove`, then `uv sync`.

### Processes

| Bind | Process |
|------|---------|
| `127.0.0.1:1234` | LM Studio (operator) |
| `127.0.0.1:8080` | agentgateway (`src/gateway/config.yaml`) |
| `127.0.0.1:8001/mcp` | FastMCP strict |
| `127.0.0.1:8002/mcp` | FastMCP legacy |
| `127.0.0.1:4317` | OTLP (optional) |

```bash
./scripts/run_mcp.sh          # :8001 and :8002
./scripts/run_gateway.sh      # :8080
./scripts/compare.sh both     # or legacy | strict
```

### Expected output

```text
[legacy] error_kind=opaque repair_attempts=0 recorded=no transfer_id=-
[strict] error_kind=none repair_attempts=1 recorded=yes transfer_id=…
```

A capable local model may emit a legal payload on the first call on both routes. That still validates the data plane. The fail-then-repair contrast is covered by `tests/integration/test_compare_both.py`. Gateway traces, if the collector is up, should distinguish `/mcp/legacy`, `/mcp/strict`, and `/v1/chat/completions`.

### Tests without the model

```bash
uv run pytest tests/contract tests/unit tests/integration
```
