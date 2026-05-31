# GUI/Manual Agent Threat Model

> M9-GUI-T001 | GUI/manual node inventory and threat model  
> Status: DRAFT | Date: 2026-05-29

## 1. Scope and Non-Goals

### Scope
- Inventory all GUI/manual-related code across the codebase
- Assess the existing GUI Agent subsystem (`gui_agent.py` + `gui_agent_routes.py`)
- Model threats associated with unattended GUI/desktop control
- Define required safety boundaries for future M9 rollout
- Document human-in-the-loop, approval, audit, and sensitive-data requirements

### Non-Goals
- Implementing GUI automation or new GUI runners
- Opening GUI/manual execution in the reviewed execution allowlist
- Modifying `approval_gate.py`, `plan_adapter.py`, `execute_reviewed_routes.py`, or frontend behavior
- Calling pywinauto / pyautogui / pynput / selenium / playwright
- Registering new `NODE_REGISTRY` entries for GUI nodes
- Opening real desktop control, browser control, or clipboard access

---

## 2. Current GUI/Manual Node Inventory

### 2.1 Summary

**No `gui_*` nodes are registered in `NODE_REGISTRY`.**  
**No GUI nodes appear in `TOOL_METADATA` (explicit catalog).**  
**No GUI/manual execution is opened by M6/M7/M8.**  
**M9 begins with threat modeling only.**

### 2.2 Complete Inventory Table

| Field | Value |
|---|---|
| GUI `node_id`s in `NODE_REGISTRY` | **0** (none registered) |
| GUI nodes in `TOOL_METADATA` | **0** (only `_fallback()` inference) |
| GUI nodes in reviewed execution allowlist | **0** |
| GUI runner functions | **0** (no `gui_*` runner wrapper) |
| GUI API endpoints | **5** (standalone, not gated by reviewed execution) |
| GUI desktop control capability | **Available** (PyWinAutoGuiProvider) |
| Default provider | **mock** (safe by default) |
| GUI agent session runtime | **Live** (`gui_agent.py`, registered in `main.py`) |

### 2.3 Detailed Node Inventory

```
node_id               runner_exists  runner_file  registered  cataloged  backend    reviewed_execution_status
───────────────────── ────────────── ──────────── ─────────── ────────── ────────── ─────────────────────────────
(none registered)     —              —            —           —          —          —
```

### 2.4 Existing GUI-Related Code (Subsystem Audit)

| File | Component | Status | Threat Relevance |
|---|---|---|---|
| `src/backend/app/runtime/gui_agent.py` | GUI Agent runtime (Mock + PyWinAuto providers) | **LIVE** | Real desktop control available |
| `src/backend/app/api/gui_agent_routes.py` | 5 REST API endpoints | **LIVE** | Ungated by reviewed execution |
| `src/backend/app/api/models.py` | `GuiAgentSessionRequest`, `GuiAgentStepRequest` | **LIVE** | Pydantic models |
| `src/backend/app/main.py` | `app.include_router(gui_agent_router)` | **LIVE** | Router registered |
| `src/backend/app/runtime/desktop_config.py` | `gui_agent` config section | **LIVE** | Provider selection, approval flag |
| `src/frontend/src/components/DesktopSettingsPanel.tsx` | GUI provider selector + "Allow GUI Agent" checkbox | **LIVE** | User-facing control |
| `src/backend/app/runtime/tool_catalog.py` | `_fallback()` `gui_` prefix inference | **ACTIVE** | Auto-flags `manual_required=True` |
| `src/backend/app/planner/plan_adapter.py` | `blocked_gui_nodes` classification | **ACTIVE** | Blocks `gui_` prefix nodes |
| `src/backend/app/planner/approval_gate.py` | `MANUAL_REQUIRED_NODE` error (step 12) | **ACTIVE** | Blocks `manual_required_nodes` |
| `src/backend/app/planner/plan_validator.py` | `manual_required_nodes` tracking | **ACTIVE** | Flags in validation result |
| `src/backend/app/api/execute_reviewed_routes.py` | `_is_policy_blocked()` includes GUI | **ACTIVE** | Blocks `blocked_gui_nodes` |
| `src/backend/app/preprocessing/rsfmri_plan_builder.py` | `dpabi_gui_called: False` constraint | **ACTIVE** | Explicitly prevents DPABI GUI |
| `src/backend/app/tools/release_readiness.py` | References `gui_agent_routes.py` in file inventory | **ACTIVE** | Documented in release checks |

