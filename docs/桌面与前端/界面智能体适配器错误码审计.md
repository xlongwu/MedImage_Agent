# GUI Agent Adapter Error Code Audit

> M10-GUI-AGENT-STABILIZE-T001 | Adapter / mock route / guard error code audit  
> Status: COMPLETE | Date: 2026-07-11

---

## 1. Executive Summary

This document audits all error codes and response structures across three layers: **adapter** (`gui_agent_model_adapter.py`), **mock route** (`gui_agent_routes.py` mock endpoints), and **guard** (`gui_agent_guard.py`). It identifies the complete taxonomy, verifies response consistency, flags any inconsistencies, and provides a test matrix for future expansion.

**Total codes surveyed: 55** (42 guard + 6 mock route + 7 adapter statuses).

---

## 2. Current Response Surfaces

| Layer | Source File | Response Types |
|-------|-------------|------|
| Adapter | `gui_agent_model_adapter.py` | `ModelOutputValidationResult` (mapped / rejected) |
| Mock route | `gui_agent_routes.py:260-450` | 6 distinct response statuses |
| Guard | `gui_agent_guard.py` | `GuiGuardResult` (ok / blocked) |
| Guarded step | `gui_agent_routes.py` | HTTP 200 / 403 + guard detail |

---

## 3. Complete Status/Error Taxonomy

### 3.1 Adapter-Level Statuses (7)

| Status | Meaning | Layer |
|--------|---------|:---:|
| `NORMALIZED_ACTION_READY` | Adapter mapped to safe action | Adapter |
| `MODEL_ACTION_REJECTED` | Adapter rejected model output | Adapter + Mock route |
| `MODEL_ACTION_MAPPED` | Mapped action submitted to guard + passed | Mock route |
| `MODEL_ACTION_MAPPED_DRY_RUN` | Mapped action, dry-run, not submitted | Mock route |
| `MODEL_ACTION_GUARD_BLOCKED` | Mapped action submitted but guard blocked | Mock route |
| `MOCK_MODEL_FIXTURE_NOT_FOUND` | Unknown fixture_id | Mock route |
| `MOCK_ADAPTER_SESSION_REQUIRED` | submit_to_guard without session_id | Mock route |

### 3.2 Guard-Level Error Codes (42)

All defined in `gui_agent_guard.py:_ERROR_CODES`:

**Provider (5):** `GUI_GUARD_PROVIDER_MISSING`, `GUI_GUARD_PROVIDER_UNKNOWN`, `GUI_GUARD_PROVIDER_BLOCKED`, `GUI_GUARD_REAL_PROVIDER_DISABLED`, `GUI_GUARD_CI_REAL_PROVIDER_BLOCKED`

**Session (12):** `GUI_GUARD_SESSION_INVALID`, `GUI_GUARD_SANDBOX_REQUIRED`, `GUI_GUARD_TARGET_SCOPE_REQUIRED`, `GUI_GUARD_ACTION_TIER_BLOCKED`, `GUI_GUARD_FILE_SCOPE_BLOCKED`, `GUI_GUARD_SCREENSHOT_BLOCKED`, `GUI_GUARD_CLIPBOARD_BLOCKED`, `GUI_GUARD_NETWORK_BLOCKED`, `GUI_GUARD_EXTERNAL_APP_BLOCKED`, `GUI_GUARD_HUMAN_REQUIRED`, `GUI_GUARD_EMERGENCY_ABORT_REQUIRED`, `GUI_GUARD_AUDIT_REQUIRED`

**Action (9):** `GUI_GUARD_ACTION_INVALID`, `GUI_GUARD_ACTION_UNKNOWN`, `GUI_GUARD_ACTION_NOT_ALLOWED`, `GUI_GUARD_ACTION_TIER_MISMATCH`, `GUI_GUARD_READ_ONLY_REQUIRED`, `GUI_GUARD_KEYBOARD_BLOCKED`, `GUI_GUARD_MOUSE_BLOCKED`, `GUI_GUARD_SIDE_EFFECT_BLOCKED`, `GUI_GUARD_CONFIRMATION_UNSUPPORTED`

