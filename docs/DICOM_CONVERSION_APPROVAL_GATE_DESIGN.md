# DICOM Conversion Approval Gate Design Review — Phase 4D

**Status:** Design review — NOT IMPLEMENTED as execution gate.
**Version:** v1.0-draft
**Date:** 2026-06-08
**Parent:** `docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md`

---

## 1. Purpose and Scope

This document defines the **approval and audit gate** required before
MedImage Agent can ever execute real DICOM-to-NIfTI conversion on user
rawdata.  It specifies the complete set of preconditions, approval record
fields, audit requirements, operator acknowledgements, and go/no-go
checklist.

**Binding decision:**

- **Current decision is NO-GO for real user-data DICOM conversion.**
- No real user-data conversion endpoint exists.
- No "Run conversion" button exists in the UI.
- The existence of the preflight endpoint, synthetic smoke path, sandbox
  runner, and conversion review panel **does not imply execution readiness.**

---

## 2. Current Disabled Baseline

| Capability | Status |
|---|---|
| Conversion dry-run (6 mapping previews) | ✅ |
| Conversion preflight endpoint (read-only) | ✅ |
| dcm2niix availability check | ✅ |
| Sandbox runner (fake_outputs, mock_subprocess) | ✅ |
| Synthetic dcm2niix smoke (synthetic DICOM only) | ✅ |
| Conversion review panel (operator UI) | ✅ |
| Command-template generation and display | ✅ |
| Real user-data conversion execution | ❌ NOT IMPLEMENTED |
| Approval gate for conversion | ❌ NOT IMPLEMENTED |
| Audit record for conversion | ❌ NOT IMPLEMENTED |
| Conversion execute endpoint | ❌ NOT IMPLEMENTED |
| "Run conversion" button | ❌ NOT PRESENT |

---

## 3. Non-Goals

- Do NOT implement real user-data conversion in this phase.
- Do NOT add a conversion execute endpoint.
- Do NOT add a "Run conversion" button.
- Do NOT call dcm2niix on real rawdata.
- Do NOT enable SPM/DPABI/MATLAB execution.
- Do NOT expand the safe allowlist.

---

## 4. Threat Model

The following threats must be mitigated by the approval gate:

| Threat | Mitigation |
|---|---|
| Accidental rawdata modification | Output root validation; rawdata read-only confirmation |
| Unreviewed output paths | Mapping review + output root confirmation |
| Shell injection | Command-template-only policy; no-shell-string acknowledgement |
| Untracked tool invocation | Audit record persisted *before* dcm2niix call |
| Silent conversion failure | stdout/stderr capture; manifest verification; provenance |
| Operator bypass | All 17 approval fields required; no wildcard bypass |
| Clinical misuse | Clinical-use prohibition acknowledgement required |

---

## 5. Required Preconditions for User-Data Conversion

All of the following must be satisfied before real conversion can proceed:

1. [ ] User approval record with all required fields
2. [ ] Audit record persisted *before* dcm2niix is called
3. [ ] `confirm_execution=true`
4. [ ] Conversion-specific approval ID
5. [ ] Selected mappings reviewed (operator confirms each mapping)
6. [ ] Output root under project output directory (validated)
7. [ ] Output root NOT under rawdata directory (validated)
8. [ ] Overwrite policy explicitly set
9. [ ] Rawdata read-only acknowledgement
10. [ ] Command templates reviewed
11. [ ] No shell string acknowledgement
12. [ ] dcm2niix availability verified (on PATH, version recorded)
13. [ ] All required environment flags present
14. [ ] Manifest and provenance paths planned
15. [ ] stdout/stderr log paths planned
16. [ ] Rollback/cleanup policy accepted
17. [ ] Clinical-use prohibition acknowledged

---

## 6. Approval Record Fields

```json
{
  "approval_id": "conv-approval-abc123",
  "project_id": "proj-xyz",
  "reviewed_plan_id": "rp-def456",
  "status": "ready_for_review",
  "approved": true,
  "approved_by": "researcher@lab",
  "approved_at": "2026-06-08T12:00:00Z",
  "mapping_ids": ["map-001", "map-002", "map-003", "map-004", "map-005", "map-006"],
  "mappings_reviewed": true,
  "output_root": "/project/converted_bids",
  "output_root_confirmed": true,
  "output_root_under_project": true,
  "output_root_not_rawdata": true,
  "rawdata_read_only_confirmed": true,
  "command_templates_reviewed": true,
  "no_shell_string_confirmed": true,
  "dcm2niix_availability_confirmed": true,
  "dcm2niix_version": "v1.0.20230411",
  "env_flags_confirmed": true,
  "missing_env_flags": [],
  "overwrite_policy": "fail_if_exists",
  "rollback_policy_acknowledged": true,
  "clinical_use_prohibited_acknowledged": true,
  "external_tool_acknowledgement": true,
  "risk_acknowledgement": true,
  "warnings": [],
  "errors": []
}
```

