# DICOM Public Execute Endpoint Design — Phase 4L-1

**Status:** Design review — NO implementation.
**Version:** v1.0-draft
**Date:** 2026-06-10
**Parent:** `docs/DICOM_CONVERSION_RELEASE_HARDENING.md` (Phase 4K-0 / 4L-0)

---

## 1. Purpose and Scope

This document defines the **Phase 4L-1 public DICOM-to-NIfTI conversion execute
endpoint design contract** for MedImage Agent.  It proposes endpoint routes,
request/response schemas, runtime gating conditions, environment flags, approval
requirements, rollback/failure policies, and test strategies.

**Binding constraint:** Phase 4L-1 is **design only**.  No endpoint is added.
No frontend execution UI is added.  Public user-data DICOM conversion remains
disabled.

---

## 2. Why This Phase Is Design-Only

1. **Policy gate, not technical gate.** 32/32 safety gates are met, but public
   enablement is a maintainer decision that cannot be automated.
2. **Prevent accidental exposure.** Separating design from implementation
   ensures every schema field, env flag, and gate condition is reviewed before
   any code reaches the execution path.
3. **Traceable sign-off.** The design contract is the artifact against which
   implementation (Phase 4L-2) will be verified.
4. **No runtime risk.** Schema-only modules and design documents cannot call
   dcm2niix, write NIfTI files, or modify rawdata.

---

## 3. Current v0.4.0-rc1 Safety Baseline

| Capability | Status |
|---|---|
| DICOM detection (FunRaw/T1Raw) | ✅ path-based, 1104 files validated |
| Conversion dry-run (6 mapping previews) | ✅ |
| Conversion preflight (read-only) | ✅ |
| Approval gate (17 preconditions) | ✅ schema + execution integration |
| Audit records (start/final) | ✅ integrated into execution path |
| Rawdata checksum (before/after) | ✅ snapshots + comparison |
| Rollback (dry-run / quarantine / delete) | ✅ 3 modes, 14 tests |
| Release readiness evaluation | ✅ schema + service + UI |
| Human release approval workflow | ✅ metadata-only, 25 tests |
| Internal FunRaw/T1Raw conversion smoke | ✅ 1104 DICOM, rawdata unchanged |
| Packaged GUI smoke | ✅ 15/15 checks |
| Public `/conversion/execute` endpoint | ❌ NOT PRESENT (verified 404) |
| Frontend "Run Conversion" button | ❌ NOT PRESENT (verified absent) |
| `MEDIMAGE_ALLOW_USER_DATA_CONVERSION=1` | ❌ NOT SET |
| `run_conversion_execute()` for normal users | ❌ BLOCKED |
| SPM/DPABI/MATLAB execution | ❌ DISABLED |
| Full preprocessing | ❌ DISABLED |
| Rawdata modification | ❌ PROHIBITED |

**Gate status:** 32/32 met, 0 partial, 0 missing.
**Decision:** FULL GO ELIGIBLE — REQUIRES FINAL HUMAN RELEASE APPROVAL.

---

## 4. Preconditions for Public Execution

Before the public `/conversion/execute` endpoint can be implemented (Phase 4L-2
or later), **all** of the following must be true:

1. Explicit maintainer sign-off recorded in commit message, PR review, or
   `PROJECT_STATE.md`.
2. `MEDIMAGE_ALLOW_USER_DATA_CONVERSION=1` set at the environment level.
3. Release approval record status is `"approved"` and not expired.
4. Release readiness report status is `"ready_for_human_release_review"`.
5. GO/NO-GO gates are 32/32 met.
6. Persisted approval/audit package exists for the target `conversion_run_id`.
7. Rawdata checksum-before snapshot exists.
8. Rollback plan exists.
9. Disk space passes the 1.5× multiplier check.
10. Output root is under the project directory and not under rawdata.
11. SPM/DPABI/MATLAB execution is disabled.
12. Full preprocessing is disabled.

**None of these preconditions are met in Phase 4L-1.**  They are documented
here as the gating contract for Phase 4L-2.

---

## 5. Required Maintainer Sign-Off

