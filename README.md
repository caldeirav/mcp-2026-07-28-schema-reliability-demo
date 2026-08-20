# MCP 2026 tool reliability demo

A laptop demo of **why tool calling fails on small local models**, and **how MCP 2026-07-28 plus a real tool schema lets the agent recover**.

You ask a banking agent to move more than $10,000. The same prompt is sent twice: once through a vague, description-only tool contract, and once through a strict JSON Schema contract in front of a gateway. The first path fails opaquely. The second path returns a precise “invalid parameters” error, the agent repairs the call, and a simulated transfer is recorded.

This repository is a **local, loopback-only** example. It does not start LM Studio or Jaeger for you.

## 1. Background: what changed in MCP 2026-07-28

If you already use LLMs with **MCP tools**, you know the pattern: the model chooses a tool, fills in arguments, and a server runs that tool.

Older MCP versions treated that like a **phone call with a handshake**. The client and server first negotiated a session (`initialize`), then kept a session id so later calls stuck to the same backend. That works on a laptop. It is painful at scale: load balancers need sticky routing or a shared session store, and a gateway often has to open the JSON body just to see *which tool* was being called.

**MCP 2026-07-28** (release candidate) changes that:

- **Each tool call stands alone.** Version, client info, and capabilities travel with the request (in a `_meta` field). There is no protocol-level session to pin you to one server.
- **Gateways can route without reading the whole body.** Standard HTTP headers name the operation and the tool (`Mcp-Method`, `Mcp-Name`), the way a URL names a REST endpoint.
- **Tool contracts get a real schema language.** Inputs (and outputs) use **JSON Schema 2020-12**, not a limited older draft. That means you can say *in the schema* “if the amount is over $10,000, this field is required” or “an internal transfer and a wire transfer are two different shapes”—instead of hoping the model reads a paragraph of English.

In short: MCP 2026 is built so **agents, gateways, and tools can scale like ordinary HTTP APIs**, and so **invalid tool arguments can be rejected with a useful error** before they hit your business logic.

## 2. The problem this demo shows

Models do not “call APIs” the way a typed client does. They **guess JSON** from the tool description. Small local models are especially likely to:

- omit a field that is only required *sometimes* (for example, a compliance code only when the amount is high)
- mix fields from two different operations (internal account vs wire IBAN/SWIFT)
- produce something that looks reasonable in English but is illegal for the bank

If the tool schema is **description-only**, the server may still accept the JSON, then fail deep in application code. The agent sees an opaque “transfer rejected” and **cannot repair** the arguments. If you recorded the transfer anyway, that would be a real incident. This demo **never records an illegal transfer**.

That is the failure mode we care about: **vague contracts → silent or opaque failure → no recovery**.

## 3. The approach

We keep three jobs in three places (the model never talks to the tool servers directly):

| Layer | Role |
|-------|------|
| **Agent** (LangGraph) | Reads the user prompt, calls `transfer_funds`, and if the gateway says the arguments are invalid, **retries with a changed payload**. |
| **Gateway** ([agentgateway](https://agentgateway.dev/)) | One process in front of both the local LLM and the MCP tools. Routes `/mcp/strict` vs `/mcp/legacy`, checks headers, and is the place validation feedback comes from. |
| **Tools** (FastMCP) | A simulated bank ledger. Strict and legacy are the **same tool name** with **two different contracts**. |

The comparison is the point of the demo:

1. **Legacy route** — the schema is mostly prose (“amounts over 10000 need a compliance code”). The model can omit `compliance_approval_code`. The tool refuses to record and returns an **opaque** error. The agent **does not** enter a repair loop.
2. **Strict route** — the schema is JSON Schema 2020-12 (`if` / `then` for the $10,000 rule; separate shapes for internal vs wire). Invalid arguments fail at the perimeter as JSON-RPC **`-32602` (invalid params)**. The agent reads that error, **copies the published demo code `CMP-DEMO-2026` from the prompt** (it must not invent a code), and retries.

You choose the route at **run time** (`legacy`, `strict`, or `both`). It is **not** an environment variable, so you never accidentally bake “which contract” into config.

```text
  compare.sh both
        │
        ▼
  LangGraph agent
        │  chat + tool calls
        ▼
  agentgateway :8080
        │                    │
        ▼                    ▼
  LM Studio :1234      FastMCP tools
                       strict :8001 / legacy :8002
```

Traces for both MCP routes (and the LLM hop) are meant to come from **the gateway**, not from an extra tracer inside the agent.

## 4. Run the demo end to end

### What you need

- **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/) (this repo does not use pip)
- **[LM Studio](https://lmstudio.ai/)** already serving `qwen/qwen3.8-27b` at `http://127.0.0.1:1234/v1`
- **OTLP collector** already running if you want traces (for example Jaeger all-in-one at `http://127.0.0.1:4317`). The demo does not start it.
- Network **once** to install the agentgateway binary

Everything binds to **localhost**.

### Install

```bash
git clone https://github.com/caldeirav/mcp-2026-07-28-schema-reliability-demo.git
cd mcp-2026-07-28-schema-reliability-demo

uv sync
./scripts/install_agentgateway.sh
```

`uv sync` installs Python dependencies from `uv.lock`. Add or remove packages later with `uv add` / `uv remove`, not pip.

### Configure

```bash
cp .env.example .env
```

Edit `.env` only if your model name or ports differ. Typical values:

```text
MODEL_NAME=qwen/qwen3.8-27b
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
AGENTGATEWAY_URL=http://127.0.0.1:8080
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
AGENTGATEWAY_VERSION=1.4.1
REPAIR_BUDGET=3
```

Do **not** set `CONTRACT_MODE`. Pass the contract on the command line.

### Start the stack (three terminals)

Confirm LM Studio is serving the model, then:

```bash
# Terminal 1 — simulated bank tools (strict + legacy)
./scripts/run_mcp.sh

# Terminal 2 — gateway in front of the model and the tools
./scripts/run_gateway.sh

# Terminal 3 — same prompt, both contracts
./scripts/compare.sh both
```

You can also run `./scripts/compare.sh legacy` or `./scripts/compare.sh strict`.

### What you should see

Labeled lines, one per route, for example:

```text
[legacy] error_kind=opaque repair_attempts=0 recorded=no transfer_id=-
[strict] error_kind=none repair_attempts=1 recorded=yes transfer_id=…
```

On a **small** model the intended story is: legacy fails without a recorded transfer; strict gets an invalid-params error, repairs using `CMP-DEMO-2026` from the prompt, then records. A stronger local model may fill in the code on the first try on both routes—that still proves the stack is wired; the mocked tests cover the fail-then-repair contrast.

If Jaeger (or another collector) is up, inspect gateway traces for `/mcp/legacy`, `/mcp/strict`, and `/v1/chat/completions`.

### Check the contracts without a model

```bash
uv run pytest tests/contract tests/unit tests/integration
```

Those tests do not need LM Studio. Live `compare.sh` does.

### Ports

| Process | Address |
|---------|---------|
| LM Studio (you start this) | `127.0.0.1:1234` |
| agentgateway | `127.0.0.1:8080` |
| FastMCP strict | `127.0.0.1:8001/mcp` (loopback only) |
| FastMCP legacy | `127.0.0.1:8002/mcp` (loopback only) |
| OTLP collector (optional) | `127.0.0.1:4317` |

---

Project rules for this example live in [`.specify/memory/constitution.md`](.specify/memory/constitution.md). The feature spec is [`specs/001-banking-fund-transfer/spec.md`](specs/001-banking-fund-transfer/spec.md).
