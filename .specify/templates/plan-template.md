# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` v1.0.0*

**I. MCP 2026-07-28 Stateless Compliance**
- [ ] Design uses MCP 2026-07-28 Streamable HTTP only (no session affinity / `Mcp-Session-Id`)
- [ ] Per-request `_meta` (protocol version + client capabilities) and `Mcp-Method` / `Mcp-Name` / protocol-version headers are specified
- [ ] agentgateway remains in `statefulMode: stateless`

**II. JSON Schema 2020-12 Tool Validation**
- [ ] Every FastMCP tool ships a JSON Schema 2020-12 input schema (`$schema` dialect 2020-12)
- [ ] Conditional args use `if`/`then`; exclusive shapes use `oneOf`; shared fragments use `$defs`
- [ ] No prose-only constraints that the schema cannot enforce

**III. LangGraph Validation-Error Resilience**
- [ ] JSON-RPC `-32602` from agentgateway is a recoverable graph path with a bounded retry limit
- [ ] Retry MUST change arguments using the validation error payload (identical invalid payloads are forbidden)
- [ ] Non-validation JSON-RPC errors are not classified as schema failures

**IV. Layered Separation of Concerns**
- [ ] Agent orchestration, proxy governance, and MCP tool execution remain separate packages/modules
- [ ] No layer implements another layer's responsibilities (policy, repair, or tool logic)
- [ ] Tool traffic MUST pass through agentgateway (no undocumented bypass)

Unjustified failures FAIL this gate. Record accepted deviations only in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Principle IV requires three independently testable layers:
  agent orchestration, proxy governance, and MCP tool execution. The delivered
  plan MUST preserve that separation (folder names may differ).
-->

```text
src/
├── agent/                 # LangGraph orchestration and -32602 repair
├── gateway/               # agentgateway config (stateless MCP)
└── mcp/                   # FastMCP tools + JSON Schema 2020-12

tests/
├── contract/              # tool schemas, MCP 2026-07-28 request shape
├── integration/           # agent → gateway → tool, including -32602 repair
└── unit/                  # per-layer tests (bypass of gateway MUST be documented)
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above. MUST map to the three constitution layers.]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