The following explicit sign-offs are required before Phase 4L-2 implementation:

- [ ] Maintainer confirms 32/32 gates remain met.
- [ ] Maintainer approves the proposed endpoint contract (this document).
- [ ] Maintainer approves the proposed request/response schemas.
- [ ] Maintainer approves the proposed env flag architecture.
- [ ] Maintainer sets `MEDIMAGE_ALLOW_USER_DATA_CONVERSION=1`.
- [ ] Maintainer sets `MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT=1`.
- [ ] Maintainer confirms rawdata remains read-only.
- [ ] Maintainer confirms SPM/DPABI/MATLAB remain disabled.
- [ ] Maintainer confirms full preprocessing remains disabled.
- [ ] Maintainer records approval in commit message: `Phase 4L-2: maintainer sign-off for public conversion execute endpoint`.

**No sign-offs are recorded in Phase 4L-1.**  This is the proposed list.

---

## 6. Required Environment Flags

The proposed public endpoint requires **all** of the following env flags set to `"1"`:

| Flag | Purpose |
|---|---|
| `MEDIMAGE_ALLOW_USER_DATA_CONVERSION=1` | **Master gate** — all public conversion disabled without this |
| `MEDIMAGE_ENABLE_DICOM_CONVERSION=1` | Enables DICOM conversion subsystem |
| `MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1` | Enables reviewed-plan execution path |
| `MEDIMAGE_ENABLE_REAL_PREPROCESSING=1` | Enables real (non-synthetic) preprocessing |
| `MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT=1` | **Endpoint-specific gate** — the endpoint returns 404 without this |
| `MEDIMAGE_MATLAB_ENABLED=1` | Required as a consistency check (MATLAB must NOT actually execute) |
| `MEDIMAGE_SPM_SMOKE_ENABLED=1` | Required as a consistency check (SPM must NOT actually execute) |

If **any** flag is missing, the endpoint returns `conversion_disabled_by_default=true`
and does not execute dcm2niix.

**In Phase 4L-1, none of these flags are set.  All default to absent/empty.**

---

## 7. Required Release Approval Record

The public endpoint must validate the following against the persisted
`release_approval_record.json`:

| Field | Required Value |
|---|---|
| `status` | `"approved"` |
| `approved_by` | Non-empty |
| `human_approval_statement` | Non-empty |
| `rawdata_readonly_acknowledged` | `true` |
| `no_clinical_use_acknowledged` | `true` |
| `rollback_acknowledged` | `true` |
| `approval_audit_acknowledged` | `true` |
| `public_endpoint_acknowledged` | `true` |
| `frontend_execute_acknowledged` | `true` |
| `spm_dpabi_matlab_disabled_acknowledged` | `true` |

If the record is missing, incomplete, expired (>180 days), or revoked, the
endpoint returns `status="blocked"` with `blocking_issues` describing the problem.

---

## 8. Required Release Readiness Report

Before execution, the endpoint calls `evaluate_conversion_release_readiness()`
and validates:

| Field | Required Value |
|---|---|
| `status` | `"ready_for_human_release_review"` |
| `gates_met` | `32` |
| `gates_total` | `32` |
| `disk_space.ok` | `true` |
| `rollback_ready` | `true` |
| `approval_audit_ready` | `true` |
| `public_endpoint_enabled` | `false` (the endpoint gate is checked separately) |
| `frontend_execute_enabled` | `false` |
| `spm_dpabi_matlab_enabled` | `false` |
| `full_preprocessing_enabled` | `false` |

---

## 9. Required Approval/Audit Package

The endpoint reads the persisted review package and validates **all** required files:

```
conversion_runs/<conversion_run_id>/
├── approval_record.json              ← must exist
├── audit_preview.json                ← must exist
├── preflight_snapshot.json           ← must exist
├── mapping_snapshot.json             ← must exist
├── command_templates.json            ← must exist
├── rawdata_checksum_before.json      ← must exist
├── rollback_plan_dry_run.json        ← must exist
├── audit_execution_start.json        ← written at execution start
└── audit_execution_final.json        ← written at execution end
```

Template count must match mapping count.  Missing or mismatched → blocked.

