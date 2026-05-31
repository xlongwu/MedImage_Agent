# GUI Manual Smoke Guide

> M9-GUI-T006 | Manual-only GUI smoke verification guide  
> Status: GUIDE | Date: 2026-07-11  
> Depends on: M9-GUI-T001 (threat model), M9-GUI-T002 (approval + HITL), M9-GUI-T003 (taxonomy + contract), M9-GUI-T004 (blocklist tests), M9-GUI-T005 (observation contract)

---

## ⚠️ SAFETY WARNING — READ BEFORE PROCEEDING

```
THIS SMOKE GUIDE IS MANUAL-ONLY.
DO NOT RUN REAL GUI AUTOMATION.
DO NOT ENABLE PyWinAutoGuiProvider.
DO NOT INTERACT WITH REAL MATLAB / SPM / DPABI GUI THROUGH THE AGENT.
DO NOT CAPTURE SCREENSHOTS CONTAINING PHI, CREDENTIALS, TOKENS, OR RAWDATA PATHS.
DO NOT READ OR WRITE CLIPBOARD.
DO NOT CLICK RUN / SUBMIT / EXECUTE.
DO NOT USE THIS GUIDE TO BYPASS REVIEWED EXECUTION.
```

---

## 1. Scope and Non-Goals

### Scope

- Provide a **manual-only** checklist for verifying the current GUI/manual Agent security posture.
- Confirm that reviewed execution correctly blocks all GUI/manual nodes.
- Confirm that `MockGuiProvider` is safe by default.
- Confirm that `PyWinAutoGuiProvider` is NOT enabled.
- Confirm that `/api/gui-agent/*` bypass gap is documented and remains known.
- Confirm that all M9 design contracts and blocklist tests are in place.
- Provide failure diagnostics and cleanup instructions.

### Non-Goals

- Implementing GUI automation or calling any GUI automation library.
- Enabling real desktop control (pywinauto, pyautogui, pynput, selenium, playwright).
- Capturing real screenshots, reading clipboard, controlling mouse/keyboard.
- Modifying `gui_agent.py`, `gui_agent_routes.py`, `approval_gate.py`, `plan_adapter.py`, `execute_reviewed_routes.py`, or any production code.
- Opening the reviewed execution allowlist for any GUI/manual node.
- Fixing the `/api/gui-agent/*` bypass gap.
- Running automated GUI smoke — **this guide is a checklist for humans, not executable code.**

---

## 2. Preconditions

### 2.1 Environment

- Backend environment available (Python 3.11+).
- All project dependencies installed (`pip install -r requirements.txt`).
- Test suite runnable locally.
- Frontend build runnable (`cd src/frontend && npm install`).

### 2.2 Required Config State

- `MEDIMAGE_GUI_AGENT_REAL_PROVIDER` must NOT be set to `1`.
- `MEDIMAGE_GUI_AGENT_PROVIDER` must NOT be set to `pywinauto`.
- No `MEDIMAGE_GUI_AGENT_BACKEND` override needed (default mock is safe).
- No GUI/manual node should be added to the reviewed execution allowlist.

**Verify with:**

```bash
# These should be empty (no pywinauto override)
echo $MEDIMAGE_GUI_AGENT_REAL_PROVIDER
echo $MEDIMAGE_GUI_AGENT_PROVIDER
echo $MEDIMAGE_GUI_AGENT_BACKEND
```

### 2.3 Required Documents

| Document | Purpose |
|----------|---------|
| `docs/GUI_MANUAL_AGENT_THREAT_MODEL.md` | Threat model and inventory |
| `docs/GUI_MANUAL_APPROVAL_HITL_DESIGN.md` | Approval + HITL design |
| `docs/GUI_ACTION_TAXONOMY_AND_SANDBOX_CONTRACT.md` | Action taxonomy + sandbox contract |
| `docs/GUI_READ_ONLY_OBSERVATION_CONTRACT.md` | Read-only observation contract |
| `docs/GUI_MANUAL_SMOKE_GUIDE.md` | This guide |

### 2.4 Required Test Files

| Test File | What It Covers |
|-----------|---------------|
| `tests/unit/test_gui_reviewed_execution_blocklist.py` | Full GUI blocklist (38 tests) |
| `tests/unit/test_plan_adapter.py` | Plan adapter policy (60+ tests) |
| `tests/unit/test_approval_gate.py` | Approval gate (28 tests) |
| `tests/unit/test_execute_reviewed_api.py` | Execute-reviewed API (100+ tests) |
| `tests/unit/test_tool_catalog.py` | Tool catalog metadata (13 tests) |

