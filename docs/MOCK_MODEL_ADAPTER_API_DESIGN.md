# Mock Model Adapter API Design

> M10-GUI-AGENT-MOCK-T001 | Mock-only model adapter API architecture  
> Status: DESIGN | Date: 2026-07-11  
> Depends on: M10-GUI-AGENT-T003 (model-output validator), M10-GUI-AGENT-CLOSEOUT  
> Feeds into: M10-GUI-AGENT-MOCK-T002 (fixture integration)

---

## 1. Executive Summary

This document defines the **Mock Model Adapter API** — a mock-only wrapper that connects fixture-supplied raw model outputs to the existing model-output adapter (`validate_and_normalize_model_output`) and the guarded `/api/gui-agent/step` pipeline. It enables end-to-end testing of the adapter→guard chain without connecting a real fine-tuned model, calling inference, or opening any GUI execution path beyond `record_observation`.

**Key invariants:**
- No real model is connected. All model outputs come from mock fixtures.
- The existing adapter (`gui_agent_model_adapter.py`) is the sole validator — the API does not add new validation logic.
- The existing guard pipeline is the sole authorization boundary — the API never sets `provider_call_allowed=true`.
- Rejected model outputs are returned with structured `MODEL_ACTION_REJECTED` and never reach the guard or provider.
- Mapped outputs that pass the adapter are forwarded to the guarded step route under existing mock session constraints.

---

## 2. Current Adapter / Guard Baseline

### What exists today

| Component | File | Role |
|-----------|------|------|
| Model-output validator | `gui_agent_model_adapter.py` | Validates raw model output, maps safe observation → `record_observation` |
| Provider gate | `gui_agent_guard.py` | `validate_gui_provider_policy()` — mock-only |
| Session validator | `gui_agent_guard.py` | `validate_gui_session_declaration()` — 18 fields |
| Action classifier | `gui_agent_guard.py` | `classify_gui_action_tier()` — 41 actions |
| Action validator | `gui_agent_guard.py` | `validate_gui_action_declaration()` — 17 checks |
| Stop-condition checker | `gui_agent_guard.py` | `validate_gui_stop_conditions()` — 9 checks |
| Audit pre-create | `gui_agent_guard.py` | `create_gui_audit_record()` — 24 fields |
| Guarded API routes | `gui_agent_routes.py` | `POST /api/gui-agent/sessions`, `POST .../step` |

### What's needed

A **Mock Model Adapter API** that bridges the gap between mock model outputs and the guarded step route, providing a single call surface for end-to-end adapter→guard testing.

---

## 3. Scope and Non-Goals

### Scope

- Design an API that accepts mock raw model outputs, runs them through the existing validator, and conditionally forwards mapped results to the guarded `POST /api/gui-agent/step` route.
- Define request/response schemas for mapped and rejected outcomes.
- Define the adapter invocation → guard submission flow.
- Define audit metadata that bridges model-level and guard-level records.
- Provide a test strategy for future T003/T004 implementation tasks.

### Non-Goals

- Connecting a real fine-tuned model — no inference, no weights, no OpenAI/LLM/VLM calls.
- Enabling PyWinAuto or any real GUI provider.
- Opening new action types beyond `record_observation`.
- Adding Tier 1/2/3 execution capability.
- Enabling screenshot, clipboard, mouse, keyboard, or network access.
- Opening GUI/manual reviewed execution allowlist entries.
- Implementing the API — this is a design document only.

---

## 4. Mock Model Adapter API Architecture

```
Mock model fixture / manually supplied raw model output
       │
       ▼
┌──────────────────────────────────────────┐
│        Mock Model Adapter API             │
│                                            │
│  1. Validate request envelope              │
│  2. Call validate_and_normalize_model_     │
│     output() — existing pure validator     │
│  3. If MODEL_ACTION_REJECTED:              │
│       → return rejection, STOP             │
│     If NORMALIZED_ACTION_READY:            │
│       → convert to GuiAgentStepRequest     │
│       → submit to POST .../step (guarded)  │
│       → attach guard result + audit_id     │
│       → return mapped response             │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│     Existing Guarded API Routes           │
│     POST /api/gui-agent/sessions/{id}/    │
│     step                                  │
│       → action validator                  │
│       → stop-condition checker            │
│       → audit pre-create                  │
│       → MockGuiProvider.perform_step()    │
└──────────────────────────────────────────┘
```

**Critical design rule:** The adapter API is a convenience wrapper, not an authority boundary. The existing guard pipeline remains the sole source of truth for authorization. The adapter API never sets `provider_call_allowed=true` — only the guard can grant that.