---

## 10. Required Checksum Before/After Policy

1. **Pre-execution:** Load `rawdata_checksum_before.json` from the review package.
   Validate it has `ok=true`, non-zero `file_count`, non-empty `fingerprint`.
2. **Post-execution:** Run `build_post_conversion_rawdata_snapshot()` immediately
   after dcm2niix completes.  Compare with pre-execution snapshot via
   `compare_conversion_rawdata_snapshots()`.
3. **On checksum change:** Mark run `status="safety_violation"`.  Write
   `rawdata_checksum_after.json` and `rawdata_checksum_comparison.json`.
   **NEVER auto-recover.**  Block all downstream processing.
4. **On checksum unchanged:** Mark `checksum_verified=true` in the response.

---

## 11. Required Rollback Policy

The endpoint must reference the existing rollback plan (`rollback_plan_dry_run.json`)
and write a `rollback_result.json` on failure.

| Scenario | Rollback Behavior |
|---|---|
| Preflight fails | No rollback needed (no files written) |
| dcm2niix fails (non-zero exit) | Write `rollback_result.json`; preserve partial outputs; allow manual rollback |
| Checksum changed | Trigger automatic quarantine rollback; mark run `safety_violation` |
| Disk full | Stop immediately; quarantine partial outputs |
| User cancellation (future) | SIGTERM to dcm2niix; quarantine partial outputs |

Rollback modes from Phase 4J-0: `dry_run` (report only), `quarantine` (move),
`delete` (requires `confirm_rollback=True`).  Rawdata paths are **always protected**.

---

## 12. Endpoint Route Proposal

**Proposed route (NOT implemented in Phase 4L-1):**

```
POST /api/projects/{project_id}/conversion/execute
```

This route is **only** registered when `MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT=1`.
When the flag is absent, the route does not exist (returns 404).

**Do NOT** register additional routes:
- No `POST /api/projects/{project_id}/conversion/run`
- No `GET /api/projects/{project_id}/conversion/execute` (POST only)
- No `DELETE /api/projects/{project_id}/conversion/execute`

---

## 13. Request Schema Proposal

```python
# src/backend/app/schemas/dicom_conversion_public_execution.py

class DicomConversionPublicExecutionRequest(BaseModel):
    """Request submitted by an operator to execute public DICOM conversion."""

    # Required identifiers
    conversion_run_id: str            # Persisted conversion run ID
    release_approval_id: str          # Release approval record ID

    # Required operator confirmations (all must be True)
    confirm_user_data_conversion: bool = False
    confirm_rawdata_readonly: bool = False
    confirm_research_use_only: bool = False
    confirm_no_clinical_use: bool = False
    confirm_rollback_available: bool = False
    confirm_disk_space_checked: bool = False
    confirm_public_execution_risk: bool = False

    # Request metadata
    requested_by: str = ""            # Operator identity
    reason: str = ""                  # Free-text reason for conversion

    # Execution options
    dry_run_first: bool = True        # Default: dry-run before real execution
    rollback_mode_on_failure: str = "quarantine"  # dry_run / quarantine / delete
```

**All confirm_* fields must be `True`** — missing any one blocks execution.

---

## 14. Response Schema Proposal

```python
class DicomConversionPublicExecutionResponse(BaseModel):
    """Response returned after public DICOM conversion execution."""

    ok: bool
    status: str                       # succeeded / warning / failed / blocked / safety_violation
    project_id: str
    conversion_run_id: str
    execution_id: str                 # New unique execution ID
    started_at: str | None
    finished_at: str | None
    output_root: str
    output_manifest_path: str | None
    execution_provenance_path: str | None
    audit_execution_start_path: str | None
    audit_execution_final_path: str | None
    checksum_before_path: str | None
    checksum_after_path: str | None
    checksum_comparison_path: str | None
    checksum_verified: bool
    rollback_plan_path: str | None
    rollback_result_path: str | None
    warnings: list[str]
    errors: list[str]
    blocking_issues: list[str]
    safety_flags: DicomConversionPublicExecutionSafetyFlags
```

---

## 15. Safety Flags

