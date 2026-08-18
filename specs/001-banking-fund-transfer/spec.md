# Feature Specification: Enterprise Banking Fund Transfer Agent

**Feature Branch**: `001-banking-fund-transfer`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Build an Enterprise Banking Agent demo that processes fund transfer requests. FastMCP server exposing a 'transfer_funds' tool defined using JSON Schema 2020-12. Tool parameters must enforce a discriminator ('transfer_type' = 'internal' vs 'wire'). Conditional rule: Transfers over $10,000 strictly require a 'compliance_approval_code'. Wire transfers strictly require valid IBAN and SWIFT pattern formats. Demonstrate how a local LM Studio model initially fails a legacy schema, but recovers using 2020-12 schema validation feedback via agentgateway. Use .env to manage model endpoint and model name and other relevant execution variables, starting with qwen/qwen3.8-27b served on http://127.0.0.1:1234"

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

A bank operations operator requests a transfer whose amount is greater than $10,000. The system refuses to record it until a compliance approval code is supplied. Once a code is present, a valid transfer of that amount can complete.

**Why this priority**: High-value gating is the primary conditional rule that vague, description-only contracts fail to enforce.

**Independent Test**: Submit an otherwise valid transfer with amount $10,000.01 and no approval code; confirm it is blocked. Resubmit with a non-empty `compliance_approval_code`; confirm it is recorded.

**Acceptance Scenarios**:

1. **Given** an internal or wire transfer with amount greater than $10,000 and no `compliance_approval_code`, **When** the request is submitted, **Then** funds are not recorded and the rejection names the compliance rule.
2. **Given** the same transfer with a non-empty `compliance_approval_code`, **When** the request is submitted, **Then** the transfer is recorded (subject to the other rules for that transfer type).
3. **Given** a transfer of exactly $10,000, **When** no approval code is supplied, **Then** the compliance rule does not apply and the transfer is not rejected for missing the code.

---

### User Story 3 - Submit a wire transfer with valid routing identifiers (Priority: P3)

A bank operations operator sends funds to an external bank. The request is accepted only when `transfer_type` is `wire` and both destination IBAN and bank SWIFT identifiers match the required patterns. Internal-account fields MUST NOT substitute for those identifiers.

**Why this priority**: Wire shape is the mutually exclusive branch of the discriminator. It proves exclusive argument objects, not only extra optional fields.

**Independent Test**: Submit a wire with valid IBAN and SWIFT (and amount $10,000 or less). Confirm it is recorded. Submit a wire with a malformed IBAN or SWIFT and confirm rejection. Submit an internal-shaped payload labeled `wire` and confirm rejection.

**Acceptance Scenarios**:

1. **Given** `transfer_type` is `wire`, a valid IBAN, a valid SWIFT, source account, and amount $10,000 or less, **When** the operator submits the request, **Then** the transfer is recorded and confirmation includes a destination summary derived from the IBAN.
2. **Given** a wire request with IBAN or SWIFT that does not match the required pattern, **When** the request is submitted, **Then** funds are not recorded and the rejection names the violated identifier rule.
3. **Given** `transfer_type` is `wire` but only internal destination-account fields are provided, **When** the request is submitted, **Then** the transfer is not recorded.

---

### User Story 4 - Recover from an illegal transfer using strict-contract feedback (Priority: P4)

A demo operator runs the same small local model against two contracts. Against a legacy, description-only contract, the model omits a required conditional field (for example a high-value transfer without a compliance code, or a wire without IBAN/SWIFT) and the illegal call is not reliably stopped or repaired. Against the strict contract, the perimeter rejects the illegal payload with a precise validation error; the agent feeds that error back, changes the arguments, and completes a legal transfer without restarting.

**Why this priority**: This is the demonstration thesis of the project—small models fail vague contracts and recover when validation feedback is explicit. It depends on stories 1–3 for rules to enforce.

**Independent Test**: Run the comparison with a high-value or wire prompt that the small model typically under-specifies. On the legacy path, observe failure or an un-repaired illegal call. On the strict path, observe a rejected first call, a changed retry, and a recorded legal transfer within the repair bound.

**Acceptance Scenarios**:

1. **Given** the legacy (description-only) contract and a prompt that needs a conditional field, **When** the local model issues a tool call missing that field, **Then** the demo shows that the call is not repaired into a legal transfer (the model does not converge).
2. **Given** the strict contract and the same prompt, **When** the model issues an illegal first call, **Then** the perimeter rejects it before the tool records funds, the agent receives the validation reason, and a subsequent call uses **changed** arguments.
3. **Given** a strict-contract repair loop, **When** a legal payload is produced within three repair attempts, **Then** the transfer is recorded and the operator sees confirmation without restarting the agent.
4. **Given** a strict-contract repair loop, **When** the model would resubmit the identical illegal payload, **Then** that attempt is not treated as progress and does not record funds.

---

### Edge Cases

- Amount of exactly $10,000: compliance approval code is **not** required (`over $10,000` means strictly greater than 10000).
- Amount of $10,000.01: compliance approval code **is** required for both internal and wire.
- Amount of zero, negative, or more than two decimal places: rejected before funds are recorded.
- `transfer_type` omitted, misspelled, or both `internal` and `wire` shapes supplied together: rejected as a discriminator violation.
- IBAN that fails the checksum or length pattern, or SWIFT/BIC that is not 8 or 11 alphanumeric characters: rejected as a wire-identifier violation.
- Empty or whitespace-only `compliance_approval_code` when amount is over $10,000: treated as missing.
- Repair budget exhausted (three failed repairs after the first illegal call): agent stops retrying, reports that the transfer was not recorded, and does not crash.
- Non-validation failures (tool unavailable, model endpoint down): follow a distinct failure path; they MUST NOT be presented as schema violations.
- Runtime configuration missing model endpoint or model name: the demo fails fast at startup with a message naming the missing setting.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a fund-transfer capability named `transfer_funds` that records a simulated transfer when the payload is legal and returns a confirmation with transfer identifier, `transfer_type`, amount, and destination summary.
- **FR-002**: Every `transfer_funds` payload MUST include a discriminator `transfer_type` whose value is exactly `internal` or `wire`. Other values, omission, and mixed shapes MUST be rejected.
- **FR-003**: An `internal` transfer MUST require `source_account`, `destination_account`, and `amount`. It MUST NOT require IBAN or SWIFT.
- **FR-004**: A `wire` transfer MUST require `source_account`, `amount`, destination `iban` matching the IBAN pattern, and `swift` matching the SWIFT/BIC pattern (8 or 11 alphanumeric characters). Internal destination-account fields MUST NOT satisfy a wire request.
- **FR-005**: When `amount` is greater than 10000, `transfer_funds` MUST reject the payload unless `compliance_approval_code` is present and non-empty (no whitespace-only values). This rule applies to both `internal` and `wire`.
- **FR-006**: When `amount` is less than or equal to 10000, `compliance_approval_code` MUST NOT be required.
- **FR-007**: Amount MUST be a finite number greater than 0 with at most two decimal places. Zero, negative, non-numeric, and over-precision values MUST be rejected.
- **FR-008**: The `transfer_funds` input contract MUST be JSON Schema 2020-12. It MUST use `oneOf` (with `transfer_type` as discriminator) for internal vs wire shapes, `if`/`then` for the amount-over-10000 compliance rule, and `$defs` for shared fragments (accounts, amount, compliance code, IBAN, SWIFT). Enforceable rules MUST NOT exist only in natural-language descriptions.
- **FR-009**: Invalid payloads MUST be rejected at the governed proxy as JSON-RPC error `-32602` (Invalid params) **before** the tool implementation records funds. The error payload MUST name the violated rule in a form the agent can parse.
- **FR-010**: The agent MUST treat `-32602` as a recoverable validation failure: parse the error, change arguments, and retry. The repair budget is three attempts after the first illegal call. Retrying the identical invalid payload is forbidden and MUST NOT count as a successful repair.
- **FR-011**: Non-validation errors MUST follow a distinct failure path and MUST NOT be classified as schema failures.
- **FR-012**: The demo MUST provide a legacy (description-only) contract path for the same `transfer_funds` capability, used only to show that the local model fails to converge on a legal payload for a prompt that needs a conditional field.
- **FR-013**: The demo MUST provide a strict 2020-12 path in which the same prompt yields perimeter rejection, changed retries, and a recorded legal transfer within the repair budget (User Story 4).
- **FR-014**: Model endpoint, model name, and other runtime settings (proxy URL, tool-server URL, repair budget if overridden) MUST be read from environment configuration via `.env`. Defaults: model endpoint `http://127.0.0.1:1234`, model name `qwen/qwen3.8-27b`. Missing required settings MUST fail fast at startup.
- **FR-015**: The demo MUST NOT move real funds, persist a production ledger, or require live bank connectivity. Recorded transfers are simulated in-process (or equivalent ephemeral store) for demonstration.

