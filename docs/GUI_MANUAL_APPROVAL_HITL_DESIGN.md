# GUI/Manual Agent Approval & Human-in-the-Loop Design

> M9-GUI-T002 | GUI/manual approval and human-in-the-loop design  
> Status: DESIGN | Date: 2026-07-11  
> Depends on: M9-GUI-T001 (threat model and inventory)

---

## 1. Scope and Non-Goals

### Scope

- Design a three-layer approval model (session, action-plan, per-action) for GUI/manual Agent execution.
- Define how `/api/gui-agent/*` can be integrated with the reviewed execution safety pipeline, or gated equivalently.
- Design provider policy (mock vs pywinauto/real desktop).
- Define human-in-the-loop (HITL) UI requirements, audit log requirements, emergency abort, and stop conditions.
- Design sensitive data / screenshot / clipboard policy for GUI sessions.
- Define a test strategy and acceptance criteria for any future GUI/manual allowlist entry.
- Define the M9 rollout plan from T002 through T006 and closeout.

### Non-Goals

- Implementing any code changes — no new runners, no allowlist entries, no modified approval gate.
- Calling GUI automation libraries (pywinauto, pyautogui, pynput, selenium, playwright).
- Controlling the real desktop, clicking buttons, typing text, capturing screenshots.
- Opening `/api/gui-agent/*` to real desktop providers.
- Fixing the current safety gap — T002 documents the required design; implementation is in later tasks.
- Modifying `NODE_REGISTRY`, `TOOL_METADATA`, or the reviewed execution allowlist.

---

## 2. Current Safety Gap (Explicit Record)

### 2.1 The Gap

The reviewed execution pipeline (12 gates: `plan_validator` → `approval_gate` → `plan_adapter` → `execute_reviewed`) correctly blocks all `gui_*` nodes from entering the allowlist. However, `/api/gui-agent/*` is a **separate API surface** that operates outside this pipeline entirely.

```text
                    ┌─────────────────────────────────────────────┐
                    │   Reviewed Execution Pipeline (12 gates)     │
                    │                                             │
  POST /api/plans/  │  plan_validator → approval_gate →           │
  execute-reviewed  │  plan_adapter → execute_reviewed            │
                    │                                             │
                    │  ✓ GUI nodes blocked by all gates           │
                    │  ✓ executor_called=false                    │
                    │  ✓ audit records written                    │
                    └─────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │   GUI Agent API (standalone)                │
                    │                                             │
  POST /api/gui-    │  create_gui_agent_session()                 │
  agent/sessions    │    → only requires provider + approved bool │
                    │                                             │
  POST /api/gui-    │  step_gui_agent_session()                   │
  agent/sessions/   │    → if approved=true + provider=pywinauto  │
  {id}/step         │    → EXECUTES REAL DESKTOP ACTION           │
                    │                                             │
                    │  ✗ No plan_validator gate                   │
                    │  ✗ No approval_gate gate                    │
                    │  ✗ No plan_adapter policy check             │
                    │  ✗ No execute_reviewed allowlist check      │
                    │  ✗ No audit_record integration              │
                    │  ✗ No MEDIMAGE_ENABLE_REVIEWED_EXECUTION    │
                    └─────────────────────────────────────────────┘
```

### 2.2 What This Means

If `provider=pywinauto` and `approved=true` are sufficient to call `step_gui_agent_session()`, then a single HTTP POST to `/api/gui-agent/sessions/{id}/step` can:

- Click any button on the Windows desktop (`click`)
- Type arbitrary keystrokes (`type_text`)
- Navigate menu paths (`menu_select`)
- Capture screenshots of any window (`capture_screenshot`)

This is a **high-risk bypass path** that is independent of all reviewed execution safety gates.

### 2.3 M9-GUI-T002 Position

```text
M9-GUI-T002 does NOT fix this bypass.
M9-GUI-T002 DEFINES the required approval/HITL design that later tasks MUST implement.
Until such controls exist, real desktop providers MUST remain disabled by default.
The mock provider is safe and can remain active for testing.
```

---

## 3. Approval Model Overview

### 3.1 Three-Layer Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    APPROVAL LAYERS                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAYER 1: Session-Level Approval                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Defines: who, what app, what provider, what scope        │   │
│  │ Does NOT authorize: any specific action                  │   │
│  │ Gate: create_gui_agent_session()                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ↓                                        │
│  LAYER 2: Action-Plan Approval                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Defines: what exact steps, what files, what side effects │   │
│  │ User reviews and approves the ENTIRE action plan         │   │
│  │ Gate: before first step executes                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ↓                                        │
│  LAYER 3: Per-Action Confirmation                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Defines: individual step confirmation for Tier 2/3       │   │
│  │ Gate: before each high-risk step                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Why `approved=true` is Insufficient

The current single boolean:

- Does not specify **what** is being approved (which app, which window, which actions).
- Does not specify **scope** (which files, which directories, which network targets).
- Does not differentiate between `record_observation` (safe) and `click Submit` (dangerous).
- Does not enforce **human presence** or **time/duration limits**.
- Cannot be semantically verified — `approved=true` could mean anything from "I want to inspect the SPM batch editor" to "install arbitrary software."

### 3.3 Why Wildcard Approval Cannot Cover GUI/Manual

In the reviewed execution pipeline:

- `approved_nodes=["*"]` covers all nodes that are **already in the safe allowlist**.
- GUI/manual nodes are explicitly **not** in the safe allowlist.
- Wildcard approval is a convenience for safe nodes, not a bypass for dangerous ones.

In the GUI Agent subsystem:

- `approved=true` is the GUI agent's own wildcard.
- It must be replaced with structured, semantic approval at all three layers.

---

## 4. Layer 1: Session-Level Approval

### 4.1 Session Declaration

A GUI session must declare its boundaries before creation. The session approval is a **boundary definition**, not an action authorization.

