# Feature Specification: Enterprise Banking Fund Transfer Agent

**Feature Branch**: `001-banking-fund-transfer`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Build an Enterprise Banking Agent demo that processes fund transfer requests. FastMCP server exposing a 'transfer_funds' tool defined using JSON Schema 2020-12. Tool parameters must enforce a discriminator ('transfer_type' = 'internal' vs 'wire'). Conditional rule: Transfers over $10,000 strictly require a 'compliance_approval_code'. Wire transfers strictly require valid IBAN and SWIFT pattern formats. Demonstrate how a local LM Studio model initially fails a legacy schema, but recovers using 2020-12 schema validation feedback via agentgateway. Use .env to manage model endpoint and model name and other relevant execution variables, starting with qwen/qwen3.8-27b served on http://127.0.0.1:1234"

## Clarifications

### Session 2026-08-19

- Q: When the local model omits a required business field on the legacy contract, what is the intended outcome? → A: Illegal transfers are never recorded. Legacy returns an opaque failure with no repair loop. Strict rejects at the perimeter as `-32602` and the agent repairs.
- Q: How does the demo operator run the legacy vs strict comparison? → A: Both contracts are separate proxy routes in one topology. A script runs both using a runtime parameter (`legacy` | `strict` | `both`); contract mode MUST NOT be set via `.env`.
- Q: Where does a valid `compliance_approval_code` come from on the strict repair path? → A: The comparison prompt already contains the published demo code. Repair MUST copy that code into the payload; invented codes are rejected.
- Q: How strictly is IBAN validated? → A: Structural pattern only (two letters, two digits, up to 30 alphanumeric). No ISO 13616 MOD-97 checksum.
- Q: What must the comparison script show for observability? → A: Labeled script output plus distributed tracing emitted by the governed proxy (not a separate agent-side tracer as the source of truth).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit an internal fund transfer (Priority: P1)

A bank operations operator asks the agent to move funds between two accounts at the same institution. For amounts of $10,000 or less, the operator supplies source account, destination account, amount, and that the transfer is internal. The transfer is recorded and a confirmation is returned. International routing identifiers are not requested.

**Why this priority**: This is the minimum viable transfer path. If internal transfers do not complete under the strict contract, the rest of the demo has no success baseline.

**Independent Test**: Submit a same-institution transfer of $10,000 or less with `transfer_type` internal and both account identifiers. Confirm a recorded transfer and confirmation. Repeat without `transfer_type` or with wire-only fields in place of internal accounts and confirm rejection.

**Acceptance Scenarios**:

1. **Given** two valid internal accounts and an amount of $10,000 or less, **When** the operator requests an internal transfer, **Then** the system records the transfer and returns a confirmation that includes a transfer identifier, type, amount, and destination summary.
2. **Given** a request missing `transfer_type` or using a value other than `internal` or `wire`, **When** the operator submits it, **Then** the transfer is not recorded and the operator receives a rejection that names the discriminator rule.
3. **Given** an internal transfer request, **When** IBAN or SWIFT are omitted, **Then** the transfer still succeeds (those fields MUST NOT be required for internal transfers).

---

### User Story 2 - Block high-value transfers without compliance approval (Priority: P2)

A bank operations operator requests a transfer whose amount is greater than $10,000. The system refuses to record it until the **published demo compliance approval code** is supplied. Invented or empty codes are rejected. Once that code is present, a valid transfer of that amount can complete.

**Why this priority**: High-value gating is the primary conditional rule that vague, description-only contracts fail to enforce.

**Independent Test**: Submit an otherwise valid transfer with amount $10,000.01 and no approval code; confirm it is blocked. Resubmit with a non-matching code; confirm it is blocked. Resubmit with the published demo code `CMP-DEMO-2026`; confirm it is recorded.

**Acceptance Scenarios**:

1. **Given** an internal or wire transfer with amount greater than $10,000 and no `compliance_approval_code`, **When** the request is submitted, **Then** funds are not recorded and the rejection names the compliance rule.
2. **Given** the same transfer with `compliance_approval_code` equal to the published demo code `CMP-DEMO-2026`, **When** the request is submitted, **Then** the transfer is recorded (subject to the other rules for that transfer type).
3. **Given** a transfer of exactly $10,000, **When** no approval code is supplied, **Then** the compliance rule does not apply and the transfer is not rejected for missing the code.
4. **Given** a transfer over $10,000 with a non-empty but non-matching `compliance_approval_code`, **When** the request is submitted, **Then** funds are not recorded.