```python
class DicomConversionPublicExecutionSafetyFlags(BaseModel):
    """Safety flags returned with every conversion execute response."""

    conversion_disabled_by_default: bool = True  # True if any gate blocked
    env_flags_missing: bool = True               # True if not all env flags are "1"
    public_execution_allowed: bool = False       # True only when all gates pass
    release_approval_obtained: bool = False
    release_readiness_ready: bool = False
    gates_32_of_32: bool = False
    approval_audit_package_present: bool = False
    rawdata_checksum_before_exists: bool = False
    rollback_plan_exists: bool = False
    disk_space_passed: bool = False
    output_root_safe: bool = False
    rawdata_read_only: bool = True
    spm_dpabi_matlab_disabled: bool = True
    full_preprocessing_disabled: bool = True
    human_release_approval_required: bool = True
    no_shell_execution: bool = True
```

---

## 16. Failure Behavior

| Failure Type | HTTP Status | Response Status | Audit Written |
|---|---|---|---|
| Missing env flags | 200 (blocked) | `disabled` | No |
| Release approval missing/expired | 200 (blocked) | `blocked` | No |
| Release readiness not ready | 200 (blocked) | `blocked` | No |
| Gates not 32/32 | 200 (blocked) | `blocked` | No |
| Approval/audit package missing | 200 (blocked) | `blocked` | No |
| Checksum-before missing | 200 (blocked) | `blocked` | No |
| Rollback plan missing | 200 (blocked) | `blocked` | No |
| Disk space insufficient | 200 (blocked) | `blocked` | No |
| Operator confirmations missing | 200 (blocked) | `blocked` | No |
| dcm2niix not found | 200 (blocked) | `blocked` | Yes (audit start + final) |
| dcm2niix non-zero exit | 200 (warning) | `warning` | Yes |
| Rawdata checksum changed | 200 (failed) | `safety_violation` | Yes |
| Disk full during execution | 200 (failed) | `failed` | Yes |
| Subprocess crash | 200 (failed) | `failed` | Yes |

**The endpoint never returns 500 for gating failures.**  All gating failures are
structured 200 responses with `ok=false` and `status="blocked"`/`"disabled"`.

---

## 17. Cancellation and Timeout Policy

| Parameter | Default | Description |
|---|---|---|
| Per-subject timeout | 1800s (30 min) | SIGTERM to dcm2niix on timeout |
| Total run timeout | 7200s (2 hr) | Hard limit across all subjects |
| Cancellation | Declared, not implemented | Future: SIGTERM via endpoint |

In Phase 4L-1: cancellation is declared but not implemented.  Long-running
conversions cannot be user-cancelled.  This is documented as a known limitation.

---

## 18. Disk-Space Policy

1. **Pre-execution:** `shutil.disk_usage()` on the output root's parent directory.
2. **Block if:** `free_bytes < estimated_bytes × 1.5`
3. **Estimated bytes:** `total_rawdata_bytes × 2` (rough: NIfTI ≈ DICOM, plus sidecars and logs)
4. **On failure:** Return `status="blocked"`, `disk_space_passed=false`.

---

## 19. Output Collision Policy

| Policy | Default | Behavior |
|---|---|---|
| `fail_if_exists` | ✅ | Block if the run directory already has conversion artifacts |
| `write_new_run_directory` | Allowed | Each execution gets a unique `execution_id` under the `conversion_run_id` directory |
| Overwrite | Prohibited | Must not overwrite existing outputs without explicit rollback first |

---

## 20. Rawdata Read-Only Invariant

- All file access goes through path safety resolution.
- The endpoint must validate that `output_root` is not under any `rawdata_dir`.
- The pre-execution and post-execution checksum snapshots must match.
- If checksum changes, the run is marked `safety_violation` and all downstream
  processing is blocked.
- **The endpoint never writes to, modifies, or deletes any file under rawdata.**

---

## 21. Frontend UX Requirements (Future Phase 4L-3)

Proposed for the frontend "Run Conversion" UI (NOT implemented in Phase 4L-1):