```python
# PROPOSED session schema (conceptual — not implemented in T002)
@dataclass
class GuiAgentSessionDeclaration:
    # Required
    target_application: str          # e.g. "MATLAB SPM12"
    target_window_title_regex: str   # e.g. "SPM.*"
    provider: str                    # "mock" | "pywinauto"
    
    # Scope
    allowed_action_tiers: list[int]  # e.g. [0, 1] — Tier 2/3 require separate contracts
    file_scope: list[str]            # e.g. ["outputs/work/"] — allowed directories
    read_only_file_scope: bool       # True = only read, no write
    
    # Policies
    screenshot_policy: str           # "disabled" | "ephemeral" | "scoped_redacted"
    clipboard_policy: str            # "disabled" | "read_only" | "write_only"
    network_policy: str              # "disabled" | "localhost_only"
    
    # Constraints
    duration_limit_seconds: int      # max session duration
    step_limit: int                  # max number of steps
    human_present: bool              # user must be at the machine
    emergency_abort_enabled: bool    # must be True for real providers
    
    # Context
    objective: str                   # human-readable goal
    reviewed_plan_id: str | None     # link to a reviewed execution plan (future)
    
    # Approval
    session_approval_id: str         # unique approval ID
    approved_by: str                 # who approved the session
    approved_at: str                 # ISO timestamp
```

### 4.2 Session Creation Flow

```text
1. User declares session scope (declaration above)
2. System validates declaration:
   a. target_application in APPLICATION_ALLOWLIST?
   b. provider allowed? (mock always; pywinauto only if feature flag + contract)
   c. action tiers within provider capability?
   d. file_scope within ALLOWED_WRITE_DIRS?
   e. screenshot/clipboard/network policy consistent?
3. System generates session_id
4. Session stored with status: "DECLARED" (not yet approved for action)
5. User reviews and confirms: semantic confirmation required
6. Session status → "APPROVED_SESSION" (ready for action-plan approval)
```

### 4.3 Provider-Based Defaults

| Provider | Default Action Tiers | Screenshot | Clipboard | Network | Human Present |
|---|---|---|---|---|---|
| `mock` | [0, 1, 2] (all safe for mock) | ephemeral | disabled | disabled | not required |
| `pywinauto` | [0] only | disabled | disabled | disabled | **required** |
| future `browser` | [0] only | disabled | disabled | disabled | **required** |

### 4.4 Session Approval Does NOT Authorize

A session approval:

- ✅ Defines **what application** can be targeted
- ✅ Defines **what provider** is used
- ✅ Defines **what file directories** are in scope
- ✅ Defines **what screenshot/clipboard/network policies** apply
- ❌ Does **NOT** authorize any specific action
- ❌ Does **NOT** authorize click, type, submit, or save
- ❌ Does **NOT** authorize Tier 2 or Tier 3 actions
- ❌ Does **NOT** authorize real desktop control (additional gates required)

---

## 5. Layer 2: Action-Plan Approval

### 5.1 Action Plan Concept

Before any step executes, the user must review and approve the **entire action plan**. This is the semantic bridge between "I want to inspect SPM batch editor" and the concrete sequence of GUI operations.

### 5.2 Action Plan Schema

```python
# PROPOSED action plan schema
@dataclass
class GuiActionPlan:
    session_id: str
    plan_id: str
    
    # What
    target_application: str
    target_window: str
    provider: str
    
    # Action sequence
    steps: list[GuiActionPlanStep]
    
    # Side effects
    files_read: list[str]
    files_written: list[str]
    files_deleted: list[str]
    screenshots_captured: int
    clipboard_accessed: bool
    network_accessed: bool
    external_apps_launched: list[str]
    
    # Safety
    rollback_plan: str               # e.g. "No writes planned — no rollback needed"
    stop_condition: str              # e.g. "Stop if SPM permission dialog appears"
    max_duration_seconds: int
    emergency_abort_available: bool
    
    # Approval
    plan_approval_id: str
    approved_by: str
    approved_at: str
    plan_hash: str                   # SHA256 of plan content
```

### 5.3 Action Plan Step Schema

```python
@dataclass
class GuiActionPlanStep:
    step_index: int
    action: str                      # action name
    action_tier: int                 # 0-3
    parameters: dict[str, Any]       # action parameters
    
    # Semantic description for user
    human_readable: str              # e.g. "Will focus the SPM batch editor window"
    expected_side_effect: str        # e.g. "No side effects (read-only)"
    
    # Files
    files_touched: list[str]
    
    # Screenshot
    screenshot_captured: bool
    screenshot_redacted: bool
```

### 5.4 Semantic Confirmation

The user confirmation MUST be semantic, not a boolean. Examples:

| ❌ Insufficient | ✅ Sufficient |
|---|---|
| `approved=true` | "I approve observing the SPM Batch Editor window (Tier 0, read-only, no file writes, no clicks)." |
| `confirm=ok` | "I approve clicking File → Open in SPM, limited to `outputs/work/` directory. I understand this will open a file dialog." |
| `submit` | "I approve filling the FWHM field with value [4,4,4] in the SPM Smooth dialog for subject sub-001. No Run/Execute will be triggered." |

### 5.5 Action-Plan Approval Flow

```text
1. System assembles action plan from session declaration + requested steps
2. System classifies each step by tier (0-3)
3. System validates:
   a. All steps within session's allowed_action_tiers?
   b. All file paths within session's file_scope?
   c. Provider can execute all actions?
4. System generates human_readable plan summary
5. User reviews plan (natural language + structured list)
6. User provides semantic confirmation
7. Plan stored with status: "APPROVED_PLAN"
8. Plan hash recorded for audit
9. Execution begins (subject to per-action confirmation for Tier 2/3)
```

---

## 6. Layer 3: Per-Action Confirmation

### 6.1 When Per-Action Confirmation is Required

| Action Tier | Confirmation | Notes |
|:---:|:---:|---|
| Tier 0 | Session approval sufficient | Read-only observation |
| Tier 1 | Action-plan approval sufficient | Low-risk navigation within declared window |
| Tier 2 | **Per-action confirmation required** | Medium-risk interaction |
| Tier 3 | **Blocked by default** | Requires separate safety contract before any execution |

### 6.2 Per-Action Confirmation Flow

```text
Before each Tier 2 action:
1. System pauses before the action
2. System presents:
   - What action will be performed
   - What file/path/control will be affected
   - What is the expected side effect
   - Whether a screenshot will be captured
3. User confirms: "I approve this specific action"
4. Action executes
5. Result recorded

If user denies:
- Action skipped
- Session continues to next step
- Denial logged in audit

After N consecutive denials:
- Session aborted (suspicious pattern)
```

### 6.3 Per-Action Confirmation Examples