---

### User Story 3 - Submit a wire transfer with valid routing identifiers (Priority: P3)

A bank operations operator sends funds to an external bank. The request is accepted only when `transfer_type` is `wire` and both destination IBAN and bank SWIFT identifiers match the required patterns. Internal-account fields MUST NOT substitute for those identifiers.

**Why this priority**: Wire shape is the mutually exclusive branch of the discriminator. It proves exclusive argument objects, not only extra optional fields.

**Independent Test**: Submit a wire with a pattern-valid IBAN and SWIFT (and amount $10,000 or less). Confirm it is recorded. Submit a wire with a malformed IBAN or SWIFT and confirm rejection. Submit an internal-shaped payload labeled `wire` and confirm rejection. A pattern-valid IBAN that would fail MOD-97 MUST still be accepted.

**Acceptance Scenarios**:

1. **Given** `transfer_type` is `wire`, a valid IBAN, a valid SWIFT, source account, and amount $10,000 or less, **When** the operator submits the request, **Then** the transfer is recorded and confirmation includes a destination summary derived from the IBAN.
2. **Given** a wire request with IBAN or SWIFT that does not match the required pattern, **When** the request is submitted, **Then** funds are not recorded and the rejection names the violated identifier rule.
3. **Given** `transfer_type` is `wire` but only internal destination-account fields are provided, **When** the request is submitted, **Then** the transfer is not recorded.

---

### User Story 4 - Recover from an illegal transfer using strict-contract feedback (Priority: P4)

A demo operator runs a comparison script against the same small local model and prompt. Legacy and strict contracts are **separate routes** in the governed proxy (one session topology, two paths). The script selects the path with a **runtime parameter** (`legacy`, `strict`, or `both`); `.env` MUST NOT choose the contract. The comparison prompt **already includes** the published demo code `CMP-DEMO-2026` plus a high-value or wire request. Against the legacy route, the model omits a required conditional field (typically `compliance_approval_code`). The illegal call is **not recorded**; the operator sees an opaque failure and the agent does **not** repair it into a legal transfer. Against the strict route, the perimeter rejects the same class of payload with a precise `-32602` validation error; the agent feeds that error back, **copies `CMP-DEMO-2026` from the prompt** into the payload (it MUST NOT invent a different code), and completes a legal transfer without restarting.

**Why this priority**: This is the demonstration thesis of the project—small models fail vague contracts and recover when validation feedback is explicit. It depends on stories 1–3 for rules to enforce.

**Independent Test**: Invoke the comparison script with runtime parameter `both` and a high-value or wire prompt that the small model typically under-specifies. On the legacy route, observe an opaque failure, no recorded transfer, and no repair loop. On the strict route, observe a `-32602` rejection, a changed retry, and a recorded legal transfer within the repair bound. Confirm the script prints a labeled per-route report and that the governed proxy emitted traces for both routes. Repeat with `legacy` and `strict` to confirm each path can be selected without changing `.env`.

**Acceptance Scenarios**:

1. **Given** the legacy (description-only) contract and a prompt that needs a conditional field, **When** the local model issues a tool call missing that field, **Then** no transfer is recorded, the failure is opaque (not a parseable `-32602` repair signal), and the agent does not converge on a legal transfer.
2. **Given** the strict contract and the same prompt (which already contains `CMP-DEMO-2026`), **When** the model issues an illegal first call that omits the code, **Then** the perimeter rejects it before the tool records funds, the agent receives the validation reason, and a subsequent call includes `compliance_approval_code` equal to `CMP-DEMO-2026` (not an invented value).
3. **Given** a strict-contract repair loop, **When** a legal payload is produced within three repair attempts, **Then** the transfer is recorded and the operator sees confirmation without restarting the agent.
4. **Given** a strict-contract repair loop, **When** the model would resubmit the identical illegal payload, **Then** that attempt is not treated as progress and does not record funds.
5. **Given** the comparison script, **When** the operator passes runtime parameter `both` (or `legacy` then `strict`) without changing `.env`, **Then** both routes run against the same prompt and model.
6. **Given** a completed `both` run, **When** the operator reads the script output, **Then** each route is labeled with error kind (opaque vs `-32602`), repair attempt count, and whether a transfer was recorded.
7. **Given** a completed `both` run, **When** the operator inspects traces exported by the governed proxy, **Then** both the legacy and strict routes appear as distinct traced calls.

