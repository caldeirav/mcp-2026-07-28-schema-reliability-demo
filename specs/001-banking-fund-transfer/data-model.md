# Data Model: Enterprise Banking Fund Transfer Agent

## Entities

### FundTransferRequest

A single `transfer_funds` argument object.

| Field | Type | Rules |
|-------|------|--------|
| `transfer_type` | enum `internal` \| `wire` | Required discriminator |
| `source_account` | string | Pattern `^[A-Za-z0-9]{6,34}$` |
| `destination_account` | string | Required iff `internal`; same account pattern |
| `iban` | string | Required iff `wire`; pattern `^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$` |
| `swift` | string | Required iff `wire`; 8 or 11 alphanumeric |
| `amount` | number | `> 0`, at most two decimal places (`multipleOf` 0.01) |
| `compliance_approval_code` | string | Required iff `amount > 10000`; **const** `CMP-DEMO-2026` |

Relationships: classified by `TransferType`. Validated by strict JSON Schema 2020-12 (`oneOf` + `if`/`then` + `$defs`) on the strict route.

### TransferType

Discriminator. Exactly one of `internal` or `wire`. Mixed shapes (both destination account and IBAN) are rejected.

### ComplianceApproval

Not a separate store. The only legal value is `CMP-DEMO-2026`. Empty, whitespace, and invented values fail validation.

### ValidationFeedback

Gateway JSON-RPC error on the strict route.

| Field | Rules |
|-------|--------|
| `code` | `-32602` |
| `message` | Names the violated rule (discriminator, amount, IBAN/SWIFT, compliance const) |
| `data` | Optional structured validator output the repair node copies into chat |

Legacy route MUST NOT produce this as a repair signal (opaque tool error instead).

### TransferConfirmation

Emitted only when the simulated ledger records a row.

| Field | Rules |
|-------|--------|
| `transfer_id` | Unique per process (UUID) |
| `transfer_type` | `internal` \| `wire` |
| `amount` | Echo of accepted amount |
| `destination_summary` | Internal account or IBAN prefix |
| `timestamp` | ISO-8601 UTC |

### ContractMode

Runtime parameter only: `legacy` \| `strict` \| `both`. Never persisted in `.env`. `both` runs legacy then strict against the same prompt and model.

### ComparisonReport

Stdout (and optional JSON) per invoked route.

| Field | Rules |
|-------|--------|
| `contract_mode` | `legacy` or `strict` |
| `error_kind` | `opaque` \| `-32602` \| `none` \| `other` |
| `repair_attempts` | Integer 0–budget |
| `transfer_recorded` | boolean |
| `transfer_id` | Present iff recorded |

### GatewayTrace

OTLP spans emitted by agentgateway. Must distinguish route (`/mcp/strict` vs `/mcp/legacy` and/or LLM `/v1`). Agent-side tracers are not the source of truth.

### AgentGraphState (orchestrator)

Not a persisted entity. LangGraph state:

| Field | Purpose |
|-------|---------|
| `messages` | Chat + tool messages (`add_messages`) |
| `contract_mode` | Selected route |
| `repair_attempts` | Count of `-32602` repairs |
| `last_error_kind` | Classifier output |
| `last_payload_fingerprint` | Hash of last tool args; identical retry forbidden |
| `transfer_recorded` | Set when confirmation received |

## State transitions (transfer)

```text
submitted → gateway_admit
              │
              ├─ strict + schema fail → rejected_32602 → (repair | budget_exhausted)
              ├─ legacy + business fail → rejected_opaque (terminal; not recorded)
              └─ admitted → tool_execute
                               ├─ legal → recorded (TransferConfirmation)
                               └─ illegal → rejected_opaque (must not record)
```

Illegal payloads never enter `recorded`.

## Validation summary

- **Strict schema**: `contracts/transfer_funds.strict.schema.json` / `src/mcp/schemas/transfer_funds.strict.json` (identical).
- **Legacy schema**: description-only; all business fields optional; no `if`/`then` / `oneOf` discriminator enforcement.
- **Ledger**: append-only in-memory list; process lifetime only.
