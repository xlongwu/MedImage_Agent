# Normalized GUI Action Schema

> M10-GUI-AGENT-T002 | Formal data contract for normalized GUI actions  
> Status: DESIGN | Date: 2026-07-11  
> Depends on: M10-GUI-AGENT-T001 (adapter design)  
> Feeds into: M10-GUI-AGENT-T003 (model-output validator)

---

## 1. Executive Summary

This document defines the formal data contract for the **Normalized GUI Action Schema** — the structured interchange format between a fine-tuned GUI Agent model and the existing guard pipeline. Every model output must be normalized into this schema before it can reach the guard, and only validated, safe actions proceed to `MockGuiProvider`.

**Key invariants:**
- Model output is untrusted. Schema validity does not imply permission.
- The guard pipeline (provider → session → action → stop → audit) remains the sole source of truth.
- The adapter cannot bypass any guard layer.
- `confidence` does not override policy. `rationale` does not override policy.
- `approved=true` and `provider` selection are not schema fields accepted from the model.
- v1 permits exactly **one** normalized action: `record_observation`.

---

## 2. Current Guard Baseline

The `/api/gui-agent/*` guard pipeline enforces:

| Layer | Function | v1 Constraint |
|-------|----------|------|
| Provider gate | `validate_gui_provider_policy()` | `provider=mock` only |
| Session validator | `validate_gui_session_declaration()` | 18 fields, 13 rejection conditions |
| Tier classifier | `classify_gui_action_tier()` | 41-action taxonomy |
| Action validator | `validate_gui_action_declaration()` | 17 checks; only `record_observation` |
| Stop-condition checker | `validate_gui_stop_conditions()` | 9 conditions |
| Audit pre-create | `create_gui_audit_record()` | 24-field record |

Real provider, PyWinAuto, all Tier 1/2/3 actions, screenshots, clipboard, mouse/keyboard, network, and file paths remain blocked.

---

## 3. Schema Design Principles

1. **Model output is untrusted.** Every field from the model must be validated; no field is accepted at face value.
2. **Schema validity ≠ permission.** A schema-conformant output that proposes an unsafe action must still be rejected.
3. **Guard is source of truth.** The adapter normalizes; the guard authorizes. The adapter never sets `provider_call_allowed=true`.
4. **Confidence does not override policy.** A high-confidence unsafe proposal is still unsafe.
5. **Rationale does not override policy.** The model's explanation is metadata, not authorization.
6. **No provider selection from model.** The model cannot choose `mock`, `pywinauto`, or any provider.
7. **No approval override from model.** `approved=true` is not a field in the normalized schema.
8. **Single action only.** Multi-action plans are rejected at the adapter.
9. **All safety flags default to blocked.** The adapter output has `provider_call_allowed=false` by design; the guard grants permission.

---

## 4. Action Taxonomy Count Normalization

**Correction:** The code comment in `gui_agent_guard.py:505` states "29 actions, 4 tiers". The actual count from the code constants is **41 actions across 4 tiers**.

| Tier | Constant | Count | Examples |
|:---:|------|:---:|------|
| 0 | `_TIER_0_ACTIONS` | **7** | `record_observation`, `get_window_title`, `screenshot_ephemeral`… |
| 1 | `_TIER_1_ACTIONS` | **6** | `focus_window`, `scroll`, `switch_tab`… |
| 2 | `_TIER_2_ACTIONS` | **6** | `fill_form_field_non_secret`, `click_dry_run`, `type_text_scoped`… |
| 3 | `_TIER_3_ACTIONS` | **22** | `click_run`, `save_file`, `read_clipboard`, `enter_credentials`… |
| **Total** | | **41** | |

**Source of truth:** `src/backend/app/runtime/gui_agent_guard.py` constants `_TIER_0_ACTIONS` through `_TIER_3_ACTIONS`. The code comment is stale; the frozen sets are authoritative. The earlier design doc `GUI_ACTION_TAXONOMY_AND_SANDBOX_CONTRACT.md` listed 29 actions (some entries were omitted from the taxonomy doc). All M10 documents use the canonical count of **41 actions**.

**v1 allowed:** 1 of 41 (`record_observation`). **40 actions remain blocked.**

---

## 5. Raw Model Output Envelope

The raw output from a fine-tuned GUI Agent, before any normalization:

```json
{
  "model_output_id": "model_out_001",
  "source": "fine_tuned_gui_agent",
  "raw_text": "observe current state",
  "raw_json": null,
  "observed_context_summary": "User asked for a safe mock observation.",
  "timestamp": "2026-07-11T00:00:00Z"
}
```