---

## 5. Mock Model Request Schema

```json
{
  "session_id": "gui_abc123",
  "model_output": {
    "model_output_id": "model_out_001",
    "source": "fine_tuned_gui_agent",
    "raw_text": "observe current state",
    "raw_json": null,
    "observed_context_summary": "mock-only fixture — no real UI context",
    "timestamp": "2026-07-11T00:00:00Z"
  },
  "submit_to_guard": true,
  "dry_run": false
}
```

| Field | Type | Required | Constraints |
|-------|------|:---:|------|
| `session_id` | `string` | Yes (if `submit_to_guard=true`) | Must reference a valid mock session created via `POST /api/gui-agent/sessions` |
| `model_output.model_output_id` | `string` | Yes | Unique per invocation |
| `model_output.source` | `string` | Yes | Must be `"fine_tuned_gui_agent"` |
| `model_output.raw_text` | `string \| null` | Yes | Untrusted; passed to validator |
| `model_output.raw_json` | `object \| null` | No | Untrusted; passed to validator |
| `model_output.observed_context_summary` | `string \| null` | No | Must be sanitized |
| `model_output.timestamp` | `string` | Yes | ISO-8601 UTC |
| `submit_to_guard` | `boolean` | Yes | If `true`, forward mapped result to guarded step route |
| `dry_run` | `boolean` | No | If `true`, return adapter result without calling guard |

**Rules:**
- `submit_to_guard=true` is only allowed when the adapter decision is `mapped` (i.e., `ok=true`). Rejected outputs are never submitted.
- `dry_run=true` returns the normalized or rejection result without any guard/provide
r call — useful for testing the adapter in isolation.
- `session_id` is validated by the existing guarded step route, not by the adapter API.

---

## 6. Mock Model Response Schema

### Mapped Response (`ok=true`)

```json
{
  "ok": true,
  "status": "MODEL_ACTION_MAPPED",
  "model_output_id": "model_out_001",
  "adapter_decision": "mapped",
  "normalized_action_type": "record_observation",
  "submitted_to_guard": true,
  "guard_status": "GUI_GUARD_OK",
  "audit_id": "audit_f7a3b2c1d4e5f6",
  "step_result": { … },
  "provider_call_allowed_by_adapter": false,
  "provider_call_allowed_by_guard": true,
  "desktop_touched": false,
  "screenshot_captured": false,
  "clipboard_accessed": false,
  "mouse_used": false,
  "keyboard_used": false
}
```

| Field | Meaning |
|-------|---------|
| `provider_call_allowed_by_adapter` | Always `false` — adapter never grants permission |
| `provider_call_allowed_by_guard` | `true` only if guard authorized provider call |
| `guard_status` | Result from guarded step route (`GUI_GUARD_OK` or blocked code) |
| `step_result` | Full response from `POST .../step` (includes audit record) |

### Rejected Response (`ok=false`)

```json
{
  "ok": false,
  "status": "MODEL_ACTION_REJECTED",
  "model_output_id": "model_out_002",
  "adapter_decision": "rejected",
  "adapter_rejection_reason": "tier_3_action_blocked",
  "submitted_to_guard": false,
  "guard_status": null,
  "audit_id": null,
  "step_result": null,
  "provider_call_allowed_by_adapter": false,
  "provider_call_allowed_by_guard": false,
  "desktop_touched": false,
  "screenshot_captured": false,
  "clipboard_accessed": false,
  "mouse_used": false,
  "keyboard_used": false,
  "rejection": {
    "reason": "tier_3_action_blocked",
    "blocked_terms": ["click_run"],
    "computed_tier": 3,
    "policy": "Tier 3 actions are blocked by default."
  }
}
```

### Dry-Run Response

Same as the mapped or rejected response, but `submitted_to_guard=false` and `guard_status=null`. The adapter result is returned without any guard or provider interaction.

---

## 7. Adapter Invocation Flow