---

## 3. Smoke Procedure

### Step 1 — Run the Full GUI Blocklist Test Suite

```bash
pytest tests/unit/test_gui_reviewed_execution_blocklist.py -v
```

**Expected:** 38 passed.

**If not 38/38:** Check failure output against the test names listed in Section 4.1.

---

### Step 2 — Run the Plan Adapter Tests

```bash
pytest tests/unit/test_plan_adapter.py -v
```

**Expected:** All 60+ tests pass.

**Focus:** Tests with `gui` in their name (`test_unknown_node_blocked` covers `nonexistent_gui_xyz`).

---

### Step 3 — Run the Approval Gate Tests

```bash
pytest tests/unit/test_approval_gate.py -v
```

**Expected:** All 28 tests pass.

**Focus:** Tests that verify manual_required blocking (`test_manual_required_blocked`, `test_manual_required_still_blocks`).

---

### Step 4 — Run the Execute-Reviewed API Tests

```bash
pytest tests/unit/test_execute_reviewed_api.py -v
```

**Expected:** All 100+ tests pass.

**Focus:** Test `test_m5t016_manual_required_no_executor` — verifies `executor_called=false` for GUI node.

---

### Step 5 — Run the Tool Catalog Tests

```bash
pytest tests/unit/test_tool_catalog.py -v
```

**Expected:** All 13 tests pass.

**Focus:** Tests verifying fallback metadata correctness.

---

### Step 6 — Run the Full Test Suite

```bash
pytest --tb=short
```

**Expected:** 1192+ passed, 4 skipped (CuPy unavailable).

---

### Step 7 — Build the Frontend

```bash
npm --prefix src/frontend run build
```

**Expected:** Build succeeds with no errors.

---

## 4. Detailed Verification Items

### 4.1 Reviewed Execution GUI Blocklist

**Test file:** `tests/unit/test_gui_reviewed_execution_blocklist.py`

| # | Test Name | What It Verifies |
|:---:|-----------|-----------------|
| 1 | `test_gui_prefixed_node_blocked_unknown` | `gui_*` prefix → `blocked_unknown_nodes` |
| 2 | `test_gui_manual_acpc_blocked_unknown` | `gui_acpc_manual` → blocked |
| 3 | `test_gui_node_not_allowed_python` | GUI node NOT in `allowed_python_nodes` |
| 4 | `test_multiple_gui_nodes_blocked` | Multiple GUI nodes all blocked |
| 5 | `test_gui_node_not_total_allowed` | GUI node excluded from total |
| 6 | `test_backend_gui_agent_blocked` | `backend=gui-agent` → blocked |
| 7 | `test_backend_gui_blocked` | `backend=gui` → blocked |
| 8 | `test_backend_manual_blocked` | `backend=manual` → blocked |
| 9 | `test_backend_desktop_blocked` | `backend=desktop` → blocked |
| 10 | `test_backend_browser_blocked` | `backend=browser` → blocked |
| 11 | `test_mock_provider_not_allowed` | `gui_mock_provider` → blocked |
| 12 | `test_pywinauto_provider_blocked` | `gui_pywinauto_provider` → blocked |

**Manual verification:** If any of these fail, the blocklist is compromised. Do NOT proceed to M9-GUI-CLOSEOUT.

---

### 4.2 Tool Catalog Fallback

**Code reference:** `src/backend/app/runtime/tool_catalog.py:505-509`

```python
elif node_id.startswith("gui_"):
    requires_approval = True
    manual_required = True
    risk_level = "high"
    tags = ["gui"]
```

**Related tests:**

| Test | What It Verifies |
|------|-----------------|
| `test_gui_catalog_fallback_contract` | `manual_required=True`, `risk_level="high"`, `tags=["gui"]`, `requires_approval=True` |
| `test_gui_fallback_manual_required_true` | `manual_required` is `True` |
| `test_gui_fallback_requires_approval` | `requires_approval` is `True` |
| `test_gui_fallback_has_required_fields` | All `ToolCatalogItem` fields present |
| `test_non_gui_fallback_not_affected` | Non-`gui_*` prefix fallback unchanged |

**Manual verification:** Open `tool_catalog.py` and confirm the `gui_` prefix branch in `_fallback()`. Confirm `manual_required=True`, `risk_level="high"`, `tags=["gui"]`, `requires_approval=True`.

---

### 4.3 Approval Gate