---

### Edge Cases

- Amount of exactly $10,000: compliance approval code is **not** required (`over $10,000` means strictly greater than 10000).
- Amount of $10,000.01: compliance approval code **is** required for both internal and wire.
- Amount of zero, negative, or more than two decimal places: rejected before funds are recorded.
- `transfer_type` omitted, misspelled, or both `internal` and `wire` shapes supplied together: rejected as a discriminator violation.
- IBAN that does not match the structural pattern (two letters, two digits, up to 30 alphanumeric), or SWIFT/BIC that is not 8 or 11 alphanumeric characters: rejected as a wire-identifier violation. MOD-97 checksum MUST NOT be required.
- Empty or whitespace-only `compliance_approval_code` when amount is over $10,000: treated as missing.
- Invented or non-matching `compliance_approval_code` (any value other than `CMP-DEMO-2026`) when amount is over $10,000: rejected; funds are not recorded.
- Repair budget exhausted (three failed repairs after the first illegal call): agent stops retrying, reports that the transfer was not recorded, and does not crash.
- Non-validation failures (tool unavailable, model endpoint down): follow a distinct failure path; they MUST NOT be presented as schema violations.
- Legacy-contract illegal payload: funds MUST NOT be recorded. The failure MUST NOT start the `-32602` repair loop (strict path only).
- Runtime configuration missing model endpoint or model name: the demo fails fast at startup with a message naming the missing setting.
- Comparison script invoked without a contract runtime parameter, or with a value other than `legacy` | `strict` | `both`: fail fast; do not read contract mode from `.env`.
- Tracing collector unreachable: the comparison still runs and prints script output; missing gateway traces fail the observability success criterion (SC-007), not the transfer-recording rules.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a fund-transfer capability named `transfer_funds` that records a simulated transfer when the payload is legal and returns a confirmation with transfer identifier, `transfer_type`, amount, and destination summary.
- **FR-002**: Every `transfer_funds` payload MUST include a discriminator `transfer_type` whose value is exactly `internal` or `wire`. Other values, omission, and mixed shapes MUST be rejected.
- **FR-003**: An `internal` transfer MUST require `source_account`, `destination_account`, and `amount`. It MUST NOT require IBAN or SWIFT.
- **FR-004**: A `wire` transfer MUST require `source_account`, `amount`, destination `iban` matching the structural IBAN pattern (`[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}`), and `swift` matching the SWIFT/BIC pattern (8 or 11 alphanumeric characters). Internal destination-account fields MUST NOT satisfy a wire request. ISO 13616 MOD-97 checksum MUST NOT be enforced.
- **FR-005**: When `amount` is greater than 10000, `transfer_funds` MUST reject the payload unless `compliance_approval_code` equals the published demo code `CMP-DEMO-2026`. Empty, whitespace-only, and any other value MUST be rejected. This rule applies to both `internal` and `wire`.
- **FR-006**: When `amount` is less than or equal to 10000, `compliance_approval_code` MUST NOT be required.
- **FR-007**: Amount MUST be a finite number greater than 0 with at most two decimal places. Zero, negative, non-numeric, and over-precision values MUST be rejected.
- **FR-008**: The `transfer_funds` input contract MUST be JSON Schema 2020-12. It MUST use `oneOf` (with `transfer_type` as discriminator) for internal vs wire shapes, `if`/`then` for the amount-over-10000 compliance rule, and `$defs` for shared fragments (accounts, amount, compliance code, IBAN, SWIFT). Enforceable rules MUST NOT exist only in natural-language descriptions.
- **FR-009**: On the **strict** path, invalid payloads MUST be rejected at the governed proxy as JSON-RPC error `-32602` (Invalid params) **before** the tool implementation records funds. The error payload MUST name the violated rule in a form the agent can parse. On the **legacy** path, an illegal payload MUST still not be recorded; rejection MAY occur after the weak contract admits the call, and MUST be an opaque (non-`-32602`-repair) failure.
- **FR-010**: The agent MUST treat `-32602` as a recoverable validation failure: parse the error, change arguments, and retry. The repair budget is three attempts after the first illegal call. Retrying the identical invalid payload is forbidden and MUST NOT count as a successful repair. For a missing high-value compliance code, a successful repair MUST set `compliance_approval_code` to `CMP-DEMO-2026` taken from the prompt; inventing a different code is not a successful repair.
- **FR-011**: Non-validation errors and **legacy opaque rejects** MUST follow a distinct failure path and MUST NOT be classified as schema failures or start the `-32602` repair loop.
- **FR-012**: The demo MUST expose the legacy (description-only) contract as a **separate governed-proxy route** for the same `transfer_funds` capability. That route MUST NOT record illegal transfers and MUST NOT run the `-32602` repair loop. It exists only to show that the local model fails to converge on a legal payload when feedback is opaque.
- **FR-013**: The demo MUST expose the strict 2020-12 contract as a **separate governed-proxy route** in which the same prompt yields perimeter rejection, changed retries, and a recorded legal transfer within the repair budget (User Story 4).
- **FR-014**: Model endpoint, model name, proxy URL, tool-server URL, OTLP collector endpoint for gateway traces, and optional repair-budget override MUST be read from `.env`. Defaults: model endpoint `http://127.0.0.1:1234`, model name `qwen/qwen3.8-27b`. Missing required settings MUST fail fast at startup. **Contract mode MUST NOT be an environment variable.**
- **FR-015**: The demo MUST NOT move real funds, persist a production ledger, or require live bank connectivity. Recorded transfers are simulated in-process (or equivalent ephemeral store) for demonstration.
- **FR-016**: A comparison script MUST accept a runtime parameter `legacy` | `strict` | `both` that selects which proxy route(s) to invoke. `both` MUST run legacy then strict against the same prompt and model. The script MUST fail fast on a missing or invalid parameter.
- **FR-017**: The comparison script MUST print labeled per-route output for every invoked route: contract mode, error kind (`opaque` vs `-32602`), repair attempt count, and whether a transfer was recorded.
- **FR-018**: The governed proxy MUST emit distributed traces (OTLP) for proxied `transfer_funds` calls on **both** routes. Tracing is implemented **via the gateway**, not by an agent-side tracer as the source of truth. Traces MUST distinguish legacy vs strict routes.