### 2.5 GUI Agent Subsystem Detail

#### Providers

| Provider | `provider_name` | Real Desktop Control | Screenshot | Default |
|---|---|---|---|---|
| `MockGuiProvider` | `mock` | No — records intent only | `.txt` placeholder | **Yes** |
| `PyWinAutoGuiProvider` | `pywinauto` | **Yes** — click, type_text, menu_select, locate_window, wait | Real `.png` pixels | No |

#### Supported Actions (PyWinAuto)

| Action | Effect | Risk |
|---|---|---|
| `wait` | Sleep N seconds | Low |
| `locate_window` | Find and focus window by title regex | Medium |
| `click` | Click a control or window | **High** |
| `type_text` | Type keystrokes into window | **High** |
| `menu_select` | Navigate menu path | **High** |
| `record_observation` | No-op (audit only) | Low |

#### API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/gui-agent/sessions` | List all sessions |
| `POST` | `/api/gui-agent/sessions` | Create session (provider selection) |
| `POST` | `/api/gui-agent/sessions/{id}/step` | Execute a GUI action step |
| `GET` | `/api/gui-agent/sessions/{id}/screenshot` | Capture screenshot |
| `POST` | `/api/gui-agent/sessions/{id}/abort` | Abort session |

#### Data Storage

| Path | Content |
|---|---|
| `outputs/work/gui_agent/sessions/{id}/session.json` | Full session state, steps, artifacts |
| `outputs/work/gui_agent/sessions/{id}/replay_steps.py` | Audit replay script |
| `outputs/work/gui_agent/sessions/{id}/screenshots/` | Screenshot files (.txt or .png) |

#### Environment Variables

| Variable | Purpose |
|---|---|
| `MEDIMAGE_GUI_AGENT_PROVIDER` | Default provider (`mock` / `pywinauto`) |
| `MEDIMAGE_GUI_AGENT_BACKEND` | PyWinAuto backend (`uia` / `win32`) |

---

## 3. Current Registry / Catalog / Reviewed-Execution Status

### 3.1 Node Registry

```
No gui_* node IDs in NODE_REGISTRY.
Any plan referencing a gui_* node would get KeyError at executor dispatch.
```

Source: search of `src/backend/app/runtime/node_registry.py` — `NODE_REGISTRY` dict contains no `gui_` prefix entries. Final entry is `gpu_nuisance_regression_subject`.

### 3.2 Tool Catalog

```
No gui_* entries in TOOL_METADATA.
_fallback("gui_*") returns:
  backend="unknown", manual_required=True, risk_level="high", tags=["gui"]
```

Source: `src/backend/app/runtime/tool_catalog.py:505-509` — `elif node_id.startswith("gui_"):` branch in `_fallback()`.

### 3.3 Plan Adapter

```
classify_plan_nodes() blocks gui_ nodes:
  - nid.startswith("gui_") → blocked_gui_nodes
  - cat.backend == "gui-agent" → blocked_gui_nodes
  - cat.manual_required → blocked_manual_required_nodes

_is_policy_blocked() includes blocked_gui_nodes + blocked_manual_required_nodes.
```

Source: `src/backend/app/planner/plan_adapter.py:480-483` — GUI classification; `plan_adapter.py:536-544` — blocked aggregation.

### 3.4 Approval Gate

```
check_approval_gate() step 12: manual_required_nodes non-empty → blocked.
Returns ApprovalGateResult(execution_allowed=False) with error code MANUAL_REQUIRED_NODE.
```

Source: `src/backend/app/planner/approval_gate.py:276-284`.

### 3.5 Execute Reviewed

```
_is_policy_blocked() includes blocked_gui_nodes + blocked_manual_required_nodes.
_execution_meta() defaults executor_called=False.
```

Source: `src/backend/app/api/execute_reviewed_routes.py:140-146`.

### 3.6 Current Behavior Summary

| Path | Result |
|---|---|
| Plan has `gui_*` node | `manual_required=True` via `_fallback()` |
| Plan Validator | Flags in `manual_required_nodes` |
| Approval Gate | Blocks with `MANUAL_REQUIRED_NODE` |
| Plan Adapter | `blocked_gui_nodes` / `blocked_manual_required_nodes` |
| Execute Reviewed | `EXECUTION_POLICY_BLOCKED` → `executor_called=false` |
| GUI Agent API (standalone) | **Ungated** — operates independently |