**Code reference:** `src/backend/app/planner/approval_gate.py:276-284`

```python
# ── 12. manual_required nodes block execution (MVP) ──
if manual_required_nodes:
    errors.append(ApprovalGateIssue(
        "MANUAL_REQUIRED_NODE",
        f"Manual/GUI nodes not yet supported: {', '.join(manual_required_nodes)}",
    ))
    return ApprovalGateResult(
        ok=False, execution_allowed=False, ...
    )
```

**Related tests:**

| Test | What It Verifies |
|------|-----------------|
| `test_gui_manual_required_blocks_gate` | Non-empty `manual_required_nodes` → `MANUAL_REQUIRED_NODE` |
| `test_gui_wildcard_approval_blocked` | `approved_nodes=["*"]` cannot bypass |
| `test_gui_backend_only_rejected` | `approved_backends=["gui"]` alone insufficient |
| `test_gui_approved_true_boolean_alone_blocked` | `approved=true` boolean alone blocked |
| `test_gui_multiple_manual_required_blocked` | Multiple manual_required nodes all blocked |
| `test_gui_spm_approval_still_works` | SPM approval behavior unchanged |
| `test_gui_gpu_approval_still_works` | GPU approval behavior unchanged |
| `test_gui_dpabi_approval_still_blocked` | DPABI execution still blocked |

**Manual verification:** Confirm that no combination of `approved_nodes=["*"]`, `approved_backends=["gui"]`, or `approved=true` can bypass the `manual_required_nodes` gate.

---

### 4.4 Execute-Reviewed

**Related tests:**

| Test | What It Verifies |
|------|-----------------|
| `test_gui_dry_run_policy_blocked` | Dry-run returns `EXECUTION_POLICY_BLOCKED` |
| `test_gui_preflight_executor_not_called` | Preflight: `executor_called=false` |
| `test_gui_unknown_node_no_execution_submitted` | Status != `EXECUTION_SUBMITTED` |
| `test_gui_agent_backend_no_execution` | `backend=gui-agent` → no execution |
| `test_gui_manual_backend_no_execution` | `backend=manual` → no execution |
| `test_gui_desktop_backend_no_execution` | `backend=desktop` → no execution |
| `test_gui_browser_backend_no_execution` | `backend=browser` → no execution |
| `test_gui_wildcard_approval_no_executor` | Wildcard approval → `executor_called=false` |
| `test_gui_backends_only_no_executor` | Backend-only approval → `executor_called=false` |
| `test_gui_spm_realign_sandbox_still_works` | SPM sandbox regression |
| `test_gui_dpabi_metadata_still_works` | DPABI metadata regression |
| `test_gui_gpu_contract_still_works` | GPU contract regression |

**Key invariant:** For every GUI/manual node scenario, `executor_called=false` and status is NEVER `EXECUTION_SUBMITTED`.

---

### 4.5 MockGuiProvider Manual Inspection

**Code reference:** `src/backend/app/runtime/gui_agent.py:28-46`

**Checklist:**

- [ ] Open `src/backend/app/runtime/gui_agent.py`.
- [ ] Locate `class MockGuiProvider` (line 28).
- [ ] Confirm `provider_name = "mock"`.
- [ ] Inspect `perform_step()` — confirms it returns `executed=False`, `provider_status="MOCK_RECORDED"`, with note: "Mock provider recorded the intended GUI action without controlling the desktop."
- [ ] Inspect `capture_screenshot()` — confirms it writes placeholder text, NOT real pixels.
- [ ] Confirm no `import pywinauto` in MockGuiProvider.
- [ ] Confirm no real `click`, `type_keys`, `menu_select`, or `capture_as_image` in MockGuiProvider.

**Expected:** MockGuiProvider cannot control the desktop, cannot capture real screenshots, cannot interact with the clipboard. It is safe for CI and contract tests.

---

### 4.6 PyWinAuto Provider Must Remain Disabled

**Code reference:** `src/backend/app/runtime/gui_agent.py:49-91`

**Checklist:**

- [ ] Open `src/backend/app/runtime/gui_agent.py`.
- [ ] Locate `class PyWinAutoGuiProvider` (line 49).
- [ ] Confirm `provider_name = "pywinauto"`.
- [ ] **Do NOT call** any method on this class.
- [ ] Confirm `_desktop()` imports `pywinauto.Desktop` — real Windows desktop access.
- [ ] Confirm `perform_step()` can `click_input()`, `type_keys()`, `menu_select()`.
- [ ] Confirm `capture_screenshot()` writes real PNG pixels via `capture_as_image()`.
- [ ] Confirm no environment variable `MEDIMAGE_GUI_AGENT_REAL_PROVIDER=1` is set.
- [ ] Confirm no smoke step, no test fixture, no configuration triggers PyWinAuto.