| Field | Type | Required | Constraints |
|-------|------|:---:|------|
| `model_output_id` | `string` | Yes | Unique per model invocation |
| `source` | `string` | Yes | Must be `"fine_tuned_gui_agent"` |
| `raw_text` | `string \| null` | Yes | Untrusted; never interpreted as command |
| `raw_json` | `object \| null` | No | Untrusted; validated structurally only |
| `observed_context_summary` | `string \| null` | No | Must be sanitized; no secrets, no PHI |
| `timestamp` | `string` | Yes | ISO-8601 UTC |

**Prohibited in raw output:**
- Raw screenshot bytes or base64-encoded images
- Raw clipboard contents
- Chain-of-thought reasoning traces
- Credentials, API keys, tokens, passwords
- PHI or unredacted subject identifiers
- Provider names (`mock`, `pywinauto`, etc.)
- `approved=true` or any approval flag

---

## 6. Normalized GUI Action Envelope

The adapter's output — a complete envelope wrapping the normalized action or rejection:

```json
{
  "ok": true,
  "status": "NORMALIZED_ACTION_READY",
  "source": "fine_tuned_gui_agent",
  "model_output_id": "model_out_001",
  "intent_type": "safe_observation",
  "adapter_decision": "mapped",
  "adapter_rejection_reason": null,
  "confidence": 0.82,
  "rationale_summary": "Model requested read-only observation.",
  "normalized_action": { … },
  "rejection": null,
  "safety_flags": {
    "provider_call_allowed": false,
    "desktop_touched": false,
    "screenshot_captured": false,
    "clipboard_accessed": false,
    "mouse_used": false,
    "keyboard_used": false
  }
}
```

| Field | Type | Required | Notes |
|-------|------|:---:|------|
| `ok` | `boolean` | Yes | `true` only if action is safe to submit to guard |
| `status` | `string` | Yes | `"NORMALIZED_ACTION_READY"` or `"MODEL_ACTION_REJECTED"` |
| `source` | `string` | Yes | `"fine_tuned_gui_agent"` |
| `model_output_id` | `string` | Yes | Links back to raw model output |
| `intent_type` | `string` | Yes | One of 6 intent classes |
| `adapter_decision` | `string` | Yes | `"mapped"`, `"rejected"`, or `"needs_clarification"` |
| `adapter_rejection_reason` | `string \| null` | No | Set only when rejected |
| `confidence` | `number` | Yes | 0.0–1.0; **does not override policy** |
| `rationale_summary` | `string` | Yes | Brief sanitized summary |
| `normalized_action` | `object \| null` | Yes | Present only when `adapter_decision=mapped` |
| `rejection` | `object \| null` | Yes | Present only when `adapter_decision=rejected` |
| `safety_flags` | `object` | Yes | All flags default to `false`; guard sets `provider_call_allowed=true` |

**Critical invariant:** `safety_flags.provider_call_allowed` is **always `false`** in the adapter output. Only the guard pipeline (specifically `validate_gui_provider_policy()`) can set it to `true`.

---

## 7. Normalized Action Object

The `normalized_action` sub-object that represents a validated, safe GUI action:

```json
{
  "action_type": "record_observation",
  "action_tier": 0,
  "read_only": true,
  "uses_screenshot": false,
  "uses_clipboard": false,
  "uses_keyboard": false,
  "uses_mouse": false,
  "network_access": false,
  "input_paths": [],
  "output_paths": [],
  "expected_side_effects": "none",
  "requires_per_action_confirmation": false,
  "approval_id": null,
  "rollback_plan": "none",
  "stop_conditions": ["unexpected_window", "credential_field"]
}
```

| Field | Type | v1 Allowed | Blocked Values |
|-------|------|:---:|------|
| `action_type` | `string` | `"record_observation"` | Any other string (40 actions blocked) |
| `action_tier` | `integer` | `0` | `1`, `2`, `3`, `null`, mismatch with computed |
| `read_only` | `boolean` | `true` | `false` |
| `uses_screenshot` | `boolean` | `false` | `true` |
| `uses_clipboard` | `boolean` | `false` | `true` |
| `uses_keyboard` | `boolean` | `false` | `true` |
| `uses_mouse` | `boolean` | `false` | `true` |
| `network_access` | `boolean` | `false` | `true` |
| `input_paths` | `list[string]` | `[]` | Non-empty list |
| `output_paths` | `list[string]` | `[]` | Non-empty list |
| `expected_side_effects` | `string` | `"none"` | Any other string |
| `requires_per_action_confirmation` | `boolean` | `false` | `true` |
| `approval_id` | `string \| null` | `null` | Non-null (model cannot provide) |
| `rollback_plan` | `string` | `"none"` | Any other string |
| `stop_conditions` | `list[string]` | Non-empty | `null`, `[]` |