---

## 7. Audit Record Requirements

An audit record must be persisted **before** any dcm2niix invocation:

| Field | Required | Description |
|---|---|---|
| `audit_id` | Yes | Unique audit identifier |
| `approval_id` | Yes | Links to the approval record |
| `project_id` | Yes | Project being converted |
| `reviewed_plan_id` | Yes | Reviewed plan reference |
| `preflight_hash` | Yes | SHA-256 of the preflight response at audit time |
| `command_template_hashes` | Yes | SHA-256 per command template |
| `input_dicom_checksum` | Yes | Directory-level checksum of input DICOM files |
| `output_root` | Yes | Confirmed output root path |
| `env_fingerprint` | Yes | Environment fingerprint at audit time |
| `dcm2niix_version` | Yes | Recorded dcm2niix version |
| `persisted_at` | Yes | ISO-8601 timestamp of persistence |

After execution, the audit record is updated with:
- `output_manifest_sha256`
- `provenance_sha256`
- `execution_return_code`
- `rawdata_unchanged_confirmed`

---

## 8. Operator Acknowledgements

Every field marked as an acknowledgement must be explicitly confirmed by
the operator.  Implicit/default confirmations are not accepted.

| Acknowledgement | Confirmation Text |
|---|---|
| Rawdata read-only | "I confirm that no rawdata files will be modified, deleted, or renamed." |
| Output root | "I confirm that conversion outputs will be written to the specified output root, which is under the project directory and not inside rawdata." |
| Command templates | "I have reviewed all command templates and confirm they are correct." |
| No shell string | "I confirm that no raw shell strings are used. All commands use argv lists." |
| dcm2niix availability | "I confirm that dcm2niix is installed and available at the recorded path." |
| Env flags | "I confirm that all required environment flags are set." |
| Rollback policy | "I accept that partial outputs will be removed if conversion fails." |
| Clinical use | "I acknowledge that MedImage Agent is for research use only and is not for clinical diagnosis." |

---

## 9. Output Directory Confirmation

- Output root must be displayed to the operator for explicit review.
- The operator must confirm the path.
- The system must validate: output root under project dir, not under rawdata.
- Overwrite policy must be explicit (`fail_if_exists`, `overwrite_derivatives_only`, or `write_new_run_directory`).

---

## 10. Rawdata Read-Only Confirmation

- The operator must acknowledge that rawdata will not be modified.
- Pre-execution and post-execution DICOM file count must be verified.
- Any discrepancy blocks all downstream processing.

---

## 11. Mapping Review Requirements

- Each conversion mapping must be individually reviewed.
- The operator must confirm the subject ID, modality, suffix, and target path.
- All mappings must be reviewed before approval is considered complete.

---

## 12. Command-Template Review Requirements

- Each dcm2niix command template must be displayed in structured form.
- `command_preview` is display-only and must be labelled as such.
- The operator must confirm that no raw shell strings are present.

---

## 13. dcm2niix Availability Requirements

- dcm2niix must be on PATH and its version recorded.
- Availability must be re-checked at approval time, not only at preflight time.
- If dcm2niix is removed or upgraded between preflight and approval, the
  approval must be invalidated.

---

## 14. Env Flag Requirements

All of the following must be `"1"`:

| Flag | Check |
|---|---|
| `MEDIMAGE_ENABLE_DICOM_CONVERSION` | Required |
| `MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE` | Required (even for real data, as an explicit gate) |
| `MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE` | Required |
| `MEDIMAGE_MATLAB_ENABLED` | Required |
| `MEDIMAGE_SPM_SMOKE_ENABLED` | Required |
| `MEDIMAGE_ENABLE_REVIEWED_EXECUTION` | Required |
| `MEDIMAGE_ENABLE_REAL_PREPROCESSING` | Required |

---

## 15. Safe Allowlist Requirements

The `dicom_to_nifti` node must be added to the safe execution allowlist
only after ALL 17 preconditions (Section 5) are implemented and tested.

Following the pattern in `docs/SPM_SAFE_ALLOWLIST_POLICY.md`:

16 conditions must be met, including:
- Real execution design review updated from NO-GO to GO
- Command-template tests pass
- Execution contract schemas consumed
- Approval gate passes
- Audit record persisted *before* external tool call
- Dry-run manifest reused
- Output manifest verified
- Provenance JSON written
- stdout/stderr captured
- Timeout/cancellation implemented
- Rawdata unchanged test passes
- Synthetic smoke passes
- External DICOM smoke passes
- Frontend warnings present
- README updated
- Explicit maintainer approval recorded

---

## 16. Manifest / Provenance Requirements