### Key Entities

- **FundTransferRequest**: A single transfer attempt. Attributes: `transfer_type` (internal | wire), `source_account`, `amount`, optional `destination_account` (internal), optional `iban` and `swift` (wire), optional `compliance_approval_code` when amount exceeds 10000.
- **TransferType**: Discriminator. Exactly one of `internal` or `wire`; selects which destination identifiers are legal.
- **ComplianceApproval**: Required when amount is greater than 10000. The only accepted value is the published demo code `CMP-DEMO-2026`. Empty, whitespace, and invented values are rejected. No external compliance-system callback.
- **ValidationFeedback**: Structured rejection for an illegal payload, including error code `-32602` and a rule-named message the agent uses to repair arguments.
- **TransferConfirmation**: Result of a legal transfer: identifier, type, amount, destination summary, timestamp.
- **ContractMode**: Runtime parameter (`legacy` | `strict` | `both`), not an environment variable. `legacy` and `strict` are separate proxy routes: description-only (opaque reject, no repair) vs JSON Schema 2020-12 with `if`/`then`, `oneOf`, `$defs` (perimeter `-32602` then repair).
- **ComparisonReport**: Labeled script output for one run: per-route error kind, repair attempts, recorded-or-not.
- **GatewayTrace**: Distributed trace span(s) emitted by the governed proxy for a proxied tool call, including which contract route was used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete a valid internal transfer of $10,000 or less without supplying wire identifiers or a compliance code, and receive a confirmation in that same attempt.
- **SC-002**: 100% of transfer attempts with amount greater than $10,000 and a missing or non-matching compliance approval code (anything other than `CMP-DEMO-2026`) are blocked before any transfer is recorded (both legacy and strict contract modes).
- **SC-003**: 100% of wire attempts with missing or malformed IBAN or SWIFT identifiers are blocked before any transfer is recorded (both legacy and strict contract modes).
- **SC-004**: On the strict-contract path, when the local model’s first call is illegal, a legal transfer is recorded within three repair attempts for the comparison prompts used in the demo, without restarting the agent.
- **SC-005**: The comparison script, given runtime parameter `both` and the same local model and prompt, produces an opaque unrepaired failure (no recorded transfer) on the legacy route and a repaired legal transfer on the strict route.
- **SC-006**: A demo operator can change model endpoint and model name without editing application source (`.env` only), and can choose `legacy` | `strict` | `both` without editing `.env` (runtime parameter only).
- **SC-007**: After a `both` run, the operator can read labeled per-route script output **and** inspect gateway-emitted traces for both the legacy and strict routes without adding an agent-side tracer as the source of truth.