**Design note:** The `action_type` values in this schema use the taxonomy action names (e.g., `"record_observation"`) which map 1:1 to the `GuiAgentStepRequest.action` field via the existing route handler.

---

## 8. Rejection Result Schema

When the adapter rejects a model output, the envelope contains:

```json
{
  "ok": false,
  "status": "MODEL_ACTION_REJECTED",
  "source": "fine_tuned_gui_agent",
  "model_output_id": "model_out_002",
  "intent_type": "destructive_action",
  "adapter_decision": "rejected",
  "adapter_rejection_reason": "tier_3_action_blocked",
  "confidence": 0.91,
  "rationale_summary": "Model attempted to click Run.",
  "normalized_action": null,
  "rejection": {
    "reason": "tier_3_action_blocked",
    "blocked_terms": ["click_run"],
    "computed_tier": 3,
    "policy": "Tier 3 actions are blocked by default."
  },
  "safety_flags": {
    "provider_call_allowed": false,
    "desktop_touched": false,
    "screenshot_captured": false,
    "clipboard_accessed": false,
    "mouse_used": false,
    "keyboard_used": false
  }
}
```

### Rejection Reason Catalog (21 codes)

| Code | Trigger Condition |
|------|------|
| `unknown_intent` | Intent class not recognized |
| `ambiguous_intent` | Intent is vague ("continue", "fix it") |
| `multi_action_plan_blocked` | Model proposed multiple actions |
| `raw_coordinate_click_blocked` | Raw (x,y) coordinates detected |
| `provider_selection_blocked` | Model specified a provider name |
| `approval_override_blocked` | Model attempted to set `approved=true` |
| `screenshot_request_blocked` | Model requested screenshot capture |
| `clipboard_request_blocked` | Model requested clipboard access |
| `keyboard_mouse_blocked` | Model requested keyboard or mouse control |
| `file_path_blocked` | Model included file paths |
| `rawdata_path_blocked` | Model referenced rawdata paths |
| `derivatives_write_blocked` | Model requested derivatives writes |
| `network_request_blocked` | Model requested network access |
| `credential_request_blocked` | Model requested credential entry |
| `external_app_blocked` | Model requested external app launch |
| `shell_command_blocked` | Model proposed shell command |
| `tier_1_action_blocked` | Action classified as Tier 1 |
| `tier_2_action_blocked` | Action classified as Tier 2 |
| `tier_3_action_blocked` | Action classified as Tier 3 |
| `unknown_action_blocked` | Action not in 41-action taxonomy |
| `policy_override_attempt` | Model attempted to disable or bypass guard |

---

## 9. Adapter Decision Schema

```json
{
  "adapter_decision": "mapped",
  "adapter_rejection_reason": null,
  "clarification_prompt": null,
  "safe_to_submit_to_guard": true
}
```

| Decision | Meaning | `safe_to_submit_to_guard` | `normalized_action` |
|----------|------|:---:|:---:|
| `mapped` | Validated & normalized to v1-safe action | `true` | Present |
| `rejected` | Unsafe, unknown, or policy-violating | `false` | `null` |
| `needs_clarification` | Ambiguous benign; ask model/user | `false` | `null` |

**Rule:** Only `adapter_decision=mapped` with `safe_to_submit_to_guard=true` proceeds to the guard pipeline.

---

## 10. Audit Metadata Schema

Model-level audit fields recorded alongside the existing `GuiAuditRecord`:

```json
{
  "model_output_id": "model_out_001",
  "source": "fine_tuned_gui_agent",
  "adapter_version": "m10_v1",
  "adapter_decision": "mapped",
  "adapter_rejection_reason": null,
  "normalized_action_type": "record_observation",
  "guard_submission_allowed": true,
  "raw_model_output_stored": false,
  "rationale_summary_stored": true,
  "chain_of_thought_stored": false
}
```

**Prohibited in audit:**
- Raw chain-of-thought traces
- Raw screenshots or image data
- Raw clipboard contents
- Credentials, API keys, tokens
- Unredacted PHI or subject identifiers
- Raw model output JSON (only `model_output_id` is stored)

---

## 11. Mapping to Existing Guard Request

The normalized action object maps 1:1 to `GuiAgentStepRequest` fields:

| Normalized Action Field | `GuiAgentStepRequest` Field |
|------|------|
| `action_type` | `action` |
| `action_tier` | `action_tier` |
| `read_only` | `read_only` |
| `uses_screenshot` | `uses_screenshot` |
| `uses_clipboard` | `uses_clipboard` |
| `uses_keyboard` | `uses_keyboard` |
| `uses_mouse` | `uses_mouse` |
| `network_access` | `network_access` |
| `input_paths` | `input_paths` |
| `output_paths` | `output_paths` |
| `expected_side_effects` | `expected_side_effects` |
| `requires_per_action_confirmation` | `requires_per_action_confirmation` |
| `approval_id` | `approval_id` |
| `rollback_plan` | `rollback_plan` |
| `stop_conditions` | `stop_conditions` |

**Fields that MUST NOT come from the model:**
- `provider` — set by session, validated by provider gate
- `approved` — set by human operator, validated by session validator
- `session_id` — derived from the active GUI session
- Any session declaration fields (`target_application`, `screenshot_policy`, etc.)

---

## 12. Test Strategy for T003 Validator

The following test cases provide the basis for `M10-GUI-AGENT-T003` (model-output validator):

### Valid Input (1 test)
1. Safe observation intent → `record_observation` passes

### Rejection by Intent Class (6 tests)
2. Ambiguous intent rejected
3. Navigation intent rejected (Tier 1)
4. Interaction intent rejected (Tier 2/3)
5. Destructive intent rejected (Tier 3)
6. Injection intent rejected (policy violation)
7. Unknown intent class rejected

### Rejection by Action Type (7 tests)
8. `click_run` rejected (Tier 3)
9. `get_window_title` rejected (v1 restriction)
10. `focus_window` rejected (Tier 1)
11. `click_dry_run` rejected (Tier 2)
12. `save_file` rejected (Tier 3)
13. `read_clipboard` rejected (Tier 3)
14. Unknown action type rejected

### Rejection by Usage Flags (6 tests)
15. `uses_screenshot=true` rejected
16. `uses_clipboard=true` rejected
17. `uses_keyboard=true` rejected
18. `uses_mouse=true` rejected
19. `network_access=true` rejected
20. `read_only=false` rejected

### Rejection by Paths/Side Effects (4 tests)
21. `input_paths` non-empty rejected
22. `output_paths` non-empty rejected
23. `expected_side_effects != "none"` rejected
24. `requires_per_action_confirmation=true` rejected

### Rejection by Structural Violations (5 tests)
25. Multi-action plan rejected
26. Raw coordinates rejected
27. Provider selection in output rejected
28. Approval override in output rejected
29. Missing required fields rejected

### Schema Integrity (5 tests)
30. Valid rejection envelope is JSON-serializable
31. Rejection reason catalog is complete (21 codes)
32. Safety flags all false on rejection
33. `safe_to_submit_to_guard=true` only for mapped record_observation
34. Intent class constants match code taxonomy

### Total: **34 test benchmarks**

---

## 13. Future Compatibility Notes

| Aspect | v1 Status | Future Direction |
|--------|:---:|------|
| Action count | 1 of 41 | Expand to other Tier 0 actions after dedicated contracts |
| Provider | Mock only | Real provider requires dedicated guard contract |
| Screenshots | Blocked | Requires redaction mechanism + persist_redacted policy |
| Clipboard | Blocked | Requires per-action confirmation |
| Tier 1 navigation | Blocked | Requires action-plan approval |
| Tier 2 interaction | Blocked | Requires per-action confirmation |
| Tier 3 actions | Permanently blocked | — |
| Multi-action plans | Rejected | Requires action-plan approval + step sequencing |
| `confidence` field | Not used for gating | May inform clarification prompts in future |
| `rationale_summary` | Logged for audit | May be surfaced in HITL UI in future |

---

## 14. References

| Document | Content |
|----------|---------|
| `docs/FINE_TUNED_GUI_AGENT_ACTION_ADAPTER_DESIGN.md` | Adapter architecture, model output classes |
| `docs/M9_GUI_AGENT_API_GUARD_CLOSEOUT.md` | Guard phase closeout, guard layer summary |
| `docs/GUI_AGENT_API_GUARD_DESIGN.md` | 14-layer guard pipeline design |
| `docs/GUI_ACTION_TAXONOMY_AND_SANDBOX_CONTRACT.md` | Original taxonomy design |
| `src/backend/app/runtime/gui_agent_guard.py` | Canonical action taxonomy constants |
| `src/backend/app/api/models.py` | `GuiAgentStepRequest` model |