| Action | Tier | Confirmation Prompt |
|---|---|---|
| `fill form fields` (FWHM=4) | 2 | "Approve filling FWHM field with [4,4,4] in SPM Smooth dialog? (No Run will be clicked.)" |
| `menu_select` (File → Open) | 2 | "Approve opening File → Open menu in SPM? This will show a file dialog within `outputs/work/`." |
| `screenshot` (unredacted, scoped) | 2 | "Approve capturing screenshot of SPM Results window? Screenshot will be redacted before storage." |
| `click Run` | 3 | **BLOCKED** — requires Tier 3 safety contract |
| `save file` | 3 | **BLOCKED** — requires Tier 3 safety contract |

### 6.4 Per-Action Confirmation Must Be Semantic

| ❌ Insufficient | ✅ Sufficient |
|---|---|
| "Continue?" | "Step 3 of 5: Agent will type '4' into the FWHM X field in SPM Smooth dialog. No other windows will be affected. Confirm?" |
| `step_approved=true` | "I approve step 3: type FWHM=[4,4,4] into SPM Smooth dialog. I understand this modifies a form field but does NOT submit or run anything." |

---

## 7. Action Tier to Approval Mapping

### 7.1 Complete Mapping Table

```
┌──────────┬──────────────────────────────┬──────────────────────────────────────────────────────┐
│ TIER     │ ACTION EXAMPLES              │ APPROVAL REQUIRED                                     │
├──────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
│          │                              │                                                      │
│ TIER 0   │ screenshot (redacted)        │ Session approval + action-plan approval               │
│ READ-ONLY│ window_title read            │ No per-action confirmation                            │
│          │ record_observation           │ Screenshot storage: disabled by default               │
│          │ visible_ui_state query       │ Redaction required before any persistence             │
│          │                              │                                                      │
│          │ Policy:                      │                                                      │
│          │ - Allowed only with session  │                                                      │
│          │   approval                   │                                                      │
│          │ - Screenshot storage         │                                                      │
│          │   disabled by default        │                                                      │
│          │ - Redaction required before  │                                                      │
│          │   persistence                │                                                      │
├──────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
│          │                              │                                                      │
│ TIER 1   │ focus window                 │ Session + action-plan approval                        │
│ LOW-RISK │ scroll                       │ No per-action confirmation                            │
│ NAV      │ switch tabs                  │ Must operate within declared target window/app         │
│          │ open non-sensitive panel     │ Action log required                                    │
│          │ wait                         │ No file writes                                         │
│          │ locate_window                │                                                      │
│          │                              │                                                      │
│          │ Policy:                      │                                                      │
│          │ - Allowed only within        │                                                      │
│          │   declared target window     │                                                      │
│          │ - Action log required        │                                                      │
│          │ - No file writes             │                                                      │
├──────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
│          │                              │                                                      │
│ TIER 2   │ fill form fields             │ Session + action-plan + PER-ACTION confirmation       │
│ MED-RISK │ select files under scoped    │ Each action confirmed individually                     │
│ INTERACT │   directory                  │ File scope validated against session boundary          │
│          │ trigger dry-run only         │ May be combined into logical groups if user prefers    │
│          │ menu_select (read-only path) │ Screenshot policy: per-step opt-in                     │
│          │ screenshot (unredacted,      │                                                      │
│          │   scoped)                    │                                                      │
│          │                              │                                                      │
│          │ Policy:                      │                                                      │
│          │ - Requires action-plan       │                                                      │
│          │   approval                   │                                                      │
│          │ - May require per-action     │                                                      │
│          │   confirmation depending on  │                                                      │
│          │   side effects               │                                                      │
├──────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
│          │                              │                                                      │
│ TIER 3   │ click Run / Execute / Submit │ BLOCKED BY DEFAULT                                     │
│ HIGH-    │ save / overwrite files       │ Requires separate Tier 3 safety contract               │
│ RISK     │ delete files                 │ Requires per-action confirmation (if ever opened)       │
│ BLOCKED  │ open rawdata                 │ Must not be reachable via wildcard approval             │
│          │ launch external app with     │ Executor NOT called unless contract satisfied           │
│          │   user data                  │                                                      │
│          │ upload / download files      │                                                      │
│          │ network submission           │                                                      │
│          │ accept license / security /  │                                                      │
│          │   permission dialogs         │                                                      │
│          │ install software             │                                                      │
│          │ enter credentials            │                                                      │
│          │ send email / message         │                                                      │
│          │ type_text with credentials   │                                                      │
│          │ access clipboard             │                                                      │
│          │                              │                                                      │
│          │ Policy:                      │                                                      │
│          │ - Requires separate contract │                                                      │
│          │   before implementation      │                                                      │
│          │ - Requires per-action        │                                                      │
│          │   confirmation               │                                                      │
│          │ - Credential/email/message   │                                                      │
│          │   actions PERMANENTLY BLOCKED│                                                      │
│          │ - Rawdata access PERMANENTLY │                                                      │
│          │   BLOCKED                    │                                                      │
└──────────┴──────────────────────────────┴──────────────────────────────────────────────────────┘
```

---

## 8. Provider Policy

### 8.1 Mock Provider (`MockGuiProvider`)

| Property | Value |
|---|---|
| Default | **Yes** — always available |
| Desktop control | **No** — records intent only |
| Screenshot output | `.txt` placeholder |
| CI safe | **Yes** |
| Requires approval | Session-level only (no real risk) |
| Action tiers allowed | All tiers (since no real execution) |
| Test usage | Full test suite, dry-run, CI |

**Policy**: Mock provider is the default for all environments. It does not control the desktop. No real execution occurs. It serves as a **recording and testing tool** for GUI action plans.

### 8.2 Real Desktop Provider (`PyWinAutoGuiProvider`)

| Property | Value |
|---|---|
| Default | **No** — must be explicitly enabled |
| Desktop control | **Yes** — click, type_text, menu_select, screenshot |
| Screenshot output | Real `.png` pixels |
| CI safe | **No** — must be skipped |
| Minimum approval | Session + action-plan + per-action (Tier 2+) |
| Action tiers allowed | Tier 0 only by default; Tier 2 requires contract |
| `approved=true` sufficient? | **No** — three-layer approval required |

**Policy**: PyWinAuto is **disabled by default** and must never execute without:

1. **Feature flag**: `MEDIMAGE_GUI_REAL_DESKTOP_ENABLED=1` (separate from `MEDIMAGE_ENABLE_REVIEWED_EXECUTION`)
2. **Local-only execution**: No remote/CI/container execution
3. **Human-present flag**: `human_present=true` in session declaration
4. **Session declaration approval**: Defined scope, limited duration, limited steps
5. **Action-plan approval**: Full step-by-step semantic review
6. **Per-action confirmation**: Every Tier 2+ action confirmed individually
7. **Emergency abort**: Registered and available at every step
8. **Audit logging**: Every action, screenshot, and result recorded

### 8.3 Provider Enablement Gates

```text
┌─────────────────────────────────────────────────────────────────┐
│  GATE                              │ MOCK   │ PYWINAUTO         │
├────────────────────────────────────┼────────┼───────────────────┤
│ Provider available                 │ Always │ Import check       │
│ Feature flag                       │ N/A    │ GUI_REAL_DESKTOP   │
│ Session declaration                │ Basic  │ Full declaration   │
│ Action-plan approval               │ Basic  │ Full semantic      │
│ Per-action confirmation (Tier 2+)  │ Skip   │ Required           │
│ Human present                      │ Skip   │ Required           │
│ Emergency abort                    │ Skip   │ Required           │
│ Audit log                          │ Basic  │ Full               │
│ Screenshot redaction               │ N/A    │ Required           │
│ CI execution                       │ Yes    │ Never               │
│ Remote execution                   │ Yes    │ Never               │
└────────────────────────────────────┴────────┴───────────────────┘
```

---

## 9. `/api/gui-agent/*` Safety Integration Design

### 9.1 Problem Statement

The current `/api/gui-agent/*` endpoints call `gui_agent.py` functions directly without going through the 12-gate reviewed execution pipeline. Two integration approaches exist.

### 9.2 Option A — Route GUI Agent Through Reviewed Execution

**Description**: Convert GUI sessions into reviewed execution plans. Each GUI step becomes a reviewed execution node. The existing `plan_validator → approval_gate → plan_adapter → execute_reviewed` pipeline gates every action.

```
POST /api/plans/execute-reviewed  (with gui_* nodes)
  → plan_validator  (validates gui_* nodes against catalog)
  → approval_gate   (checks manual_required, node approval)
  → plan_adapter    (classifies gui_* → blocked_gui_nodes unless sandbox contract satisfied)
  → execute_reviewed (preflight + gated execution)
    → calls gui_agent session runner
```

| Pros | Cons |
|---|---|
| Reuses existing 12-gate infrastructure | GUI sessions are interactive and long-lived |
| Consistent audit behavior | Reviewed execution is designed for batch pipelines, not interactive sessions |
| `executor_called=false` semantics available | Session lifecycle (create → step → step → abort) doesn't map cleanly to DAG nodes |
| Policy checks centralized | Per-action confirmation not part of the DAG model |

**Verdict**: Attractive for **batch GUI actions** (e.g., "run SPM batch for all subjects"), but incomplete for **interactive GUI sessions** (e.g., "explore results in SPM viewer"). Both use cases exist.

### 9.3 Option B — Keep GUI Agent API Separate with Equivalent 12-Gate Guard

**Description**: Keep `/api/gui-agent/*` as a standalone API but add a middleware/pre-check layer that applies the same 12-gate logic at the session and step level.

```text
POST /api/gui-agent/sessions
  → Gate 1: Session declaration validation
  → Gate 2: Provider policy validation
  → Gate 3: Application allowlist check
  → Gate 4: create_gui_agent_session()

POST /api/gui-agent/sessions/{id}/step
  → Gate 5: Session status check (not ABORTED, not EXPIRED)
  → Gate 6: Action tier classification
  → Gate 7: Tier 2/3 per-action confirmation check
  → Gate 8: File scope validation
  → Gate 9: Screenshot/clipboard/network policy validation
  → Gate 10: Audit log creation
  → Gate 11: Emergency abort registration
  → Gate 12: step_gui_agent_session()
```

| Pros | Cons |
|---|---|
| Fits interactive session model | Duplicates gate logic across two API surfaces |
| Per-step confirmation natural fit | Audit trail split between two systems |
| Session lifecycle maintained | Risk of gate divergence over time |
| Can add HITL-specific gates not in reviewed execution | — |

**Verdict**: Better fit for interactive GUI sessions. The gates are logically equivalent to the reviewed execution gates but adapted for the session/step lifecycle.

### 9.4 Recommended Approach: Hybrid (Option B with Reviewed Execution Bridge)