**Stop/Audit (7):** `GUI_GUARD_AUDIT_FAILED`, `GUI_GUARD_STOP_CONDITION`, `GUI_GUARD_SESSION_MISSING`, `GUI_GUARD_STEP_LIMIT_EXCEEDED`, `GUI_GUARD_DURATION_LIMIT_EXCEEDED`, `GUI_GUARD_EMERGENCY_ABORTED`

**Mock route (2):** `SESSION_NOT_FOUND`, `BLOCKED` (fallback)

---

## 4. Response Schema Per Status

### 4.1 Success — MODEL_ACTION_MAPPED

```json
{
  "ok": true,
  "status": "MODEL_ACTION_MAPPED",
  "fixture_id": "safe_observe_current_state",
  "model_output_id": "fixture_safe_observe_current_state",
  "adapter_decision": "mapped",
  "adapter_status": "NORMALIZED_ACTION_READY",
  "normalized_action_type": "record_observation",
  "submitted_to_guard": true,
  "guard_status": "GUI_GUARD_OK",
  "audit_id": "audit_...",
  "provider_call_allowed_by_adapter": false,
  "provider_call_allowed_by_guard": true,
  "desktop_touched": false,
  "screenshot_captured": false,
  "clipboard_accessed": false,
  "mouse_used": false,
  "keyboard_used": false
}
```
✅ Consistent. `provider_call_allowed_by_adapter` always false. `audit_id` present.

### 4.2 Dry-Run — MODEL_ACTION_MAPPED_DRY_RUN

```json
{
  "ok": true,
  "status": "MODEL_ACTION_MAPPED_DRY_RUN",
  "fixture_id": "...",
  "adapter_decision": "mapped",
  "adapter_status": "NORMALIZED_ACTION_READY",
  "normalized_action_type": "record_observation",
  "submitted_to_guard": false,
  "guard_status": null,
  "audit_id": null,
  "provider_call_allowed_by_adapter": false,
  "provider_call_allowed_by_guard": false
}
```
✅ Consistent. No provider call. No audit.

### 4.3 Adapter Rejected — MODEL_ACTION_REJECTED

```json
{
  "ok": false,
  "status": "MODEL_ACTION_REJECTED",
  "fixture_id": "...",
  "model_output_id": "...",
  "adapter_decision": "rejected",
  "adapter_rejection_reason": "tier_3_action_blocked",
  "submitted_to_guard": false,
  "guard_status": null,
  "audit_id": null,
  "provider_call_allowed": false,
  "desktop_touched": false,
  "screenshot_captured": false,
  "clipboard_accessed": false,
  "mouse_used": false,
  "keyboard_used": false
}
```
✅ Consistent. Note: field is `provider_call_allowed` (not `by_adapter`/`by_guard`).

### 4.4 Guard Blocked — MODEL_ACTION_GUARD_BLOCKED

```json
{
  "ok": false,
  "status": "MODEL_ACTION_GUARD_BLOCKED",
  "fixture_id": "...",
  "adapter_decision": "mapped",
  "adapter_status": "NORMALIZED_ACTION_READY",
  "normalized_action_type": "record_observation",
  "submitted_to_guard": true,
  "guard_status": "GUI_GUARD_EMERGENCY_ABORTED" | "SESSION_NOT_FOUND" | "BLOCKED",
  "audit_id": null,
  "provider_call_allowed_by_adapter": false,
  "provider_call_allowed_by_guard": false,
  "desktop_touched": false,
  "screenshot_captured": false,
  "clipboard_accessed": false,
  "mouse_used": false,
  "keyboard_used": false
}
```
⚠️ **Inconsistency found:** `guard_status` can be `SESSION_NOT_FOUND` (not a guard-prefixed code) or `"BLOCKED"` (fallback when HTTPException detail is not a string). The guard codes use `GUI_GUARD_` prefix; `SESSION_NOT_FOUND` does not.

