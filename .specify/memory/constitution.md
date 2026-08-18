<!--
Sync Impact Report
- Version change: 0.0.0 (unfilled template) → 1.0.0
- Modified principles:
  - [PRINCIPLE_1_NAME] → I. MCP 2026-07-28 Stateless Compliance
  - [PRINCIPLE_2_NAME] → II. JSON Schema 2020-12 Tool Validation
  - [PRINCIPLE_3_NAME] → III. LangGraph Validation-Error Resilience
  - [PRINCIPLE_4_NAME] → IV. Layered Separation of Concerns
  - [PRINCIPLE_5_NAME] removed (user specified four governing principles)
- Added sections: Architectural Constraints; Quality Gates
- Removed sections: none (template placeholders replaced)
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated (Constitution Check gates + layer layout)
  - .specify/templates/spec-template.md ✅ updated (mandatory Constitution Constraints)
  - .specify/templates/tasks-template.md ✅ updated (schema, protocol, recovery, layer tasks)
  - .specify/templates/commands/*.md ✅ N/A (directory absent; .cursor/skills and git commands have no agent-locked names)
  - README.md ✅ updated (constitution pointer)
  - .cursor/rules/specify-rules.mdc ✅ updated (constitution as runtime guidance)
- Follow-up TODOs: none
-->

# MCP 2026-07-28 Schema Reliability Demo Constitution

## Core Principles

### I. MCP 2026-07-28 Stateless Compliance

This project MUST implement the Model Context Protocol **2026-07-28**
stateless Streamable HTTP profile. Servers and clients MUST NOT require
protocol-level sessions, a sticky `initialize` handshake, or
`Mcp-Session-Id` affinity. Each JSON-RPC request MUST carry protocol
version and client capabilities in `_meta`, and Streamable HTTP calls
MUST include the `Mcp-Method`, `Mcp-Name`, and protocol-version headers
so a perimeter proxy can route and apply policy without inventing
session stickiness. agentgateway MUST run with `statefulMode: stateless`.
Tools MUST be invocable as independent HTTP round trips with no
server-held conversation state.

**Rationale**: Session-held MCP failed at scale. The 2026-07-28 spec
makes every call self-describing so gateways can govern traffic and
small models can retry without pinning to a backend.

### II. JSON Schema 2020-12 Tool Validation

Every FastMCP tool MUST declare its input contract as **JSON Schema
2020-12**. Conditional argument shapes MUST use `if`/`then` (and `else`
when a false branch is required). Mutually exclusive argument objects
MUST use `oneOf`. Shared fragments MUST live in `$defs` and be referenced
with `$ref`. Tools MUST NOT encode enforceable constraints only in
natural-language descriptions. The schema `$schema` identifier MUST be
the 2020-12 dialect. Output and error payloads that agents consume MUST
also be schema-described when they drive retries.

**Rationale**: Small local models fail tool calling when contracts are
ambiguous. Explicit 2020-12 conditionals make invalid calls detectable
at the edge before tool code runs.

### III. LangGraph Validation-Error Resilience

LangGraph orchestration MUST treat JSON-RPC error code **`-32602`**
(Invalid params) returned by agentgateway as a **recoverable validation
failure**, not a fatal graph exception. The graph MUST (1) parse the
validation error payload, (2) feed the schema violation back into the
model or a dedicated repair node, and (3) retry the tool call with
**changed** arguments within a bounded attempt limit. Retrying the
identical invalid payload is forbidden. Non-validation JSON-RPC errors
MUST follow a distinct failure path and MUST NOT be classified as
schema failures.

**Rationale**: Edge validation is useless if the agent dies on the first
reject. Bounded repair against `-32602` is how small models converge on
legal tool arguments.

### IV. Layered Separation of Concerns

The system MUST keep three layers distinct:

1. **Agent orchestration** (LangGraph) — planning, tool selection, and
   `-32602` repair loops.
2. **Proxy governance** (agentgateway) — routing, header checks, and
   JSON Schema enforcement at the edge.
3. **MCP tool execution** (FastMCP) — tool implementations bound to
   their 2020-12 schemas.

Gateway policy MUST NOT be implemented inside the agent graph. Agent
retry and orchestration MUST NOT be implemented inside MCP tools. Tool
business logic MUST NOT live in gateway configuration. All tool traffic
MUST pass through agentgateway; private backdoors that bypass the proxy
are forbidden.

**Rationale**: Mixing orchestration, governance, and execution makes
schema failures un-debuggable and prevents each layer from being tested
or replaced independently.

## Architectural Constraints

- **Purpose**: Demonstrate elimination of tool-calling failures for small
  local models via self-validating MCP tools, agentgateway edge
  validation, and LangGraph repair.
- **Protocol**: MCP 2026-07-28 Streamable HTTP only. Earlier MCP session
  profiles are out of scope.
- **Stack**: FastMCP for tools, agentgateway for the governed proxy,
  LangGraph for the agent. Substitutions require a constitution
  amendment.
- **Defense in depth**: Tool schemas and gateway validation MUST agree.
  The gateway is the enforcement point; the FastMCP schema is the source
  of truth the gateway is configured from.
- **State**: Application-level continuation tokens (if any) MUST be
  caller-held and request-scoped. They MUST NOT reintroduce MCP session
  affinity.

## Quality Gates

A change is non-compliant until all of the following hold:

- **Schema gate**: Each new or changed FastMCP tool includes a JSON
  Schema 2020-12 document that uses `if`/`then`, `oneOf`, and/or `$defs`
  wherever arguments are conditional or exclusive, plus fixtures for at
  least one valid payload and one payload that MUST fail validation.
- **Protocol gate**: No code, config, or test requires `Mcp-Session-Id`
  stickiness or a mandatory session `initialize` before `tools/call`.
- **Resilience gate**: The LangGraph path demonstrates catch, repair,
  and bounded retry of agentgateway `-32602` responses; identical-payload
  retries are covered as a failing case.
- **Layer gate**: Agent, gateway, and MCP packages remain independently
  testable. A test that needs to skip agentgateway to reach a tool FAILS
  this gate unless it is an isolated unit test of tool logic with the
  bypass documented.

Unjustified gate failures block `/speckit-plan` Phase 0 and merge.

## Governance

This constitution supersedes informal practice, README conventions, and
feature specs. When a spec or plan conflicts with a principle, the
constitution wins until an amendment is ratified.

**Amendments**: Propose the change in the pull request, update this
file, bump **Version** using semantic versioning, set **Last Amended**
to the amendment date, and propagate the change through
`.specify/templates/` (plan, spec, tasks) plus runtime guidance
(`README.md`, `.cursor/rules/specify-rules.mdc`). MAJOR: remove or
redefine a principle. MINOR: add a principle or materially expand
guidance. PATCH: clarification or wording-only edits.

**Compliance review**: Every `/speckit-plan` run MUST complete the
Constitution Check. `/speckit-analyze` treats principle violations as
CRITICAL. Pull requests that add tools, gateway config, or graph nodes
MUST show the four quality gates above.

**Runtime guidance**: Follow this file, then the active feature
`plan.md`. Do not weaken a MUST here in agent instructions.

**Version**: 1.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