```
┌──────────────────────────────────────────────────────────────────┐
│                      RECOMMENDED ARCHITECTURE                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Batch GUI actions (future M9-T005+):                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ gui_* nodes in reviewed execution plan                    │   │
│  │   → plan_validator → approval_gate → plan_adapter        │   │
│  │   → execute_reviewed → gui_session_runner()              │   │
│  │   (reuses 12-gate infrastructure)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Interactive GUI sessions (future M9-T005+):                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ /api/gui-agent/* with equivalent 12-gate guard            │   │
│  │   → session declaration validation                       │   │
│  │   → provider policy validation                           │   │
│  │   → application allowlist check                          │   │
│  │   → action tier classification                           │   │
│  │   → per-action confirmation                              │   │
│  │   → file scope validation                                │   │
│  │   → screenshot/clipboard/network policy validation       │   │
│  │   → audit log creation                                   │   │
│  │   → emergency abort registration                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Shared:                                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - GuiSafetyGuard module (reusable across both paths)      │   │
│  │ - GuiAuditRecord module (linked to audit_record.py)       │   │
│  │ - GuiActionTaxonomy module (tier classification shared)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 9.5 Immediate Recommendation (T002)

```text
Until an equivalent guard exists for /api/gui-agent/*:
  1. Keep provider default as "mock"
  2. Add feature flag MEDIMAGE_GUI_REAL_DESKTOP_ENABLED (default 0)
  3. API returns 403 if real provider requested but flag is 0
  4. Document that real desktop control requires full HITL implementation
  5. Do NOT remove or disable the API — mock provider is useful for testing
```

### 9.6 Gate Equivalence Table

| Reviewed Execution Gate | GUI Agent Equivalent Gate |
|---|---|
| `MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1` | `MEDIMAGE_GUI_REAL_DESKTOP_ENABLED=1` |
| `confirm_execution=true` | `session_approval_id` + `plan_approval_id` |
| `persist_audit=true` | `audit_log_created` per step |
| `ProjectSettings.validate()` | Session declaration validation |
| `validate_plan(plan).ok` | `validate_session_declaration()` |
| `check_approval_gate()` | `check_gui_approval()` |
| `adapt_reviewed_plan()` | `classify_gui_action_plan()` |
| `_check_safe_allowlist()` | `check_provider_policy()` + `check_action_tiers()` |
| `pipeline_writer.write()` | `_write_session()` (already exists) |
| `build_review_audit_record()` | `build_gui_audit_record()` |
| `run_pipeline()` | `step_gui_agent_session()` |

---

## 10. Human-in-the-Loop UI Requirements

### 10.1 Session Creation UI

The user must see:

| Element | Content |
|---|---|
| Target application | "MATLAB SPM12" (with icon if available) |
| Provider | "Mock (safe, no desktop control)" or "PyWinAuto (REAL DESKTOP CONTROL ⚠️)" |
| Provider warning | If real provider: "⚠️ This will control your real desktop. Actions CANNOT be easily undone." |
| Allowed actions | "Tier 0-1 only" or "Tier 0-2 with per-action confirmation" |
| File scope | "Read: outputs/work/ | Write: outputs/work/ (sandbox only)" |
| Duration limit | "Max 5 minutes" |
| Step limit | "Max 50 steps" |
| Screenshot policy | "Disabled" / "Ephemeral (auto-deleted)" / "Scoped + redacted" |
| Objective | "Inspect SPM batch editor for subject sub-001" |
| **Confirm button** | **"I approve this GUI session scope"** (NOT "OK" or "Continue") |

### 10.2 Action Plan Review UI

The user must see:

| Element | Content |
|---|---|
| Step list | Numbered, each with `human_readable` description |
| Per-step tier badge | 🟢 Tier 0 / 🟡 Tier 1 / 🟠 Tier 2 / 🔴 Tier 3 |
| Files touched | List of input/output paths per step |
| Side effects summary | "Total: 0 file writes, 3 screenshots (redacted), 0 clipboard access" |
| Estimated duration | "~45 seconds" |
| Stop condition | "Stops if SPM shows any dialog or error message" |
| Abort button | **Visible and enabled at all times** |
| **Confirm button** | **"I have reviewed all 5 steps and approve this action plan"** |

### 10.3 Per-Action Confirmation UI

Before each Tier 2 action:

| Element | Content |
|---|---|
| Current step | "Step 3 of 5: Fill FWHM field" |
| Description | "Will type '4' into FWHM X field in SPM Smooth dialog" |
| Warning (if applicable) | "This modifies a form field but does NOT submit" |
| **Confirm** | **"I approve step 3: fill FWHM=[4,4,4]"** |
| **Skip** | "Skip this step and continue" |
| **Abort session** | "Stop all GUI actions immediately" |

### 10.4 Emergency Abort UI

| Element | Content |
|---|---|
| Always visible | Red "ABORT" button in corner of GUI session panel |
| Effect | Immediately stops all GUI actions |
| Confirmation | Immediate — no "are you sure?" for abort |
| Post-abort | Session status → ABORTED, audit record written, clean close |

### 10.5 Anti-Patterns (What NOT to Show)

| ❌ Anti-Pattern | ✅ Correct |
|---|---|
| "Continue" button | "I approve step 3: type FWHM=[4,4,4] into SPM Smooth dialog" |
| `approved=true` toggle | Structured declaration with semantic confirmation |
| "Run all" without review | Step-by-step review required |
| Hidden abort button | Always-visible red ABORT button |
| "OK" dialog | Contextual confirmation with specific action description |
| Progress bar without details | Step list with human-readable descriptions |

---

## 11. Sensitive Data / Screenshot / Clipboard Policy

### 11.1 Screenshot Policy

| Tier | Policy | Storage | Redaction |
|---|---|---|---|
| Default | **Disabled** | — | — |
| Ephemeral | Captured but auto-deleted after session close | Memory only | N/A |
| Scoped + Redacted | Captured, redacted, stored | `outputs/work/gui_agent/sessions/{id}/screenshots/` (encrypted or access-controlled) | Black-bar: text regions, paths, subject IDs, window titles containing PII |

**Screenshot rules**:

- Screenshots are **disabled by default** for all providers.
- Screenshot capture requires explicit opt-in at session declaration.
- Real provider screenshots require `screenshot_policy: "scoped_redacted"` in session declaration.
- All screenshots must be redacted before persistence. Redaction must cover:
  - Subject IDs and patient names
  - File paths outside the declared scope
  - MATLAB command window text that may contain data paths
  - Any visible credentials, tokens, or API keys
- Screenshots must not be stored if redaction fails.
- Screenshot retention: auto-delete after audit review or session close (configurable).

### 11.2 Clipboard Policy

| Policy | Description |
|---|---|
| `disabled` | **(Default)** No clipboard access permitted |
| `read_only` | Can read clipboard text only (requires per-action confirmation) |
| `write_only` | Can write to clipboard only (requires per-action confirmation) |

**Clipboard rules**:

- Clipboard access is **disabled by default**.
- No clipboard access for credential transfer.
- Clipboard read content must be logged (redacted) in audit trail.
- Clipboard write content must be validated against session scope.

### 11.3 Credential Boundary

| Rule | Enforcement Point |
|---|---|
| `type_text` must not contain passwords/tokens | Pre-action validation at `step_gui_agent_session()` |
| Screenshots must not capture password fields | Redaction before storage |
| Session JSON must not contain secrets in plaintext | `_write_session()` secret filter |
| Audit logs must not contain secrets | Log scrubbing filter |
| No clipboard credential transfer | Clipboard access disabled by default |
| No `MEDIMAGE_*_API_KEY` in session parameters | Environment variable filter |

### 11.4 File Path Policy

| Scope | Rule |
|---|---|
| Read | Only files within declared `file_scope` |
| Write | Only files within declared `file_scope` AND `ALLOWED_WRITE_DIRS` |
| Rawdata | **Permanently blocked** — never readable or writable |
| Derivatives | Only within `outputs/work/` sandbox |
| External paths | Blocked unless explicitly declared and approved |
| Path traversal | `..`, absolute paths, symlinks validated |

---

## 12. Audit Log Requirements

### 12.1 Per-Session Audit

| Field | Source |
|---|---|
| `session_id` | From session creation |
| `created_at` | ISO timestamp |
| `provider` | `mock` | `pywinauto` |
| `target_app` | Session declaration |
| `target_window` | Session declaration |
| `objective` | Session declaration |
| `session_approval_id` | From session approval |
| `approved_by` | User identifier |
| `approved_at` | ISO timestamp |
| `session_status` | `DECLARED` / `APPROVED_SESSION` / `RUNNING` / `ABORTED` / `COMPLETED` |
| `duration_seconds` | End time - start time |
| `total_steps` | Count of steps executed |
| `screenshots_captured` | Count |
| `errors` | List of error messages |

### 12.2 Per-Step Audit

| Field | Source |
|---|---|
| `session_id` | Session |
| `step_index` | Step sequence number |
| `action` | Action name |
| `action_tier` | 0-3 |
| `parameters` | Action parameters (redacted) |
| `plan_approval_id` | From action-plan approval |
| `per_action_approved` | `true` | `false` | `not_required` |
| `per_action_approval_id` | If Tier 2 confirmed |
| `executed` | Did the provider execute it |
| `provider_status` | `EXECUTED` | `MOCK_RECORDED` | `FAILED` |
| `files_read` | List (within scope only) |
| `files_written` | List (within scope only) |
| `screenshot_captured` | Boolean |
| `screenshot_redacted` | Boolean |
| `clipboard_accessed` | Boolean |
| `network_accessed` | Boolean |
| `result` | Step outcome |
| `error` | Error message if failed |
| `timestamp` | ISO timestamp |

### 12.3 Audit Record Integration

Future implementation should integrate with the existing `audit_record.py` module:

```python
# Proposed (not implemented in T002)
from src.backend.app.planner.audit_record import build_review_audit_record

# GUI sessions produce audit records with:
# - event_type: "gui_session_created" | "gui_step_executed" | "gui_session_aborted"
# - plan_hash → session_hash
# - audit_id → gui_audit_id
# - Linked to reviewed execution audit via reviewed_plan_id
```

### 12.4 Audit Storage

- Audit records stored alongside session data: `outputs/work/gui_agent/sessions/{id}/audit.json`
- Also written to centralized audit directory: `outputs/reports/audit_records/gui_{session_id}_{timestamp}.json`
- Read-only after write (append-only log per step)
- SHA256 hash of audit record for integrity verification

---

## 13. Emergency Abort and Stop Conditions

### 13.1 Emergency Abort

```text
TRIGGERS:
  - User clicks "ABORT" button in UI
  - POST /api/gui-agent/sessions/{id}/abort called
  - Session duration exceeds declared limit
  - Step count exceeds declared limit
  - Tier 3 action attempted without contract
  - Credential field detected in target window
  - Permission/security dialog detected
  - Unexpected window appears (not declared target_app)
  - File dialog navigates outside declared file_scope
  - Network/upload dialog detected
  - Rawdata path appears in window title or file dialog
  - Screenshot redaction fails
  - Clipboard access attempted without policy approval

EFFECT:
  - All pending actions cancelled
  - Session status → ABORTED
  - Audit record written with abort reason
  - Provider disconnected (if real)
  - No automatic retry
```

### 13.2 Stop Conditions (Auto-Pause)

```text
TRIGGERS:
  - Permission dialog detected by window title heuristics
  - Error dialog detected
  - "Save changes?" dialog detected
  - License agreement dialog detected
  - Credential prompt detected

EFFECT:
  - Session PAUSED (not aborted)
  - User notified: "GUI session paused — {dialog_type} detected in {window_title}"
  - User decides: ABORT or OVERRIDE (with explicit confirmation)
  - Override logged in audit
```

### 13.3 Session Limits

| Limit | Default | Source |
|---|---|---|
| Max duration | 300s (5 min) | Session declaration |
| Max steps | 50 | Session declaration |
| Max screenshots | 20 | Configurable |
| Max file writes | 10 | Configurable |
| `type_text` max length | 256 chars | Hard-coded |

Limits are enforced at `step_gui_agent_session()` — if exceeded, the session is auto-aborted.

---

## 14. Prompt Injection / UI Injection Controls

### 14.1 Threat

GUI content is untrusted. Text visible in any application window, dialog, terminal, browser, or log viewer can contain instructions that look like valid agent commands.

### 14.2 Controls

| Control | Implementation |
|---|---|
| Agent follows **plan only** | Never derives next action from UI content — always from approved action plan |
| UI text is **observation only** | Window titles, control labels, and text content are read for audit but never become instructions |
| No `eval` of UI text | Text read from windows is treated as data, never as code |
| Action whitelist | Only approved actions in the catalog can execute; UI text can't introduce new actions |
| Parameter validation | All action parameters validated against declared types and ranges; UI text can't bypass |
| Session scope lock | `target_app` and `target_window` are set at session creation; agent cannot follow UI to a different application |
| Audit comparison | Post-session, compare approved plan with actual executed steps; deviations flagged |

### 14.3 Explicit Prohibition

```text
The agent MUST NOT:
  - Follow instructions found in screenshots
  - Follow instructions found in window text
  - Follow instructions found in webpages (if browser target)
  - Follow instructions found in terminal output, logs, notebooks, PDFs
  - Change its objective based on UI content
  - Navigate to a different application based on UI content
  - Execute a different action than the one in the approved plan
  - Accept commands embedded in file names or dialog text
```

---

## 15. Rollback / Cleanup Policy

### 15.1 Principle

GUI actions are not trivially reversible (unlike file operations). There is no "undo" for a mouse click.

### 15.2 Design

| Phase | Policy |
|---|---|
| **Before action** | Prefer dry-run / observation-only steps |
| **Tier 0-1** | No writes — no rollback needed |
| **Tier 2** | Prefer form fills (reversible by clearing fields) over clicks |
| **Tier 3** | Require explicit rollback plan in safety contract |
| **Post-session** | Clean up temporary files, screenshots per retention policy |
| **Failed session** | Revert any written files (if tracked), abort remaining steps |

### 15.3 Cleanup

```text
On session close (normal or abort):
  - Ephemeral screenshots: DELETED
  - Scoped screenshots: retained per policy
  - Session JSON: retained for audit (redacted)
  - Temporary files: DELETED
  - Provider connection: CLOSED
```

---

## 16. Approval Schema Proposal

### 16.1 Session Approval Schema

```json
{
  "session_approval_id": "gui_approval_a1b2c3d4",
  "session_id": "gui_e5f6g7h8",
  "approved_by": "researcher@lab",
  "approved_at": "2026-07-11T12:00:00Z",
  "approval_type": "session_declaration",
  "declaration": {
    "target_application": "MATLAB SPM12",
    "target_window_title_regex": "SPM.*",
    "provider": "mock",
    "allowed_action_tiers": [0, 1],
    "file_scope": ["outputs/work/sandbox/"],
    "screenshot_policy": "disabled",
    "clipboard_policy": "disabled",
    "network_policy": "disabled",
    "duration_limit_seconds": 300,
    "step_limit": 50,
    "human_present": false
  },
  "approval_hash": "sha256:abc123..."
}
```

### 16.2 Action-Plan Approval Schema

```json
{
  "plan_approval_id": "gui_plan_approval_x1y2z3",
  "session_id": "gui_e5f6g7h8",
  "session_approval_id": "gui_approval_a1b2c3d4",
  "approved_by": "researcher@lab",
  "approved_at": "2026-07-11T12:01:00Z",
  "approval_type": "action_plan",
  "plan_hash": "sha256:def456...",
  "plan": {
    "steps": [
      {
        "step_index": 1,
        "action": "locate_window",
        "action_tier": 1,
        "human_readable": "Will locate and focus the SPM batch editor window",
        "parameters": {"window_title": "SPM.*"}
      },
      {
        "step_index": 2,
        "action": "record_observation",
        "action_tier": 0,
        "human_readable": "Will observe the current state of the SPM batch editor (read-only)",
        "parameters": {}
      }
    ],
    "files_read": [],
    "files_written": [],
    "screenshots_captured": 0,
    "total_duration_estimate_seconds": 10
  },
  "semantic_confirmation": "I approve observing the SPM batch editor window. Read-only, no clicks, no file writes.",
  "approval_hash": "sha256:ghi789..."
}
```

### 16.3 Per-Action Confirmation Schema

```json
{
  "per_action_approval_id": "gui_step_approval_s3",
  "session_id": "gui_e5f6g7h8",
  "plan_approval_id": "gui_plan_approval_x1y2z3",
  "step_index": 3,
  "action": "fill_form_fields",
  "action_tier": 2,
  "approved_by": "researcher@lab",
  "approved_at": "2026-07-11T12:02:00Z",
  "semantic_confirmation": "I approve step 3: typing FWHM=[4,4,4] into the SPM Smooth dialog. I understand this modifies form fields but does NOT click Run.",
  "approval_hash": "sha256:jkl012..."
}
```

---

## 17. API Behavior Proposal

### 17.1 Current API (M9-GUI-T001 baseline)

```
GET  /api/gui-agent/sessions                        → list
POST /api/gui-agent/sessions                        → create (provider + approved bool)
POST /api/gui-agent/sessions/{id}/step              → execute step
GET  /api/gui-agent/sessions/{id}/screenshot        → capture screenshot
POST /api/gui-agent/sessions/{id}/abort             → abort
```

### 17.2 Proposed API (future M9-T004+)

```
# Session management
GET    /api/gui-agent/sessions                       → list (same)
POST   /api/gui-agent/sessions                       → create with session declaration (enhanced)
GET    /api/gui-agent/sessions/{id}                  → get session state
DELETE /api/gui-agent/sessions/{id}                  → close and cleanup

# Approval
POST   /api/gui-agent/sessions/{id}/approve-session   → Layer 1: approve session declaration
POST   /api/gui-agent/sessions/{id}/approve-plan      → Layer 2: approve action plan
POST   /api/gui-agent/sessions/{id}/steps/{n}/confirm → Layer 3: confirm a specific step

# Execution
POST   /api/gui-agent/sessions/{id}/step              → execute step (gated by approval layers)
POST   /api/gui-agent/sessions/{id}/run-plan          → execute all approved steps (batch)

# Observation
GET    /api/gui-agent/sessions/{id}/screenshot        → capture (gated by screenshot policy)

# Control
POST   /api/gui-agent/sessions/{id}/abort             → abort (same)
POST   /api/gui-agent/sessions/{id}/pause             → pause session
POST   /api/gui-agent/sessions/{id}/resume            → resume paused session

# Audit
GET    /api/gui-agent/sessions/{id}/audit              → get audit record
GET    /api/gui-agent/sessions/{id}/replay             → get replay script
```

### 17.3 Provider Validation in API

```python
# Proposed (not implemented in T002)
def _validate_provider(provider: str, session_declaration: dict) -> None:
    if provider == "mock":
        return  # always allowed
    
    if provider == "pywinauto":
        if not os.environ.get("MEDIMAGE_GUI_REAL_DESKTOP_ENABLED") == "1":
            raise HTTPException(403, "Real desktop provider disabled. "
                                      "Set MEDIMAGE_GUI_REAL_DESKTOP_ENABLED=1 to enable.")
        if not session_declaration.get("human_present"):
            raise HTTPException(400, "Real desktop provider requires human_present=true.")
        if not session_declaration.get("emergency_abort_enabled"):
            raise HTTPException(400, "Real desktop provider requires emergency_abort_enabled=true.")
        if session_declaration.get("allowed_action_tiers", []) != [0]:
            raise HTTPException(400, "Real desktop provider default action tier is [0] only. "
                                      "Higher tiers require a separate safety contract.")
```

---

## 18. Test Strategy

### 18.1 M9-GUI-T002 (This Task — Design Only)

No code changes. Run existing tests to confirm no regressions:

```bash
pytest --tb=short
npm --prefix src/frontend run build
```

### 18.2 M9-GUI-T004 (Future — Blocklist Tests)

Test categories:

```
1. GUI node blocking in plan_adapter
   - gui_* prefix → blocked_gui_nodes
   - backend="gui-agent" → blocked_gui_nodes
   - manual_required → blocked_manual_required_nodes

2. GUI node blocking in approval_gate
   - wildcard approved_nodes=["*"] does not cover gui_* nodes
   - manual_required_nodes → MANUAL_REQUIRED_NODE error
   - approved_backends=["gui"] alone is insufficient

3. GUI node blocking in execute_reviewed
   - executor_called=false for gui_* nodes
   - EXECUTION_POLICY_BLOCKED for blocked_gui_nodes
   - SPM/DPABI/GPU allowlists do not regress when GUI blocking is tested

4. Session declaration validation (unit)
   - Valid declaration passes
   - Missing target_app fails
   - Real provider without human_present fails
   - Invalid action tier fails

5. Provider policy (unit)
   - Mock provider always allowed
   - PyWinAuto disabled when feature flag is 0
   - PyWinAuto returns 403 without MEDIMAGE_GUI_REAL_DESKTOP_ENABLED

6. Action tier classification (unit)
   - All Tier 0 actions classified correctly
   - All Tier 1 actions classified correctly
   - All Tier 2 actions classified correctly
   - All Tier 3 actions classified correctly
   - Unknown action → Tier 3 (conservative)
```

---

## 19. Future M9 Rollout Plan

| Task | Content | Dependencies |
|---|---|---|
| **M9-GUI-T001** ✅ | GUI/manual node inventory and threat model | — |
| **M9-GUI-T002** ✅ | GUI/manual approval and HITL design (this doc) | T001 |
| **M9-GUI-T003** | GUI action taxonomy and sandbox declaration contract | T001, T002 |
| **M9-GUI-T004** | GUI/manual plan_adapter blocklist tests (code) | T001 |
| **M9-GUI-T005** | Read-only GUI observation contract, if safe | T002, T003 |
| **M9-GUI-T006** | Manual-only smoke guide, no automation | T002, T003, T004 |
| **M9-GUI-CLOSEOUT** | GUI/manual phase closeout | T001-T006 |

### 19.1 Detailed Future Task Descriptions

#### M9-GUI-T003: Action Taxonomy and Sandbox Contract

- Formalize the `GuiActionTaxonomy` module (tier classification logic)
- Design `GuiSandboxContract` schema (per-action-type safety constraints)
- Define `APPLICATION_ALLOWLIST` for GUI automation targets
- Define `ACTION_ALLOWLIST` with tier assignments
- Write contract validation logic

#### M9-GUI-T004: Plan Adapter Blocklist Tests

- Add `blocked_gui_nodes` tests to `test_plan_adapter.py`
- Add `blocked_manual_required_nodes` tests
- Add `gui-agent` backend tests
- Add wildcard approval tests
- Add `executor_called=false` tests
- Add SPM/DPABI/GPU regression tests

#### M9-GUI-T005: Read-Only GUI Observation Contract

- Design `GuiObservationContract` (Tier 0 only)
- Define screenshot lifecycle (ephemeral → redacted → stored)
- Design window title observation API
- Design observation audit trail
- Write contract tests

#### M9-GUI-T006: Manual Smoke Guide

- Document how to manually test mock GUI agent
- Document how to safely configure pywinauto for local testing
- Document emergency abort procedure
- Document screenshot review procedure

---

## 20. Acceptance Criteria for Any Future GUI/Manual Allowlist

Before any GUI/manual node or action enters any allowlist:

### 20.1 Design Complete

- [x] M9-GUI-T001: Threat model complete
- [x] M9-GUI-T002: Approval and HITL design complete (this doc)
- [ ] M9-GUI-T003: Action taxonomy formalized
- [ ] M9-GUI-T004: Blocklist tests written and passing
- [ ] M9-GUI-T005: Observation contract designed and tested
- [ ] M9-GUI-T006: Smoke guide written

### 20.2 Safety Gates Implemented

- [ ] Session declaration validation active
- [ ] Application allowlist enforced
- [ ] Provider policy enforced (mock always, pywinauto gated)
- [ ] Action tier classification active
- [ ] Per-action confirmation for Tier 2+ implemented
- [ ] Emergency abort functional
- [ ] Audit log integrated with `audit_record.py`
- [ ] Screenshot redaction functional
- [ ] Clipboard policy enforced
- [ ] Session limits enforced (duration, steps)
- [ ] Stop conditions active (dialog detection, credential detection)
- [ ] UI injection controls active (plan-locked, no UI-derived actions)
- [ ] `MEDIMAGE_GUI_REAL_DESKTOP_ENABLED` feature flag active

### 20.3 Tests Complete

- [ ] All blocklist tests passing (M9-GUI-T004)
- [ ] All session validation tests passing
- [ ] All provider policy tests passing
- [ ] All action tier tests passing
- [ ] All approval gate tests passing (no regression)
- [ ] All reviewed execution tests passing (SPM/DPABI/GPU still blocked)
- [ ] CI safe (mock only in CI)
- [ ] No real desktop provider tests in CI

### 20.4 Documentation Complete

- [ ] Threat model (T001)
- [ ] Approval/HITL design (T002)
- [ ] Action taxonomy (T003)
- [ ] Blocklist test coverage report (T004)
- [ ] Observation contract (T005)
- [ ] Manual smoke guide (T006)
- [ ] Updated CURRENT_STATE.md
- [ ] Updated NEXT_ACTIONS.md

---

## 21. References

| Document | Relationship |
|---|---|
| `docs/GUI_MANUAL_AGENT_THREAT_MODEL.md` | M9-GUI-T001 — threat model and inventory |
| `docs/CURRENT_STATE.md` | Current milestone status |
| `docs/NEXT_ACTIONS.md` | Next actions pointer |
| `docs/SAFE_REVIEWED_EXECUTION_DESIGN.md` | 14-condition preflight gate (model for GUI gates) |
| `docs/EXECUTION_INTEGRATION_DESIGN.md` | M5 execution integration |
| `src/backend/app/runtime/gui_agent.py` | GUI Agent runtime (current implementation) |
| `src/backend/app/api/gui_agent_routes.py` | GUI Agent API (current implementation) |
| `src/backend/app/planner/approval_gate.py` | Approval gate — model for GUI approval |
| `src/backend/app/planner/plan_adapter.py` | Node classification — model for GUI action classification |
| `src/backend/app/api/execute_reviewed_routes.py` | Gated execution — model for GUI session gating |
| `src/backend/app/planner/audit_record.py` | Audit record — integration target for GUI audit |