- [ ] Release readiness check passes (all gates met, disk sufficient)
- [ ] Approval gate checklist displayed with all items confirmed
- [ ] Command templates displayed and reviewed
- [ ] Output root displayed and confirmed
- [ ] Rollback policy acknowledged
- [ ] Clinical use prohibition acknowledged
- [ ] Button labelled "Approve & Execute Conversion"
- [ ] Secondary confirmation dialog with all 7 operator confirmations
- [ ] Progress indicator per subject
- [ ] Cancel button (when cancellation is implemented)

**None of the above is implemented in Phase 4L-1.**

---

## 22. User Confirmation Copy

Proposed confirmation text for the frontend dialog:

1. **Conversion warning:** "This will convert DICOM rawdata to NIfTI format
   using dcm2niix. Rawdata will not be modified. Outputs will be written to
   the project's converted_bids directory."
2. **Clinical use prohibition:** "MedImage Agent is for research use only.
   It is not for clinical diagnosis."
3. **External tool notice:** "This operation uses the external tool dcm2niix.
   Ensure you have reviewed all command templates."
4. **Rollback notice:** "If conversion fails, you can roll back partial
   outputs using the rollback panel."
5. **Risk acknowledgement:** "This is a public data conversion operation.
   Review all command templates and approval records before proceeding."

---

## 23. Audit/Provenance Requirements

Per Phase 4J-1, every public execution must produce:

| Artifact | Written When |
|---|---|
| `audit_execution_start.json` | Before first dcm2niix invocation |
| `audit_execution_final.json` | After last dcm2niix returns (success or failure) |
| `output_manifest.json` | After all dcm2niix invocations complete |
| `execution_provenance.json` | After manifest; references all evidence paths |

Provenance `metadata` must include:
- `approval_record_path`, `audit_record_path`, `audit_final_path`
- `checksum_before_path`, `checksum_after_path`, `checksum_comparison_path`
- `rollback_plan_path`, `rollback_result_path`
- `approval_status`, `audit_state`, `release_approval_id`

---

## 24. Security / Threat Model

| Threat | Mitigation |
|---|---|
| Accidental rawdata modification | Pre/post checksum; output root validation; path safety |
| Shell injection | Command-template only; `extra='forbid'`; argv list; no `shell=True` |
| Untracked tool invocation | Audit start before dcm2niix; audit final after |
| Silent conversion failure | stdout/stderr capture; manifest verification; provenance |
| Operator bypass | 9 confirm_* fields required; release approval required |
| Clinical misuse | 3 separate clinical-use prohibitions (request + approval + UI) |
| Path traversal | `".."` rejected in mapping paths; path safety resolution |
| Disk exhaustion | Pre-execution disk check with 1.5× multiplier |
| Env flag bypass | All 7 flags checked as a set; any missing → disabled |

---

## 25. Test Strategy

### 25.1 Schema tests (`test_dicom_conversion_public_execution_schema.py`)

| # | Test |
|---|---|
| 1 | Missing `confirm_user_data_conversion` blocks |
| 2 | Missing `confirm_rawdata_readonly` blocks |
| 3 | Missing `confirm_research_use_only` blocks |
| 4 | Missing `confirm_no_clinical_use` blocks |
| 5 | Missing `confirm_rollback_available` blocks |
| 6 | Missing `confirm_disk_space_checked` blocks |
| 7 | Missing `confirm_public_execution_risk` blocks |
| 8 | Missing `MEDIMAGE_ALLOW_USER_DATA_CONVERSION` blocks |
| 9 | Missing `MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT` blocks |
| 10 | Expired release approval blocks |
| 11 | Release readiness not ready blocks |
| 12 | GO/NO-GO not 32/32 blocks |
| 13 | Approval/audit package missing blocks |
| 14 | Rollback plan missing blocks |
| 15 | Disk space failed blocks |
| 16 | Complete preconditions allow design-level decision, not execution |
| 17 | Schema imports no subprocess |
| 18 | Schema performs no file I/O |
| 19 | No `/conversion/execute` route exists in API |
| 20 | No frontend "Run Conversion" onClick handler exists |

### 25.2 Route absence tests (`test_dicom_conversion_public_execute_absence.py`)