## Constitution Constraints *(mandatory)*

- **MCP 2026-07-28**: Feature MUST use stateless Streamable HTTP. MUST NOT require `Mcp-Session-Id` affinity or a sticky `initialize` session before `tools/call`.
- **JSON Schema 2020-12**: FastMCP tool inputs MUST be 2020-12 schemas. Conditional args MUST use `if`/`then`; exclusive shapes MUST use `oneOf`; shared fragments MUST use `$defs`.
- **Validation resilience**: JSON-RPC `-32602` from agentgateway MUST be a recoverable agent path with bounded retries that change arguments. Identical invalid retries are out of spec.
- **Layering**: Agent orchestration, proxy governance, and MCP tool execution MUST remain separate. Tool traffic MUST pass through agentgateway.
- **Stack**: FastMCP implements `transfer_funds`; agentgateway enforces the strict schema at the edge **and** emits OTLP traces for proxied calls; LangGraph owns the `-32602` repair loop. The local model is served in OpenAI-compatible form from the configured endpoint (default LM Studio at `http://127.0.0.1:1234`).

## Assumptions

- Target users are demo operators and engineers showing schema reliability, not production bank tellers. There is no customer-facing UI beyond the agent session.
- Currency is USD. The $10,000 threshold is a numeric comparison on `amount` (greater than 10000). No FX conversion.
- `source_account` and `destination_account` are non-empty opaque account identifiers (demo accepts strings of 6–34 alphanumeric characters). No live core-banking lookup.
- IBAN validation is the structural pattern only: two letters, two digits, then 1–30 alphanumeric characters. SWIFT/BIC is 8 or 11 alphanumeric characters. Full IBAN MOD-97 checksum is out of scope; a pattern-valid IBAN that would fail checksum MUST still be accepted.
- `compliance_approval_code` is not a free-form string. The only valid demo value is `CMP-DEMO-2026`. Comparison prompts for User Story 4 MUST include that code in natural language so the model can copy it after `-32602` feedback. No external compliance-system callback.
- Repair budget defaults to three attempts after the first illegal call unless overridden in environment configuration.
- The local model is already running (LM Studio or compatible) at `http://127.0.0.1:1234` with id `qwen/qwen3.8-27b`. The demo does not start the model process.
- Authentication, real payment rails, sanctions screening, and durable ledgers are out of scope.
- The legacy contract exists only for the comparison demo; it is not an alternate production mode. Illegal payloads are never recorded on either path; only the strict path exposes parseable `-32602` feedback and a repair loop.
- Environment file `.env` is the source for model endpoint, model name, proxy URL, tool-server URL, OTLP collector endpoint, and optional repair-budget override. A documented example file is provided; secrets are not committed. Contract mode is a script runtime parameter only (`legacy` | `strict` | `both`).
- A local OTLP collector (Jaeger all-in-one) is started by `./scripts/run_jaeger.sh` (`compose.yaml`, loopback `:4317` / UI `:16686`). Distributed traces are produced by the governed proxy; the comparison script’s labeled stdout is the human-readable report.