### Key Entities

- **FundTransferRequest**: A single transfer attempt. Attributes: `transfer_type` (internal | wire), `source_account`, `amount`, optional `destination_account` (internal), optional `iban` and `swift` (wire), optional `compliance_approval_code` when amount exceeds 10000.
- **TransferType**: Discriminator. Exactly one of `internal` or `wire`; selects which destination identifiers are legal.
- **ComplianceApproval**: Opaque code required when amount is greater than 10000; empty or whitespace is treated as absent.
- **ValidationFeedback**: Structured rejection for an illegal payload, including error code `-32602` and a rule-named message the agent uses to repair arguments.
- **TransferConfirmation**: Result of a legal transfer: identifier, type, amount, destination summary, timestamp.
- **ContractMode**: Demo switch between `legacy` (description-only) and `strict` (JSON Schema 2020-12 with `if`/`then`, `oneOf`, `$defs`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete a valid internal transfer of $10,000 or less without supplying wire identifiers or a compliance code, and receive a confirmation in that same attempt.
- **SC-002**: 100% of transfer attempts with amount greater than $10,000 and no compliance approval code are blocked before any transfer is recorded.
- **SC-003**: 100% of wire attempts with missing or malformed IBAN or SWIFT identifiers are blocked before any transfer is recorded.
- **SC-004**: On the strict-contract path, when the local model’s first call is illegal, a legal transfer is recorded within three repair attempts for the comparison prompts used in the demo, without restarting the agent.
- **SC-005**: In the side-by-side demo, the same local model and prompt fail to complete a legal transfer against the legacy contract, and succeed against the strict contract using validation feedback.
- **SC-006**: A demo operator can change model endpoint and model name without editing application source; only environment configuration changes.

## Constitution Constraints *(mandatory)*

- **MCP 2026-07-28**: Feature MUST use stateless Streamable HTTP. MUST NOT require `Mcp-Session-Id` affinity or a sticky `initialize` session before `tools/call`.
- **JSON Schema 2020-12**: FastMCP tool inputs MUST be 2020-12 schemas. Conditional args MUST use `if`/`then`; exclusive shapes MUST use `oneOf`; shared fragments MUST use `$defs`.
- **Validation resilience**: JSON-RPC `-32602` from agentgateway MUST be a recoverable agent path with bounded retries that change arguments. Identical invalid retries are out of spec.
- **Layering**: Agent orchestration, proxy governance, and MCP tool execution MUST remain separate. Tool traffic MUST pass through agentgateway.
- **Stack**: FastMCP implements `transfer_funds`; agentgateway enforces the strict schema at the edge; LangGraph owns the `-32602` repair loop. The local model is served in OpenAI-compatible form from the configured endpoint (default LM Studio at `http://127.0.0.1:1234`).

## Assumptions

- Target users are demo operators and engineers showing schema reliability, not production bank tellers. There is no customer-facing UI beyond the agent session.
- Currency is USD. The $10,000 threshold is a numeric comparison on `amount` (greater than 10000). No FX conversion.
- `source_account` and `destination_account` are non-empty opaque account identifiers (demo accepts strings of 6–34 alphanumeric characters). No live core-banking lookup.
- IBAN pattern follows the usual letter-letter plus check digits plus up to 30 alphanumeric characters; SWIFT/BIC is 8 or 11 alphanumeric characters. Full IBAN checksum MAY be enforced; pattern match is the minimum.
- `compliance_approval_code` is an opaque demo string (minimum 6 non-space characters). No external compliance-system callback.
- Repair budget defaults to three attempts after the first illegal call unless overridden in environment configuration.
- The local model is already running (LM Studio or compatible) at `http://127.0.0.1:1234` with id `qwen/qwen3.8-27b`. The demo does not start the model process.
- Authentication, real payment rails, sanctions screening, and durable ledgers are out of scope.
- The legacy contract exists only for the comparison demo; it is not an alternate production mode.
- Environment file `.env` is the source for model endpoint, model name, proxy URL, tool-server URL, and optional repair-budget override. A documented example file is provided; secrets are not committed.