```
1. Receive request:
     session_id: "gui_abc123"
     model_output: { raw_text: "observe current state", ... }
     submit_to_guard: true

2. Validate request envelope:
     - model_output.model_output_id must be present and non-empty
     - model_output.source must be "fine_tuned_gui_agent"
     - If submit_to_guard=true, session_id must be present

3. Call validate_and_normalize_model_output(
     model_output_id=...,
     source=...,
     raw_text=...,
     raw_json=...,
     ...
   )

4. If result.ok == false (MODEL_ACTION_REJECTED):
     → Return rejection response with submitted_to_guard=false
     → Do NOT call /api/gui-agent/step
     → Do NOT call provider

5. If result.ok == true (NORMALIZED_ACTION_READY):
     a) Convert normalized_action to GuiAgentStepRequest payload
     b) If dry_run=true:
          → Return mapped result without calling guard
     c) If submit_to_guard=true:
          → POST /api/gui-agent/sessions/{session_id}/step
          → Attach guard response to result
          → Return mapped response
     d) If submit_to_guard=false:
          → Return mapped result without calling guard
```

---

## 8. Guard Submission Flow

The adapter API may only submit normalized actions that satisfy **all** v1 constraints:

| Field | v1 Allowed Value |
|-------|------|
| `action_type` | `"record_observation"` |
| `action_tier` | `0` |
| `read_only` | `true` |
| `uses_screenshot` | `false` |
| `uses_clipboard` | `false` |
| `uses_keyboard` | `false` |
| `uses_mouse` | `false` |
| `network_access` | `false` |
| `input_paths` | `[]` |
| `output_paths` | `[]` |
| `expected_side_effects` | `"none"` |
| `requires_per_action_confirmation` | `false` |
| `rollback_plan` | `"none"` |
| `stop_conditions` | Non-empty |

**Explicitly blocked from submission:**
- Any normalized action where `action_type != "record_observation"`
- Any rejected model output (`normalized_action=null`)
- Any output containing provider, approved, or session declaration fields from the model
- Any output proposing Tier 1/2/3 actions

The existing guarded step route performs its own validation as defense-in-depth. The adapter API's guard submission is additive — it does not replace the guard checks.

---

## 9. Rejection Flow

```
1. Adapter returns MODEL_ACTION_REJECTED

2. API constructs rejection response:
     ok: false
     status: "MODEL_ACTION_REJECTED"
     adapter_rejection_reason: (from adapter)
     submitted_to_guard: false
     guard_status: null
     provider_call_allowed_by_adapter: false
     provider_call_allowed_by_guard: false
     rejection: { reason, blocked_terms, computed_tier, policy }

3. Response returned to caller

4. No guard call. No provider call. No audit record created by the API.
   (Audit of the rejection itself is at the adapter level — schema-defined, not persisted today.)
```

---

## 10. Audit Metadata Flow

The response carries model-level audit metadata:

| Field | Source | Persisted? |
|-------|--------|:---:|
| `model_output_id` | Request | In response |
| `adapter_decision` | Adapter | In response |
| `adapter_rejection_reason` | Adapter (if rejected) | In response |
| `normalized_action_type` | Adapter (if mapped) | In response |
| `submitted_to_guard` | API logic | In response |
| `guard_status` | Guard step route | In response |
| `audit_id` | Guard step route (`create_gui_audit_record`) | In response + on disk |
| `raw_model_output_stored` | API logic | `false` (never stored) |
| `rationale_summary_stored` | Adapter | `true` (in response only) |
| `chain_of_thought_stored` | Adapter | `false` (never stored) |

**Prohibited in audit metadata:**
- Chain-of-thought traces
- Raw screenshots or image data
- Raw clipboard contents
- Credentials, API keys, tokens, passwords
- Unredacted PHI or subject identifiers

---

## 11. Error Response Schema

Standardized error for invalid requests:

```json
{
  "ok": false,
  "status": "MOCK_ADAPTER_REQUEST_INVALID",
  "error_code": "MISSING_MODEL_OUTPUT_ID",
  "message": "model_output.model_output_id is required.",
  "provider_call_allowed": false,
  "desktop_touched": false,
  "screenshot_captured": false,
  "clipboard_accessed": false,
  "mouse_used": false,
  "keyboard_used": false
}
```

Error codes:

| Code | Condition |
|------|------|
| `MISSING_MODEL_OUTPUT_ID` | `model_output.model_output_id` is missing or empty |
| `INVALID_SOURCE` | `model_output.source` is not `"fine_tuned_gui_agent"` |
| `MISSING_SESSION_ID` | `submit_to_guard=true` but `session_id` is missing |
| `SESSION_NOT_FOUND` | Referenced session does not exist |
| `SUBMIT_BLOCKED_BY_ADAPTER` | `submit_to_guard=true` but adapter rejected the output |

---

## 12. Safety Boundaries