| # | Test |
|---|---|
| 1 | `POST /conversion/execute` returns 404 or is absent |
| 2 | No route named `conversion_execute` is registered |
| 3 | No frontend API wrapper named `runProjectDicomConversionExecute` |
| 4 | No frontend text "Run Conversion" appears as a button label |
| 5 | `run_conversion_execute()` remains blocked for normal users |

### 25.3 Existing test matrices

All existing test suites must continue to pass:

- `test_dicom_conversion_release_approval.py` — 25 tests
- `test_dicom_conversion_release_readiness.py` — 19 tests
- `test_dicom_conversion_release_readiness_api.py` — 9 tests
- `test_dicom_conversion_go_no_go_schema.py` — 19 tests
- `test_dicom_conversion_rollback.py` — 14 tests
- `test_dicom_conversion_approval_audit_execution_integration.py` — 20 tests
- Phase 2/3/SPM regression matrices — 41 tests

---

## 26. Phase 4L-2 Implementation Checklist

To be completed **only** after maintainer sign-off (NOT in Phase 4L-1):

- [ ] Register `POST /api/projects/{project_id}/conversion/execute` behind env flag gate
- [ ] Implement `validate_public_execution_request_acknowledgements()`
- [ ] Implement `evaluate_public_execution_preconditions()`
- [ ] Wire release approval record validation
- [ ] Wire release readiness validation
- [ ] Wire approval/audit package validation
- [ ] Wire checksum before/after policy
- [ ] Wire rollback policy
- [ ] Implement `run_public_conversion_execute()` service function
- [ ] Add endpoint route with 404-when-disabled behavior
- [ ] Add `MEDIMAGE_ALLOW_USER_DATA_CONVERSION=1` check at entry
- [ ] Add `MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT=1` check at route registration
- [ ] Write audit start/final records
- [ ] Write manifest/provenance
- [ ] Add integration tests
- [ ] Update `PROJECT_STATE.md`
- [ ] Update `docs/DICOM_CONVERSION_RELEASE_HARDENING.md`
- [ ] Run full test suite
- [ ] Verify no `/conversion/execute` when flag is off
- [ ] Verify `/conversion/execute` works when all flags and gates pass

---

## 27. Non-Goals

- Do NOT add the `/conversion/execute` endpoint in Phase 4L-1.
- Do NOT add a frontend "Run Conversion" button in Phase 4L-1.
- Do NOT enable public conversion in Phase 4L-1.
- Do NOT change `run_conversion_execute()` behavior.
- Do NOT set `MEDIMAGE_ALLOW_USER_DATA_CONVERSION=1`.
- Do NOT set `MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT=1`.
- Do NOT call dcm2niix.
- Do NOT write NIfTI files.
- Do NOT modify rawdata.
- Do NOT use `shell=True`.
- Do NOT enable SPM/DPABI/MATLAB.
- Do NOT enable full preprocessing.
- Do NOT weaken any existing gating conditions.

---

## 28. Go/No-Go Decision for Implementation

**Decision for Phase 4L-1: DESIGN-ONLY PROCEED.**

Phase 4L-1 is the design review phase.  It produces:
1. This design contract document
2. Pure schema modules (Pydantic models, Literal types, helpers)
3. Schema tests (no endpoint, no execution)
4. Route absence tests (confirm no endpoint exists)
5. Updated `PROJECT_STATE.md` and related docs

**Decision for Phase 4L-2: NO-GO pending maintainer sign-off.**

Phase 4L-2 (implementation) must NOT proceed until:
1. This design contract is reviewed and approved.
2. Maintainer sign-off is recorded.
3. `MEDIMAGE_ALLOW_USER_DATA_CONVERSION=1` is set.
4. All Phase 4 regression matrices pass.

---

*End of Phase 4L-1 public execute endpoint design contract.  No endpoint
was added.  No frontend execution UI was added.  Public conversion remains
disabled.  SPM/DPABI/MATLAB remain disabled.  Full preprocessing remains
disabled.  Rawdata remains read-only.  Research-use only, not for clinical
diagnosis.*