**Expected:** PyWinAuto provider remains **inspected but NOT called.** No real desktop interaction occurs.

---

### 4.7 `/api/gui-agent/*` Bypass Awareness

**Known gap:** The `/api/gui-agent/*` API surface operates outside the reviewed execution pipeline.

**Checklist:**

- [ ] Open `src/backend/app/api/gui_agent_routes.py`.
- [ ] Confirm 5 endpoints exist: `GET/POST /api/gui-agent/sessions`, `POST .../step`, `GET .../screenshot`, `POST .../abort`.
- [ ] Open `src/backend/app/main.py` line 18.
- [ ] Confirm `gui_agent_router` is registered: `app.include_router(gui_agent_router)`.
- [ ] Confirm these routes do NOT call `plan_validator`, `approval_gate`, `plan_adapter`, or `execute_reviewed`.
- [ ] Open `src/backend/app/api/execute_reviewed_routes.py` — confirm it has no reference to `gui_agent`.
- [ ] Confirm that reviewed execution blocklist tests in `test_gui_reviewed_execution_blocklist.py` verify reviewed-execution-side blocking but do NOT gate `/api/gui-agent/*`.

**Test confirmation:**

```bash
pytest tests/unit/test_gui_reviewed_execution_blocklist.py::test_gui_bypass_gap_still_exists -v
```

**Expected:** Test passes, confirming the bypass is documented and known. T006 does NOT fix this bypass.

**M9-GUI-T006 does not fix this. Future task (M9-GUI-GUARD) must add guard before provider call.**

---

### 4.8 Read-Only Observation Contract Check

**Document:** `docs/GUI_READ_ONLY_OBSERVATION_CONTRACT.md`

**Checklist:**

- [ ] Confirm the document exists.
- [ ] Confirm Tier 0 actions are listed (7 actions: `record_observation`, `get_window_title`, `list_windows`, `observe_visible_ui_state`, `screenshot_ephemeral`, `get_control_text`, `get_menu_state`).
- [ ] Confirm Tier 1 / 2 / 3 actions remain blocked for read-only observation.
- [ ] Confirm real provider observation is documented as design-only (not enabled).
- [ ] Confirm `screenshot_policy` defaults to `disabled`.
- [ ] Confirm `clipboard_policy` defaults to `disabled`.
- [ ] Confirm session declaration schema requires `gui_sandbox_mode=true`, `provider=mock`, `allowed_action_tiers=[0]`.
- [ ] Confirm action declaration schema requires `action_tier=0`, `read_only=true`, all usage flags `false`.

**Expected:** Read-only observation contract is in place as a design document. No code implements it yet. No real desktop observation is enabled.

---

## 5. Regression Assurance

### 5.1 SPM Allowlist

```bash
pytest tests/unit/test_gui_reviewed_execution_blocklist.py -k spm -v
```

**Expected:** `test_gui_spm_realign_sandbox_still_works` and related tests pass. SPM sandbox-gated realign still executes correctly.

### 5.2 DPABI Allowlist

```bash
pytest tests/unit/test_gui_reviewed_execution_blocklist.py -k dpabi -v
```

**Expected:** `test_gui_dpabi_metadata_still_works` passes. DPABI metadata nodes still correctly classified.

### 5.3 GPU Allowlist

```bash
pytest tests/unit/test_gui_reviewed_execution_blocklist.py -k gpu -v
```

**Expected:** `test_gui_gpu_contract_still_works` passes. GPU contract nodes still correctly classified.

---

## 6. Expected Outcomes

| Item | Expected Result |
|------|----------------|
| `test_gui_reviewed_execution_blocklist.py` | 38/38 passed |
| `test_plan_adapter.py` | All passed |
| `test_approval_gate.py` | All passed |
| `test_execute_reviewed_api.py` | All passed |
| `test_tool_catalog.py` | All passed |
| Full pytest suite | 1192+ passed, 4 skipped |
| Frontend build | Passed |
| GUI nodes in reviewed execution allowlist | **0** (none) |
| GUI nodes reaching `EXECUTION_SUBMITTED` | **0** (none) |
| `executor_called=true` for GUI node | **Never** |
| MockGuiProvider real desktop control | **None** |
| PyWinAuto provider enabled | **No** |
| Real screenshots captured | **None** |
| Clipboard accessed | **No** |
| Rawdata modified | **No** |
| Derivatives modified by GUI agent | **No** |