```
MOCK ADAPTER API DOES NOT:
  - Call a real model
  - Call model inference
  - Load model weights
  - Call any LLM/VLM API (OpenAI, local, etc.)
  - Expose provider selection
  - Approve actions
  - Bypass any guard layer
  - Enable PyWinAuto
  - Open GUI reviewed execution
  - Allow Tier 1/2/3 actions
  - Allow screenshot, clipboard, mouse, keyboard, network

MOCK ADAPTER API DOES:
  - Accept mock/fixture raw model outputs
  - Call the existing pure-function validator
  - Forward mapped record_observation to the guarded step route
  - Return structured rejection for unsafe outputs
  - Carry model-level audit metadata in the response
```

---

## 13. Future Fixture Integration Plan

The following tasks implement this design:

```
M10-GUI-AGENT-MOCK-T002: Mock model fixture integration
  - Define mock model output fixtures (safe + unsafe examples)
  - Create a test fixture catalog covering all rejection categories

M10-GUI-AGENT-MOCK-T003: Mock adapter API route implementation
  - Implement the API route (new router or extension)
  - Integration with validate_and_normalize_model_output()
  - Guard submission via existing POST .../step

M10-GUI-AGENT-MOCK-T004: Adapter-to-guard API integration tests
  - End-to-end tests: fixture → adapter API → guard → provider
  - Verify all rejection categories produce correct responses
  - Verify audit metadata flow

M10-GUI-AGENT-MOCK-T005: Model-output audit metadata persistence design
  - Design persistent storage for model-level audit records
  - Define retention and redaction policies

M10-GUI-AGENT-MOCK-CLOSEOUT: Mock model integration closeout
```

---

## 14. Future API Integration Tests (T004 Basis)

At least 25 test benchmarks:

### Happy Path (3)
1. Safe observation mock output → mapped → submitted to guard → HTTP 200
2. Safe observation mock output → dry_run=true → returns normalized result, no guard call
3. Mapped response contains audit_id from guard

### Rejection Categories (10)
4. click_run mock output → MODEL_ACTION_REJECTED, not submitted
5. pywinauto mock output → MODEL_ACTION_REJECTED
6. approved=true mock output → MODEL_ACTION_REJECTED
7. screenshot mock output → MODEL_ACTION_REJECTED
8. clipboard mock output → MODEL_ACTION_REJECTED
9. rawdata path mock output → MODEL_ACTION_REJECTED
10. credentials mock output → MODEL_ACTION_REJECTED
11. ambiguous intent mock output → MODEL_ACTION_REJECTED
12. multi-action plan mock output → MODEL_ACTION_REJECTED
13. policy override mock output → MODEL_ACTION_REJECTED

### Safety Flags (4)
14. Mapped response: `provider_call_allowed_by_adapter=false`, `by_guard=true`
15. Rejected response: both `provider_call_allowed` flags false
16. All desktop/screenshot/clipboard/mouse/keyboard flags false on both paths
17. Adapter API never sets `provider_call_allowed=true` for any input

### Error Handling (4)
18. Missing model_output_id → MOCK_ADAPTER_REQUEST_INVALID
19. Wrong source → MOCK_ADAPTER_REQUEST_INVALID
20. submit_to_guard=true without session_id → error
21. submit_to_guard=true with rejected output → SUBMIT_BLOCKED_BY_ADAPTER

### Regression (4)
22. Existing adapter validator tests still pass
23. Existing guarded API tests still pass
24. PyWinAuto not imported
25. No real model call traceable

---

## 15. Acceptance Criteria Before Implementation

1. Design document reviewed and approved
2. All 21+ rejection categories from `gui_agent_model_adapter.py` are mapped to API responses
3. Guard submission constraints are explicit and testable
4. Audit metadata fields are defined
5. Error response schema is defined
6. Safety boundaries are explicit
7. No path from the API can bypass the existing guard
8. No path from the API can call a real model
9. No path from the API can enable PyWinAuto

---

## 16. References

| Document | Content |
|----------|---------|
| `docs/FINE_TUNED_GUI_AGENT_ACTION_ADAPTER_DESIGN.md` | Adapter architecture, model output classes |
| `docs/NORMALIZED_GUI_ACTION_SCHEMA.md` | 5 schema envelopes |
| `docs/M9_GUI_AGENT_API_GUARD_CLOSEOUT.md` | Guard phase closeout |
| `docs/M10_GUI_AGENT_ADAPTER_PHASE_CLOSEOUT.md` | Adapter phase closeout |
| `src/backend/app/runtime/gui_agent_model_adapter.py` | Model-output validator |
| `src/backend/app/api/gui_agent_routes.py` | Guarded API routes |