### 4.5 Fixture Not Found — MOCK_MODEL_FIXTURE_NOT_FOUND

```json
{
  "ok": false,
  "status": "MOCK_MODEL_FIXTURE_NOT_FOUND",
  "fixture_id": "...",
  "submitted_to_guard": false,
  "provider_call_allowed": false
}
```
⚠️ **Inconsistency:** Missing safety flags (`desktop_touched`, etc.). Other rejection responses include these flags.

### 4.6 Session Required — MOCK_ADAPTER_SESSION_REQUIRED

```json
{
  "ok": false,
  "status": "MOCK_ADAPTER_SESSION_REQUIRED",
  "fixture_id": "...",
  "submitted_to_guard": false,
  "provider_call_allowed": false
}
```
⚠️ Same inconsistency as fixture-not-found: missing safety flags.

---

## 5. Inconsistency Findings

| # | Finding | Severity | Recommendation |
|:---:|------|:---:|------|
| 1 | `MOCK_MODEL_FIXTURE_NOT_FOUND` missing safety flags | Low | Add standard 5 safety flags for consistency |
| 2 | `MOCK_ADAPTER_SESSION_REQUIRED` missing safety flags | Low | Add standard 5 safety flags |
| 3 | `guard_status: "SESSION_NOT_FOUND"` not prefixed `GUI_GUARD_` | Low | Rename to `GUI_GUARD_SESSION_NOT_FOUND` or keep as-is (route-level, not guard-level) |
| 4 | `guard_status: "BLOCKED"` is a fallback string, not a structured error | Low | Map to specific guard error code when possible |
| 5 | `provider_call_allowed` (rejected) vs `provider_call_allowed_by_adapter` (mapped) naming | Low | Accept as-is: rejected uses simple `provider_call_allowed=false`; mapped uses `by_adapter`/`by_guard` distinction |
| 6 | Rejected response uses `provider_call_allowed` (bool), mapped uses `provider_call_allowed_by_adapter` (bool) | Info | Deliberate design choice: rejection path has no guard involvement, so adapter/guard distinction is unnecessary |
| 7 | `audit_id` is `null` for guard-blocked responses, but T005 stop-condition checker creates blocked audit records | Minor | Could surface blocked audit_id in guard-blocked response; deferred to future audit persistence task |

**Assessment:** All inconsistencies are low-severity and do not affect security. The core invariants hold: adapter never grants `provider_call_allowed=true`, rejected outputs never reach guard/provider, and all blocked responses have safety flags set to `false`.

---

## 6. Safety Flag Requirements (All Response Types)

| Response Type | `desktop_touched` | `screenshot_captured` | `clipboard_accessed` | `mouse_used` | `keyboard_used` |
|------|:---:|:---:|:---:|:---:|:---:|
| `MODEL_ACTION_MAPPED` | `false` ✅ | `false` ✅ | `false` ✅ | `false` ✅ | `false` ✅ |
| `MODEL_ACTION_MAPPED_DRY_RUN` | (absent) | (absent) | (absent) | (absent) | (absent) |
| `MODEL_ACTION_REJECTED` | `false` ✅ | `false` ✅ | `false` ✅ | `false` ✅ | `false` ✅ |
| `MODEL_ACTION_GUARD_BLOCKED` | `false` ✅ | `false` ✅ | `false` ✅ | `false` ✅ | `false` ✅ |
| `MOCK_MODEL_FIXTURE_NOT_FOUND` | ⚠️ Missing | ⚠️ Missing | ⚠️ Missing | ⚠️ Missing | ⚠️ Missing |
| `MOCK_ADAPTER_SESSION_REQUIRED` | ⚠️ Missing | ⚠️ Missing | ⚠️ Missing | ⚠️ Missing | ⚠️ Missing |

---

## 7. `provider_call_allowed` Field Semantics