---

## 7. Failure Diagnostics

### If a GUI/manual node reaches `EXECUTION_SUBMITTED`

```
CRITICAL FAILURE. DO NOT PROCEED.

Investigate:
  1. plan_adapter.classify_plan_nodes() — is the node classified as blocked?
  2. execute_reviewed._is_policy_blocked() — is the policy gate working?
  3. execute_reviewed._check_safe_allowlist() — is the allowlist filter active?

Roll back any code changes that may have opened the allowlist.
```

### If `executor_called=true` for a GUI/manual request

```
CRITICAL FAILURE. DO NOT PROCEED.

Investigate:
  1. execute_reviewed.api_execute_reviewed() — is the preflight path skipping gates?
  2. Has MEDIMAGE_ENABLE_REVIEWED_EXECUTION been set unintentionally?

Roll back. Do not open the allowlist.
```

### If PyWinAuto provider runs during smoke

```
CRITICAL FAILURE. STOP IMMEDIATELY.

Check:
  1. Is MEDIMAGE_GUI_AGENT_REAL_PROVIDER set to 1? Unset it.
  2. Is any test calling PyWinAutoGuiProvider directly outside test_gui_agent_runtime.py?
  3. Is any script importing pywinauto?

The PyWinAuto provider must never run outside of its dedicated sandboxed test file
(test_gui_agent_runtime.py), and even then only with approved=false.
```

### If a screenshot file contains real pixels

```
CRITICAL FAILURE. DELETE ARTIFACT IMMEDIATELY.

Check:
  1. What provider wrote the screenshot? If PyWinAuto, investigate routing.
  2. What path was used? If outside outputs/work/gui_agent/smoke/, investigate.
  3. Does the screenshot contain PHI, credentials, or rawdata paths? If yes, secure-delete.

Delete the file. Do not commit. Do not archive.
```

### If clipboard is read or written

```
CRITICAL FAILURE. STOP AND INVESTIGATE.

Check:
  1. Is pyperclip, clipboard, or pywinauto.clipboard being imported anywhere?
  2. Is any test or script accessing the system clipboard?

Clipboard access is blocked by all current M9 contracts. Any access is unauthorized.
```

### If SPM / DPABI / GPU regression tests fail

```
REGRESSION FAILURE. DO NOT PROCEED TO NEXT M9 TASK.

Investigate:
  1. Has a code change inadvertently affected plan_adapter.classify_plan_nodes()?
  2. Has a new allowlist entry broken the existing classification?
  3. Has an environment change affected test fixtures?

Do not proceed to M9-GUI-CLOSEOUT until regression is resolved.
```

### If `/api/gui-agent/*` bypass appears fixed accidentally

```
UNEXPECTED BEHAVIOR CHANGE.

Check:
  1. Has gui_agent_routes.py changed? Has main.py router registration changed?
  2. Has any middleware been added that gates gui_agent routes?
  3. Were changes reviewed and approved?

If the bypass was fixed intentionally, update M9 documents to reflect the new state.
If the change is unreviewed, revert.
```

---

## 8. Cleanup

### 8.1 Remove Temporary Smoke Outputs

```bash
# Only run if these directories exist and contain smoke artifacts
rm -rf outputs/work/gui_agent/smoke/ 2>/dev/null
rm -rf reports/gui/smoke/ 2>/dev/null
```

On Windows:
```cmd
rmdir /s /q outputs\work\gui_agent\smoke 2>nul
rmdir /s /q reports\gui\smoke 2>nul
```

### 8.2 Do NOT Remove

- `rawdata/` — never modify rawdata.
- `outputs/derivatives/` — never remove derivative outputs unless generated by this smoke guide.
- `outputs/reports/` — only remove explicit smoke guide artifacts.
- `outputs/work/reviewed_pipelines/` — do not touch reviewed pipeline outputs.
- Test artifacts in `outputs/reports/audit_records/` — these are test-generated, leave for audit trail.

### 8.3 Environment Variable Cleanup

```bash
# Verify no GUI-related overrides remain
unset MEDIMAGE_GUI_AGENT_REAL_PROVIDER
unset MEDIMAGE_GUI_AGENT_PROVIDER
unset MEDIMAGE_GUI_AGENT_BACKEND
```

---

## 9. Manual Smoke Checklist

