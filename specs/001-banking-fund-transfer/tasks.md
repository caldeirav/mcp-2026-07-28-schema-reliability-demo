---
description: "Task list for enterprise banking fund-transfer agent"
---

# Tasks: Enterprise Banking Fund Transfer Agent

**Input**: Design documents from `/specs/001-banking-fund-transfer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — user requested test scripts for schema failure vs recovery, plus constitution schema/protocol/resilience gates.

**Organization**: User stories (P1–P4). Workstreams (FastMCP/schema, agentgateway YAML, LangGraph/LM Studio, failure-vs-recovery tests) are labeled in each phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: `[US1]`–`[US4]` on user-story tasks only
- Include exact file paths in descriptions

## Path Conventions

- `src/agent/` LangGraph + ChatOpenAI + compare CLI
- `src/gateway/` agentgateway YAML + install notes
- `src/mcp/` FastMCP + JSON Schema 2020-12
- `tests/contract/`, `tests/integration/`, `tests/unit/`

## Workstream map

| Workstream | Tasks |
|------------|-------|
| FastMCP Server & JSON Schema 2020-12 | T005–T009, T022–T026, T027–T029, T030–T032, T040 |
| agentgateway (CEL & MCP routes) | T010–T015, T043 |
| LangGraph + LM Studio client | T016–T021, T034–T037, T039 |
| Test scripts (failure vs recovery) | T022–T023, T027, T030, T033–T034, T038, T041, T043 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Python project skeleton matching `plan.md`

- [x] T001 Create directories `src/agent/`, `src/gateway/`, `src/mcp/schemas/`, `scripts/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, `prompts/` and empty `__init__.py` files under `src/agent/` and `src/mcp/`
- [x] T002 Add `pyproject.toml` with Python 3.12+, `fastmcp`, `langgraph`, `langchain-openai`, `langchain-mcp-adapters`, `jsonschema`, `python-dotenv`, `pytest`
- [x] T003 [P] Write `.env.example` with `MODEL_NAME`, `LM_STUDIO_BASE_URL`, `AGENTGATEWAY_URL`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `AGENTGATEWAY_VERSION`, `REPAIR_BUDGET` and **no** contract-mode variable
- [x] T004 [P] Add `tests/conftest.py` and pytest config in `pyproject.toml` (`testpaths = tests`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Three layers runnable as separate processes. **No user-story work until this phase is complete.**

### FastMCP Server & JSON Schema 2020-12

- [x] T005 [P] Copy `specs/001-banking-fund-transfer/contracts/transfer_funds.strict.schema.json` to `src/mcp/schemas/transfer_funds.strict.json` and `transfer_funds.legacy.schema.json` to `src/mcp/schemas/transfer_funds.legacy.json`
- [x] T006 [P] Implement ephemeral simulated ledger (UUID, no record on illegal payload) in `src/mcp/ledger.py`
- [x] T007 Load strict 2020-12 schema as FastMCP `transfer_funds` `parameters`, Streamable HTTP `stateless_http=True` on `127.0.0.1:8001/mcp` in `src/mcp/server_strict.py`
- [x] T008 [P] Load legacy description-only schema as FastMCP `transfer_funds` on `127.0.0.1:8002/mcp` in `src/mcp/server_legacy.py`
- [x] T009 Add `scripts/run_mcp.sh` to start both FastMCP processes (loopback only)

### agentgateway configuration (CEL rules & MCP routes)

- [x] T010 Write standalone `src/gateway/config.yaml`: listener `127.0.0.1:8080`, custom OpenAI-compatible LLM backend `http://127.0.0.1:1234/v1`, MCP routes `/mcp/strict` → `:8001` and `/mcp/legacy` → `:8002`, `statefulMode: stateless`
- [x] T011 Add CEL `mcpAuthorization` allowing `mcp.tool.name == "transfer_funds"` and L7 matches on `Mcp-Method` / `Mcp-Name` in `src/gateway/config.yaml`
- [x] T012 Add `frontendPolicies.tracing` OTLP gRPC to collector host from `.env.example` in `src/gateway/config.yaml`
- [x] T013 [P] Add `scripts/install_agentgateway.sh` wrapping `curl -sL https://agentgateway.dev/install` with `--version "$AGENTGATEWAY_VERSION"`
- [x] T014 Add `scripts/run_gateway.sh` that runs `agentgateway -f src/gateway/config.yaml`
- [x] T015 [P] Document ports and install in `src/gateway/README.md`

### LangGraph agent with LM Studio client

- [x] T016 [P] Define `AgentGraphState` (`messages`, `contract_mode`, `repair_attempts`, `last_error_kind`, `last_payload_fingerprint`, `transfer_recorded`) in `src/agent/state.py`
- [x] T017 [P] Implement `ChatOpenAI` client `base_url=http://127.0.0.1:8080/v1`, model from env, dummy key in `src/agent/llm.py`
- [x] T018 Classify JSON-RPC `-32602` vs opaque vs other; fingerprint args; forbid identical retries in `src/agent/repair.py`
- [x] T019 Build `StateGraph` nodes `model` → `tools` → `classify` → `repair`|`end` with repair budget in `src/agent/graph.py`
- [x] T020 MCP Streamable HTTP client through gateway (`/mcp/strict` or `/mcp/legacy`) sending `Mcp-Method`, `Mcp-Name`, `Mcp-Protocol-Version`, `_meta` in `src/agent/mcp_client.py`
- [x] T021 Fail-fast env loader (no contract mode) in `src/agent/config.py`

**Checkpoint**: FastMCP, agentgateway YAML, and LangGraph skeleton exist; agent must not call `:8001`/`:8002` except documented unit tests

---

## Phase 3: User Story 1 - Submit an internal fund transfer (Priority: P1) 🎯 MVP

**Goal**: Legal internal transfer ≤ $10,000 records a confirmation; missing discriminator is rejected; IBAN/SWIFT not required

**Independent Test**: POST `transfer_funds` internal payload through gateway strict route; confirmation returned. Repeat without `transfer_type` → `-32602`, ledger empty

### Tests for User Story 1

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T022 [P] [US1] Contract tests for valid internal payload and missing/invalid `transfer_type` against `src/mcp/schemas/transfer_funds.strict.json` in `tests/contract/test_transfer_funds_internal.py`
- [x] T023 [P] [US1] Unit tests for ledger record/reject in `tests/unit/test_ledger.py` (document gateway bypass)

### Implementation for User Story 1

- [x] T024 [US1] Record legal internal transfers and return `TransferConfirmation` in `src/mcp/server_strict.py` using `src/mcp/ledger.py`
- [x] T025 [US1] Ensure internal `oneOf` branch does not require `iban`/`swift` in `src/mcp/schemas/transfer_funds.strict.json`
- [x] T026 [US1] Bind `transfer_funds` through gateway strict route in `src/agent/mcp_client.py` for internal happy-path invocation

**Checkpoint**: Internal ≤ $10k works on strict route; discriminator failures do not record

---

## Phase 4: User Story 2 - Block high-value transfers without compliance approval (Priority: P2)

**Goal**: `amount > 10000` requires const `CMP-DEMO-2026`; invented codes fail; exactly $10,000 does not require the code

**Independent Test**: `$10000.01` without code / with wrong code fail schema; with `CMP-DEMO-2026` records

### Tests for User Story 2

- [x] T027 [P] [US2] Contract tests for `if`/`then` amount threshold, `CMP-DEMO-2026` const, and invented codes in `tests/contract/test_compliance_if_then.py`

### Implementation for User Story 2

- [x] T028 [US2] Keep `if`/`then` + `$defs/compliance_approval_code` const in `src/mcp/schemas/transfer_funds.strict.json` loaded by `src/mcp/server_strict.py`
- [x] T029 [US2] Refuse to record high-value transfers without matching code in `src/mcp/ledger.py` (defense in depth; gateway still enforces first)

**Checkpoint**: High-value gating is schema-enforced, not prose-only

---

## Phase 5: User Story 3 - Submit a wire transfer with valid routing identifiers (Priority: P3)

**Goal**: Wire `oneOf` requires IBAN/SWIFT patterns; internal destination fields cannot satisfy wire; no MOD-97 checksum

**Independent Test**: Pattern-valid wire records; malformed IBAN/SWIFT fail; checksum-invalid but pattern-valid IBAN is accepted

### Tests for User Story 3

- [x] T030 [P] [US3] Contract tests for wire `oneOf`, IBAN/SWIFT patterns, and checksum-invalid-but-pattern-valid IBAN in `tests/contract/test_wire_iban_swift.py`

### Implementation for User Story 3

- [x] T031 [US3] Record legal wire transfers (destination summary from IBAN) in `src/mcp/server_strict.py`
- [x] T032 [US3] Confirm `iban`/`swift` `$defs` patterns have no checksum logic in `src/mcp/schemas/transfer_funds.strict.json`

**Checkpoint**: Discriminator exclusive shapes work for wire vs internal

---

## Phase 6: User Story 4 - Recover from illegal transfer using strict-contract feedback (Priority: P4)

**Goal**: Compare script `--contract both`: legacy opaque fail (not recorded, no repair); strict `-32602` then copy `CMP-DEMO-2026` from prompt; labeled stdout; gateway traces

**Independent Test**: `scripts/compare.sh both` prints per-route report; legacy unrepaired; strict records after changed args

### Tests for User Story 4 (failure vs recovery)

- [x] T033 [P] [US4] Contract tests that legacy schema admits illegal high-value payloads in `tests/contract/test_legacy_schema_weak.py`
- [x] T034 [P] [US4] Unit tests for `-32602` classify, fingerprint, budget, identical-retry forbidden in `tests/unit/test_repair.py`

### Implementation for User Story 4

- [x] T035 [US4] Implement comparison CLI `--contract {legacy|strict|both}` fail-fast on missing/invalid param in `src/agent/compare.py`
- [x] T036 [US4] Add `scripts/compare.sh` wrapping `python -m agent.compare`
- [x] T037 [US4] Add high-value internal prompt containing `CMP-DEMO-2026` in `prompts/high_value_internal.txt`
- [x] T038 [US4] Integration test: `both` → legacy opaque unrepaired vs strict `-32602` repair in `tests/integration/test_compare_both.py`
- [x] T039 [US4] Print labeled `ComparisonReport` (mode, error kind, repair count, recorded) in `src/agent/report.py`
- [x] T040 [US4] Legacy tool: do not record illegal payloads; return opaque non-`-32602` error in `src/mcp/server_legacy.py`
- [x] T041 [US4] Integration test that tool traffic uses `AGENTGATEWAY_URL` not `:8001`/`:8002` in `tests/integration/test_no_mcp_bypass.py`

**Checkpoint**: Demo thesis runnable via runtime parameter; SC-005/SC-007 observable

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T042 [P] Expand `README.md` from `specs/001-banking-fund-transfer/quickstart.md`
- [x] T043 [P] Contract test: MCP requests include required headers and never `Mcp-Session-Id` in `tests/contract/test_mcp_headers.py`
- [x] T044 [P] Add `.gitignore` for `.env`, `__pycache__/`, `.venv/`
- [x] T045 Run `specs/001-banking-fund-transfer/quickstart.md` including `compare.sh both` and confirm gateway traces for both MCP routes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories. FastMCP, gateway YAML, and LangGraph tracks can proceed in parallel after T001–T004
- **US1 (Phase 3)**: After Phase 2 — MVP
- **US2 (Phase 4)**: After Phase 2; extends strict schema already used by US1
- **US3 (Phase 5)**: After Phase 2; wire `oneOf` independent of US2
- **US4 (Phase 6)**: After US1 (needs a working strict internal path); uses US2 compliance prompt
- **Polish (Phase 7)**: After desired stories

### User Story Dependencies

- **US1 (P1)**: After Foundational
- **US2 (P2)**: After Foundational; independently testable via contract tests
- **US3 (P3)**: After Foundational; independently testable via contract tests
- **US4 (P4)**: Needs US1 happy path + US2 const code in the prompt; compare script is the demo

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Schema/ledger before FastMCP handlers
- Gateway YAML before integration tests that call `:8080`
- Repair classifier before compare CLI

### Parallel Opportunities

- T003/T004 after T001
- T005/T006/T008; T013/T015; T016/T017
- T022/T023; T027; T030; T033/T034
- T042/T043/T044

---

## Parallel Example: User Story 1

```bash
# Tests first:
Task: "Contract tests in tests/contract/test_transfer_funds_internal.py"
Task: "Unit tests in tests/unit/test_ledger.py"

# Then implementation:
Task: "Record internal transfers in src/mcp/server_strict.py"
```

## Parallel Example: Foundational workstreams

```bash
# FastMCP:
Task: "Copy schemas to src/mcp/schemas/"
Task: "Ledger in src/mcp/ledger.py"
Task: "Legacy server in src/mcp/server_legacy.py"

# agentgateway (after T010, sequential YAML edits):
Task: "CEL + headers in src/gateway/config.yaml"

# LangGraph:
Task: "state.py and llm.py in parallel"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (FastMCP + gateway YAML + LangGraph client)
3. Phase 3 US1 internal transfer
4. **STOP and VALIDATE** contract tests + one gateway `tools/call`

### Incremental Delivery

1. Setup + Foundational
2. US1 internal → demo baseline
3. US2 compliance `if`/`then`
4. US3 wire `oneOf`
5. US4 `compare.sh both` (failure vs recovery)

### Parallel Team Strategy

1. Shared Setup + Foundational
2. Then: A = FastMCP/schema stories (US1–US3), B = gateway YAML, C = LangGraph + US4 tests

---

## Notes

- [P] = different files, no incomplete-task dependencies
- Gateway YAML tasks T010–T012 share `src/gateway/config.yaml` — run sequentially
- Unit tests that hit FastMCP without the gateway MUST document the bypass
- Contract mode is CLI-only (`--contract`), never `.env`
- Commit after each task or workstream group