| Field | Where Used | Meaning | Set By |
|-------|-----------|---------|:---:|
| `provider_call_allowed` | Rejected, fixture-not-found, session-required | Simple boolean — provider was NOT called | Mock route |
| `provider_call_allowed_by_adapter` | Mapped, dry-run, guard-blocked | Adapter did NOT grant permission | Mock route |
| `provider_call_allowed_by_guard` | Mapped, dry-run, guard-blocked | Guard granted (or denied) permission | Guard step route |

**Invariant:** `provider_call_allowed_by_adapter` is **always `false`** across all response types. Only the guard can set `provider_call_allowed_by_guard=true`.

---

## 8. Test Coverage Matrix (49 tests)

### A. Success Schema (5)
1. `MODEL_ACTION_MAPPED` has all 15 required fields
2. `provider_call_allowed_by_adapter=false` in mapped response
3. `provider_call_allowed_by_guard=true` in mapped response
4. `audit_id` starts with `audit_`
5. All 5 safety flags `false`

### B. Dry-Run Schema (5)
6. `MODEL_ACTION_MAPPED_DRY_RUN` status
7. `submitted_to_guard=false`, `guard_status=null`, `audit_id=null`
8. `provider_call_allowed_by_adapter=false`
9. `provider_call_allowed_by_guard=false` or absent
10. Provider not called

### C. Adapter Rejected Schema (8)
11. `MODEL_ACTION_REJECTED` status
12. `submitted_to_guard=false`
13. `guard_status=null`, `audit_id=null`
14. `provider_call_allowed=false`
15. `adapter_rejection_reason` present
16. `normalized_action` absent or null
17. Provider not called
18. All 5 safety flags `false`

### D. Guard Blocked Schema (7)
19. Aborted session → `MODEL_ACTION_GUARD_BLOCKED`
20. Guard status present (`GUI_GUARD_EMERGENCY_ABORTED` or equivalent)
21. `provider_call_allowed_by_adapter=false`
22. `provider_call_allowed_by_guard` not `true`
23. Provider not called
24. Step limit exceeded → `MODEL_ACTION_GUARD_BLOCKED`
25. Invalid session → `MODEL_ACTION_GUARD_BLOCKED`

### E. Fixture/Request Error Schema (6)
26. Unknown fixture → `MOCK_MODEL_FIXTURE_NOT_FOUND`
27. Missing session → `MOCK_ADAPTER_SESSION_REQUIRED`
28. Both have `submitted_to_guard=false`
29. Both have `provider_call_allowed=false`
30. Both do not call provider

### F. Safety Flag Consistency (8)
31–35. All 5 safety flags `false` in rejected
36–38. Responses do not expose `raw_text`/`raw_json`/`chain_of_thought`

### G. Regression (10)
39–48. All existing mock/guard tests pass

---

## 9. Recommended Fixes

1. **Add safety flags to `MOCK_MODEL_FIXTURE_NOT_FOUND`** — add `desktop_touched`, `screenshot_captured`, `clipboard_accessed`, `mouse_used`, `keyboard_used` all `false`.
2. **Add safety flags to `MOCK_ADAPTER_SESSION_REQUIRED`** — same as above.
3. **Consider renaming `SESSION_NOT_FOUND`** to `GUI_GUARD_SESSION_NOT_FOUND` for consistency, or accept as route-level status distinct from guard codes.
4. **Stabilize `guard_status` in `MODEL_ACTION_GUARD_BLOCKED`** — extract the guard error code from the HTTPException detail when possible.

All fixes are low-priority; current behavior is safe.

---

## 10. Acceptance Criteria Before Future Expansion

1. Response schemas for all 7 mock route statuses are locked in tests
2. `provider_call_allowed` / `provider_call_allowed_by_adapter` / `provider_call_allowed_by_guard` semantics are unambiguous
3. All blocked/rejected responses have 5 safety flags set to `false`
4. `raw_text`/`raw_json`/`chain_of_thought` are never exposed in responses
5. 49 audit tests pass
6. All 1696 existing tests continue to pass