Copy this checklist and check each item. Use a fresh copy for each smoke run.

```
M9-GUI-T006 Manual Smoke Checklist
===================================
Date: _______________
Operator: _______________
Environment: _______________

PRECONDITIONS
[ ] MEDIMAGE_GUI_AGENT_REAL_PROVIDER is NOT set to 1
[ ] MEDIMAGE_GUI_AGENT_PROVIDER is NOT set to pywinauto
[ ] No GUI/manual node in reviewed execution allowlist

TEST EXECUTION — REVIEWED EXECUTION BLOCKLIST
[ ] test_gui_reviewed_execution_blocklist.py: 38/38 passed
[ ] test_plan_adapter.py: all passed
[ ] test_approval_gate.py: all passed
[ ] test_execute_reviewed_api.py: all passed
[ ] test_tool_catalog.py: all passed
[ ] pytest --tb=short: 1192+ passed, 4 skipped

TEST EXECUTION — FRONTEND
[ ] npm --prefix src/frontend run build: passed

INSPECTION — MOCK PROVIDER
[ ] MockGuiProvider inspected — no real desktop control
[ ] MockGuiProvider perform_step returns MOCK_RECORDED
[ ] MockGuiProvider capture_screenshot writes placeholder text

INSPECTION — PyWinAuto PROVIDER
[ ] PyWinAutoGuiProvider NOT called during smoke
[ ] No pywinauto import triggered
[ ] No mouse, keyboard, screenshot, or desktop interaction occurred

INSPECTION — /api/gui-agent/* BYPASS
[ ] bypass documented in test_gui_bypass_gap_still_exists
[ ] No fix applied in T006
[ ] Future guard task needed before provider call

INSPECTION — READ-ONLY OBSERVATION CONTRACT
[ ] docs/GUI_READ_ONLY_OBSERVATION_CONTRACT.md exists
[ ] Tier 0 actions documented, Tier 1+ blocked
[ ] Real provider observation is design-only
[ ] screenshot_policy=disabled, clipboard_policy=disabled

REGRESSION
[ ] SPM sandbox allowlist still works
[ ] DPABI metadata allowlist still works
[ ] GPU contract allowlist still works
[ ] test_spm_approval_still_works passed
[ ] test_gpu_approval_still_works passed

SAFETY
[ ] No real screenshots captured
[ ] No clipboard accessed
[ ] No rawdata modified
[ ] No derivatives modified by GUI agent
[ ] No GUI automation library called

CLEANUP
[ ] Temporary smoke outputs removed
[ ] Environment variables cleaned up
[ ] No test artifacts left in unexpected locations

RESULT: [ ] PASS    [ ] FAIL (describe below)
___________________________________________________________
___________________________________________________________
___________________________________________________________
```

---

## 10. Next Steps After T006

After completing this manual smoke guide, proceed to:

```
M9-GUI-CLOSEOUT — GUI/manual phase closeout
```

The closeout should consolidate all M9 deliverables:
- Threat model and inventory (T001)
- Approval and HITL design (T002)
- Action taxonomy and sandbox contract (T003)
- Blocklist tests (T004)
- Read-only observation contract (T005)
- Manual smoke guide (T006)
- Summary of remaining safety gaps
- Recommendations for future guard implementation

---

## 11. References

| Document | Content |
|----------|---------|
| `docs/GUI_MANUAL_AGENT_THREAT_MODEL.md` | Threat model, inventory, taxonomy |
| `docs/GUI_MANUAL_APPROVAL_HITL_DESIGN.md` | Three-layer approval model, provider policy |
| `docs/GUI_ACTION_TAXONOMY_AND_SANDBOX_CONTRACT.md` | 29-action taxonomy, sandbox declaration schema |
| `docs/GUI_READ_ONLY_OBSERVATION_CONTRACT.md` | Tier 0 observation contract |
| `tests/unit/test_gui_reviewed_execution_blocklist.py` | 38 blocklist tests (M9-GUI-T004) |
| `src/backend/app/runtime/gui_agent.py` | GUI Agent runtime |
| `src/backend/app/api/gui_agent_routes.py` | GUI Agent API endpoints |
| `src/backend/app/planner/plan_adapter.py` | Plan adapter with GUI blocking |
| `src/backend/app/planner/approval_gate.py` | Approval gate step 12 |
| `src/backend/app/api/execute_reviewed_routes.py` | Gated execution with policy checks |
| `src/backend/app/runtime/tool_catalog.py` | Tool catalog with gui_* fallback |