> **Key Finding:** The GUI Agent API (`/api/gui-agent/*`) is a standalone subsystem that is NOT gated by the reviewed execution pipeline. It has its own approval mechanism (`approved=true` boolean), but that approval is within the GUI agent subsystem, not routed through `plan_validator` → `approval_gate` → `plan_adapter` → `execute_reviewed`.

---

## 4. GUI/Manual Execution Threat Model

### 4.1 Threat Surface

```
┌─────────────────────────────────────────────────────────────┐
│                    THREAT SURFACE                            │
├─────────────────────────────────────────────────────────────┤
│  1. Unattended Control Risk                                 │
│  2. Sensitive Data Exposure                                 │
│  3. External Application Risk                               │
│  4. Prompt Injection / UI Injection                         │
│  5. Credential Capture                                      │
│  6. Path Traversal via Session Data                         │
│  7. Bypass of Reviewed Execution Pipeline                   │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.1 Unattended Control Risk

**Description**: GUI/manual Agent must not execute unattended destructive actions.

**Requirements**:
- GUI/manual Agent must not click through dialogs automatically.
- GUI/manual Agent must not approve external prompts automatically.
- GUI/manual Agent must not operate outside the declared application/window scope.
- Every destructive/high-risk action requires explicit per-step human confirmation.
- No background unattended execution allowed.
- Stop condition and emergency abort must be available at every step.

**Current state**:
- `PyWinAutoGuiProvider` has `approved` gate but it is a single boolean, not per-action.
- `MockGuiProvider` is safe by default (no real control).
- GUI agent runs in its own subsystem — no integration with `plan_adapter` or `approval_gate`.

**Risk level**: **HIGH** if `provider=pywinauto` and `approved=true`.

---

### 4.2 Sensitive Data Risk

**Categories of sensitive data**:

| Category | Examples | Exposure Vector |
|---|---|---|
| Credentials | MATLAB/SPM passwords, API keys | Window text in screenshots, keystroke logs |
| Medical data | Subject IDs, BOLD images, T1w scans | Screenshot pixels, window titles |
| Personal identifiers | Patient names, scan dates, file paths | Session JSON, screenshot capture |
| Browser data | Session cookies, URLs | If browser is the target app |
| Clipboard contents | Any data on clipboard | `type_text` or clipboard access |

**Requirements**:
- No credential exfiltration.
- No logging of secrets or API keys.
- No screenshots stored unless explicitly scoped and redacted.
- No clipboard reading unless explicitly approved.
- Screenshot redaction policy must exist before any real screenshot capture.
- Session JSON must not contain secrets in plaintext.

**Current state**:
- Screenshots saved to `outputs/work/gui_agent/sessions/{id}/screenshots/` — no redaction mechanism.
- Session JSON contains full step parameters — no secret filtering.
- `type_text` can send arbitrary strings including passwords.

**Risk level**: **HIGH** for real provider with screenshots enabled.

---

### 4.3 External Application Risk

**Description**: External GUI apps are not safe reviewed execution targets by default. Each app requires a separate safety contract.

**Target applications identified in code**:

| Application | Context | Risk |
|---|---|---|
| MATLAB | `target_app="spm"`, SPM/DPABI GUI automation | **HIGH** — medical image processing |
| SPM GUI | Subset of MATLAB | **HIGH** — statistical analysis |
| DPABI GUI | Subset of MATLAB | **HIGH** — rs-fMRI pipeline |
| Browser | Not implemented but structurally possible | **HIGH** — web access |
| File Explorer | Window title matching could target | **MEDIUM** — file system access |
| Terminal/IDE | Window title matching could target | **MEDIUM** — system commands |
| OS Dialogs | Save/open/file picker dialogs | **HIGH** — uncontrolled file access |
| Email/Messaging | Window title matching could target | **CRITICAL** — data exfiltration |
| Cloud Sync Folders | Window title matching could target | **MEDIUM** — unintended sync |

**Requirements**:
- Each app requires a separate safety contract before GUI automation is allowed.
- Default: all external apps are blocked for GUI automation.
- SPM/DPABI apps must go through sandbox-mode reviewed execution, not GUI automation.
- No browser automation without a separate browser safety contract.
- No email/messaging app control — blocked permanently.

**Current state**:
- `create_gui_agent_session()` accepts arbitrary `target_app` string — no allowlist.
- `PyWinAutoGuiProvider._window()` matches windows by regex title — can target any application.

**Risk level**: **HIGH** — no application allowlist.

---

### 4.4 Prompt Injection / UI Injection

**Description**: GUI content can contain untrusted instructions. Text visible in UI must not override system policy.

**Sources of untrusted content**:
- Browser pages (if browser is targeted)
- MATLAB command window output
- Document viewers (PDFs, notebooks)
- Terminal output
- Log files displayed in UI
- Error messages from SPM/DPABI
- File names and paths visible in file dialogs

**Requirements**:
- The agent must not follow instructions found in screenshots or app windows unless they match the user-approved task.
- Text visible in UI must not override system policy or change the agent's objective.
- Window titles and control labels must be treated as untrusted input.
- No self-modifying behavior based on GUI content.

**Current state**:
- No prompt injection guard in `gui_agent.py`.
- `PyWinAutoGuiProvider` reads window text via `window.window_text()` — could be influenced by hostile UI content.

**Risk level**: **MEDIUM** — injection vector exists but requires hostile application to be running.

---

### 4.5 Credential Capture

**Description**: GUI agent `type_text` action can send passwords. Screenshots can capture password fields. Session JSON may inadvertently log credentials.

**Requirements**:
- `type_text` must not be used for password/credential entry.
- Screenshots must redact password fields before storage.
- Session JSON must not contain `type_text` parameter values that are credentials.
- No clipboard access for credential transfer.

**Current state**:
- `type_text` params stored unredacted in session JSON.
- Screenshots are full-window captures — no redaction.

**Risk level**: **HIGH** for real provider.

---

### 4.6 Path Traversal via Session Data

**Description**: Session ID is used as a directory name. Screenshot paths are constructed from session data.

**Current state**:
- `_session_dir()` validates `session_id` for `/`, `\\`, `..` — **partially mitigated**.
- Screenshot filenames use sequential numbering — safe.
- Session JSON path: `outputs/work/gui_agent/sessions/{id}/session.json` — within work directory.

**Risk level**: **LOW** — basic path traversal prevention exists.

---

### 4.7 Bypass of Reviewed Execution Pipeline

**Description**: The GUI agent subsystem operates independently of the 12-gate reviewed execution pipeline. API endpoints at `/api/gui-agent/*` do not go through `plan_validator`, `approval_gate`, `plan_adapter`, or `execute_reviewed`.

**Current state**:
- GUI agent routes are registered in `main.py` directly — no middleware gating.
- No `MEDIMAGE_ENABLE_REVIEWED_EXECUTION` check on GUI endpoints.
- No audit record integration between GUI sessions and the audit record system.
- GUI agent "approval" is its own boolean, not the structured `ApprovalRecord` used by reviewed execution.

**Risk level**: **MEDIUM** (mitigated by `mock` default) — would escalate if provider default changes.

---

## 5. Human-in-the-Loop Requirements

Future any GUI/manual execution must require:

| Requirement | Detail |
|---|---|
| Explicit user-visible action plan | User must see every step before execution begins |
| Step-by-step confirmation | High-risk actions require individual confirmation |
| No wildcard approval | `approved=true` for session is insufficient |
| No background unattended execution | User must be present and aware |
| Clear target application/window | Explicit window title and application scope |
| Clear file path scope | What files will be read/written |
| Clear rollback / cleanup plan | Reversible actions preferred |
| Audit log for every UI action | Steps, screenshots, outcomes |
| Screenshot redaction policy | What gets captured and what gets redacted |
| Stop condition and emergency abort | `abort_gui_agent_session()` must always be available |
| Semantic confirmation | User must know: what app, what action, what file/path, what expected side effect |

**Current state**: `approved=true` boolean is the only gate — no per-step confirmation, no action plan preview.

---

## 6. Approval Requirements

### 6.1 Current State

| Layer | GUI Behavior |
|---|---|
| `approval_gate.py` | `manual_required_nodes` → `MANUAL_REQUIRED_NODE` blocked |
| `plan_adapter.py` | `gui_` prefix → `blocked_gui_nodes` |
| `execute_reviewed_routes.py` | GUI nodes in `blocked_gui_nodes` → `EXECUTION_POLICY_BLOCKED` |
| GUI agent own approval | `approved=true` boolean — independent of reviewed execution |

### 6.2 Recommended Future Requirements

Future M9 implementation should enforce:

- GUI/manual nodes must require explicit node approval in the reviewed execution pipeline.
- GUI/manual backends must be classified as high-risk backends.
- `approved_nodes=["*"]` must not cover GUI/manual nodes.
- `approved_backends=["gui"]` or `["manual"]` alone is insufficient without explicit per-node approval.
- Any destructive action requires separate per-action confirmation.
- Each GUI session must be linked to a reviewed execution plan and audit record.

### 6.3 Suggested Code Changes (NOT part of M9-GUI-T001 — document only)

```python
# Suggested future additions to approval_gate.py:
HIGH_RISK_BACKENDS to include: "gui", "manual", "desktop", "browser"

# Suggested future additions to plan_adapter.py:
EXPLICIT_APPROVAL_REQUIRED_NODE_IDS to include all gui_* node prefixes
```

---

## 7. Action Risk Taxonomy

### Level 0: Read-Only Observation
| Action | Risk | Requires Confirmation |
|---|---|---|
| `screenshot` (redacted) | Low | No |
| `window_title` read | Low | No |
| `record_observation` | Low | No |
| `visible_ui_state` query | Low | No |

### Level 1: Low-Risk Navigation
| Action | Risk | Requires Confirmation |
|---|---|---|
| `focus window` | Low | No |
| `scroll` | Low | No |
| `switch tabs` | Low | No |
| `open non-sensitive panel` | Low | No |
| `wait` | Low | No |

### Level 2: Medium-Risk Interaction
| Action | Risk | Requires Confirmation |
|---|---|---|
| `fill form fields` (non-sensitive) | Medium | Per-field group |
| `select files` under scoped directory | Medium | Per file |
| `trigger dry-run action` | Medium | Yes |
| `menu_select` (read-only path) | Medium | Yes |
| `screenshot` (unredacted, scoped) | Medium | Yes |

### Level 3: High-Risk — Blocked by Default
| Action | Risk | Requires Confirmation |
|---|---|---|
| `click Run / Execute / Submit` | **HIGH** | Blocked |
| `save / overwrite files` | **HIGH** | Blocked |
| `delete files` | **HIGH** | Blocked |
| `open rawdata` | **HIGH** | Blocked |
| `launch external app with user data` | **HIGH** | Blocked |
| `access clipboard` | **HIGH** | Blocked |
| `upload/download files` | **HIGH** | Blocked |
| `network submission` | **HIGH** | Blocked |
| `accept license / security / permission dialogs` | **HIGH** | Blocked |
| `install software` | **HIGH** | Blocked |
| `enter credentials` | **CRITICAL** | **Permanently Blocked** |
| `send email/message` | **CRITICAL** | **Permanently Blocked** |
| `type_text` with credentials | **CRITICAL** | **Permanently Blocked** |

---

## 8. Blocked Actions (Permanent)

| Action | Reason |
|---|---|
| Enter credentials / passwords | Credential exfiltration risk |
| Send email / messages | Data exfiltration risk |
| Open browser to arbitrary URLs | Network access outside scope |
| Click OS-level security dialogs | Bypasses OS security |
| Install software | System integrity risk |
| Delete files outside derivatives | Data loss risk |
| Modify rawdata | Rawdata readonly invariant |
| Upload files to external servers | Data exfiltration risk |
| Access clipboard with sensitive content | Credential/sensitive data leak |
| Control email/messaging apps | Permanent block |

---

## 9. Sensitive Data / Credential Handling

### 9.1 Screenshot Policy

| Rule | Requirement |
|---|---|
| Default | Screenshots disabled |
| Scoped enable | Per-session, per-step opt-in |
| Redaction | Black-bar or blur regions with text/paths/images |
| Storage | Encrypted or access-controlled directory |
| Retention | Auto-delete after session close or audit review |
| Review | Human must review screenshots before storage finalization |

### 9.2 Session Data Policy

| Rule | Requirement |
|---|---|
| `type_text` params | Must not contain passwords/tokens |
| Window titles | Must be filtered for PII/paths |
| Artifact metadata | Must not expose absolute paths |
| Replay scripts | Must be reviewed before sharing |

### 9.3 Credential Boundary

| Rule | Requirement |
|---|---|
| No credential in session JSON | Enforced at `step_gui_agent_session()` |
| No credential in screenshots | Redaction required |
| No credential in logs | Log-scrubbing filter |
| No clipboard credential transfer | Clipboard access blocked |

---

## 10. External Application Boundary

| Application | Default Status | Condition for Opening |
|---|---|---|
| MATLAB | Blocked | Sandbox-mode reviewed execution, not GUI |
| SPM GUI | Blocked | Requires separate SPM GUI safety contract |
| DPABI GUI | Blocked | Requires separate DPABI GUI safety contract |
| Browser | **Permanently Blocked** | — |
| File Explorer | Blocked | Requires scoped-directory safety contract |
| Terminal/IDE | Blocked | Requires command allowlist safety contract |
| OS Dialogs | Blocked | Requires dialog-type allowlist |
| Email/Messaging | **Permanently Blocked** | — |
| Cloud Sync Folders | Blocked | Requires sync-exclusion safety contract |

---

## 11. Audit / Replay / Rollback Requirements

### 11.1 Audit

| Event | Record |
|---|---|
| Session created | `session_id`, `provider`, `target_app`, `objective` |
| Step executed | `action`, `parameters`, `executed`, `provider_status` |
| Screenshot captured | `path`, `type`, redaction status |
| Session aborted | `reason`, `time` |
| Session completed | Summary of all steps |

### 11.2 Replay

- `replay_steps.py` script already generated for every session.
- Must be human-reviewable before execution.
- Must not auto-execute without explicit user confirmation.

### 11.3 Rollback

- GUI actions are not trivially reversible.
- Prefer dry-run / observation before any write action.
- No automatic rollback — human must manually undo if needed.

---

## 12. Current Policy Behavior

### 12.1 At Every Layer

| Layer | Behavior | Source |
|---|---|---|
| Tool Catalog | `_fallback("gui_*")` → `manual_required=True` | `tool_catalog.py:505-509` |
| Plan Validator | `manual_required_nodes` in result | `plan_validator.py:273` |
| Approval Gate | Step 12 → `MANUAL_REQUIRED_NODE` blocks | `approval_gate.py:276-284` |
| Plan Adapter | `blocked_gui_nodes` ← `gui_` prefix check | `plan_adapter.py:480-483` |
| Execute Reviewed | `_is_policy_blocked()` includes GUI | `execute_reviewed_routes.py:140-146` |
| GUI Agent API | Own `approved` boolean (independent) | `gui_agent_routes.py` |

### 12.2 End-to-End Test Coverage

| Test | File | What It Verifies |
|---|---|---|
| `test_manual_required_blocked` | `test_approval_gate.py:133` | `gui_acpc_location` → `MANUAL_REQUIRED_NODE` |
| `test_manual_required_still_blocks` | `test_approval_gate.py:325` | Even with explicit approval, still blocked |
| `test_manual_required` | `test_approval_gate_api.py:101` | API returns `execution_allowed=false` |
| `test_m5t016_manual_required_no_executor` | `test_execute_reviewed_api.py:1193` | `gui_acpc_manual` → executor not called |
| `test_unknown_node_blocked` | `test_plan_adapter.py:134` | Unknown `gui_` node → `blocked_unknown_nodes` |
| `test_gui_agent_mock_session_records_steps` | `test_gui_agent_runtime.py:11` | Mock session works |
| `test_gui_agent_real_provider_requires_approval` | `test_gui_agent_runtime.py:39` | PyWinAuto blocked without approval |
| `test_gui_agent_api_mock_session` | `test_api_basic.py:48` | API endpoint works |

---

## 13. Safety Gaps Identified

### 13.1 Gap 1: GUI Agent API Ungated by Reviewed Execution

**Description**: `/api/gui-agent/*` endpoints are not routed through `plan_validator` → `approval_gate` → `plan_adapter` → `execute_reviewed`. They operate independently.

**Severity**: Medium (mitigated by `mock` default provider)  
**Action**: Document for M9-GUI-T004 (plan_adapter blocklist tests). Do NOT modify in T001.

### 13.2 Gap 2: No Application Allowlist

**Description**: `create_gui_agent_session()` accepts any `target_app` string. `PyWinAutoGuiProvider._window()` matches any window by title regex.

**Severity**: High  
**Action**: Document for M9-GUI-T003 (sandbox declaration contract). Do NOT modify in T001.

### 13.3 Gap 3: No Per-Action Confirmation

**Description**: `approved=true` is a session-level boolean. No per-step, per-action confirmation exists.

**Severity**: Medium  
**Action**: Document for M9-GUI-T002 (human-in-the-loop design). Do NOT modify in T001.

### 13.4 Gap 4: No Screenshot Redaction

**Description**: Screenshots are full captures. No redaction mechanism exists. Medical data, credentials, and paths may be visible.

**Severity**: High  
**Action**: Document for M9-GUI-T005 (observation contract). Do NOT modify in T001.

### 13.5 Gap 5: No Audit Record Integration

**Description**: GUI sessions write `session.json` but do not integrate with `audit_record.py` or the reviewed execution audit trail.

**Severity**: Medium  
**Action**: Document for M9-GUI-T006 (smoke guide). Do NOT modify in T001.

---

## 14. Future M9 Rollout Plan

| Task | Content | Dependencies |
|---|---|---|
| **M9-GUI-T001** ✅ | GUI/manual node inventory and threat model (this doc) | — |
| **M9-GUI-T002** | GUI/manual approval and human-in-the-loop design | T001 |
| **M9-GUI-T003** | GUI action taxonomy and sandbox declaration contract | T001 |
| **M9-GUI-T004** | GUI/manual plan_adapter blocklist tests | T001 |
| **M9-GUI-T005** | Read-only GUI observation contract, if safe | T002, T003 |
| **M9-GUI-T006** | Manual-only smoke guide, no automation | T002, T003, T004 |
| **M9-GUI-CLOSEOUT** | GUI/manual phase closeout | T001-T006 |

### Rollout Constraints

```
Do not implement GUI automation before T002/T003/T004.
Do not allow click/keyboard automation in T001.
Do not open browser or desktop control in T001.
Do not register GUI runners in NODE_REGISTRY before T004.
Do not allowlist GUI nodes before T005.
Do not integrate GUI agent with reviewed execution before T004.
```

---

## 15. Acceptance Criteria for Future GUI/Manual Reviewed Execution

Before any GUI/manual node enters the reviewed execution allowlist:

1. GUI nodes have explicit `NODE_REGISTRY` entries with safety contracts.
2. GUI nodes are in `TOOL_METADATA` with `requires_approval=True`, `manual_required=True`, `risk_level="high"`.
3. `HIGH_RISK_BACKENDS` includes `gui`, `manual`, `desktop`, `browser`.
4. `plan_adapter.py` classifies GUI nodes under `blocked_gui_nodes` unless explicit sandbox contract is satisfied.
5. `approval_gate.py` blocks wildcard approval for GUI nodes.
6. `execute_reviewed_routes.py` blocks GUI nodes except those in safe allowlist.
7. Per-action confirmation exists for all Level 2+ actions.
8. Application allowlist is enforced.
9. Screenshot redaction is implemented.
10. Audit record integration is complete.
11. Human-in-the-loop semantic confirmation is implemented.
12. Emergency abort is available at every step.
13. All Level 3 actions remain blocked by default.
14. Credential entry and email/messaging remain permanently blocked.
15. All safety gaps from Section 13 are addressed.

---

## 16. References

| Document | Relationship |
|---|---|
| `docs/CURRENT_STATE.md` | Current milestone status |
| `docs/NEXT_ACTIONS.md` | Next actions pointer |
| `docs/SAFE_REVIEWED_EXECUTION_DESIGN.md` | 14-condition preflight gate |
| `docs/EXECUTION_INTEGRATION_DESIGN.md` | M5 execution integration |
| `docs/GPU_REVIEWED_EXECUTION_SAFETY_REVIEW.md` | M8 GPU safety model (parallel structure) |
| `src/backend/app/runtime/gui_agent.py` | GUI Agent runtime |
| `src/backend/app/api/gui_agent_routes.py` | GUI Agent API |
| `src/backend/app/runtime/desktop_config.py` | Desktop/GUI config |
| `src/backend/app/planner/plan_adapter.py` | Node classification |
| `src/backend/app/planner/approval_gate.py` | Approval gate (step 12) |
| `src/backend/app/api/execute_reviewed_routes.py` | Gated execution |
| `src/frontend/src/components/DesktopSettingsPanel.tsx` | Frontend GUI controls |