- Output manifest must be planned before execution.
- Provenance record must be planned before execution.
- Both paths must be confirmed in the approval record.
- After execution, manifest and provenance are verified against the plan.

---

## 17. Failure / Rollback Requirements

- If conversion fails, all partial outputs are removed (best-effort rollback).
- The operator must acknowledge the rollback policy before execution.
- A `DicomConversionFailureRecord` must be written recording any failure.

---

## 18. Frontend UX Requirements

### Current state

- `DicomConversionReviewPanel` shows conversion readiness, dcm2niix availability,
  command templates, safety flags, mappings, and operator warning.
- No "Run conversion" button exists.

### Future approval UI (NOT implemented in this phase)

- Add an "Approval Gate Checklist" section showing all 17 preconditions
  with checkboxes.
- Each checkbox must be explicitly toggled by the operator.
- "Approve & Execute" button must remain disabled until all checkboxes
  are checked AND all env flags are confirmed AND dcm2niix is available.
- The button must be labelled "Approve & Execute Conversion" (not just "Run").
- A secondary confirmation dialog must appear before execution.
- The dialog must restate all safety acknowledgements.

---

## 19. Test Strategy

### Schema tests (this phase)

`tests/unit/test_dicom_conversion_approval_schema.py`:
- All 17 preconditions represented in approval record
- Missing any required field → blocked/incomplete
- Unsafe output root → blocked
- Rawdata output root → blocked
- All fields present + safe → approved
- No subprocess imports
- No file writes
- No SPM/DPABI/MATLAB imports

### Future gate tests (NOT this phase)

- Approval gate integration with preflight
- Audit record persistence before dcm2niix
- Approval invalidation when dcm2niix version changes
- Frontend checklist toggle logic
- Confirmation dialog behavior

---

## 20. Go / No-Go Checklist

Before real user-data conversion can be enabled:

- [ ] All 17 preconditions (Section 5) are implemented and tested
- [ ] All 16 safe allowlist conditions are met
- [ ] Approval schema consumed by real gate code
- [ ] Audit record persistence implemented
- [ ] Frontend approval checklist implemented
- [ ] Confirmation dialog implemented
- [ ] Synthetic smoke passes
- [ ] External DICOM smoke passes (on a single subject, behind all flags)
- [ ] Rawdata unchanged test passes
- [ ] Output manifest verified
- [ ] Provenance complete
- [ ] Rollback tested
- [ ] README / README_CN updated
- [ ] Explicit maintainer approval recorded (commit message / PR review)

**Current status: 0/14 conditions met.  Real user-data conversion remains NO-GO.**

---

## 21. Phase 4E-0 — Approval Persistence and Run-Directory Reservation

**Implemented.**  This section records the Phase 4E-0 contract after implementation.

### 21.1 Purpose

Phase 4E-0 adds persistence for approval records and run-directory reservation
without executing dcm2niix.  It prepares the audit/run artifact structure
required before future real DICOM-to-NIfTI conversion.

### 21.2 What gets persisted

- `approval_record.json` — full `DicomConversionApprovalRecord`
- `audit_preview.json` — planned `DicomConversionAuditRecord`
- `preflight_snapshot.json` — full preflight response at persist time
- `mapping_snapshot.json` — conversion mappings at persist time
- `command_templates.json` — dcm2niix command templates at persist time
- `planned_output_manifest.json` — skeleton `OutputManifest`
- `planned_execution_provenance.json` — skeleton `ExecutionProvenance`
- `README.md` — human-readable summary explaining no conversion was executed

### 21.3 What does NOT get executed

- No dcm2niix invocation
- No NIfTI file creation
- No rawdata modification
- No external tool execution

### 21.4 Run directory layout

```
<project_dir>/conversion_runs/<conversion_run_id>/
├── approval_record.json
├── audit_preview.json
├── preflight_snapshot.json
├── mapping_snapshot.json
├── command_templates.json
├── planned_output_manifest.json
├── planned_execution_provenance.json
├── logs/
│   ├── stdout.log  (empty placeholder)
│   └── stderr.log  (empty placeholder)
└── README.md
```

### 21.5 Endpoint

`POST /api/projects/{project_id}/conversion/approval/persist-plan`

- Evaluates approval gate before writing
- Returns `status=blocked` for incomplete approval
- Reserves run directory only when safe
- Returns reservation paths and gate decision
- No dcm2niix call, no NIfTI writes, no rawdata modification

### 21.6 Immediate next task — Phase 4E-1

**Persisted conversion review package UI polish and audit export.**

- Full display of persisted approval/review package in the UI
- Audit export bundle (zip of all persisted metadata)
- Still no conversion execution

---

*End of design review document.  Real user-data DICOM conversion remains
disabled.  This document defines the approval gate that must be satisfied
before any real conversion can be enabled.  Research-use only, not for
clinical diagnosis.*
