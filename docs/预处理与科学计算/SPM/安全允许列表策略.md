# SPM Safe Allowlist Policy

**Status:** Policy document — binding for current phase.
**Version:** v1.0
**Date:** 2026-06-18

---

## 1. Purpose

This document defines the conditions under which `spm_realign_subject` may
be considered for future inclusion in the safe execution allowlist.  It
also records the **current binding decision** and the guard tests that
must remain green until real execution is intentionally implemented.

Binding decisions:

- **Current decision is NO-GO for real MATLAB/SPM execution.**
- `spm_realign_subject` **must remain outside the safe execution
  allowlist** in the current phase.
- The existence of dry-run manifest, wrapper skeleton, batch preview, and
  smoke scaffold **does not imply execution readiness.**
- This platform is **research-use only**, not for clinical diagnosis.

---

## 2. Current Status

The following non-executing SPM realign preparation capabilities are
implemented and tested:

| Capability | Status |
|---|---|
| High-risk tool catalog metadata (`not-executable` tag) | ✅ |
| SPM parameter validation (`validate_spm_realign_params`) | ✅ |
| Plan Validator integration (`SPM_REALIGN_PARAM_INVALID`, `SPM_REALIGN_NODE_NOT_EXECUTABLE`) | ✅ |
| MATLAB/SPM environment health check (`build_matlab_spm_health`) | ✅ |
| SPM dry-run output manifest (`build_spm_realign_dry_run`) | ✅ |
| SPM wrapper skeleton / batch preview (`build_spm_realign_batch_preview_result`) | ✅ |
| Output/provenance manifest adapter (`spm_realign_manifest_adapter`) | ✅ |
| Wrapper skeleton output manifest integration | ✅ |
| Command-template pure-function tests (`test_spm_realign_command_template.py`) | ✅ |
| Execution contract Pydantic schemas (`SpmRealignExecutionRequest` et al.) | ✅ |
| Backend approval/audit external-tool gate (`check_approval_gate`) | ✅ |
| PlanReviewConsole External Tool Safety Acknowledgement UI | ✅ |
| Frontend dry-run/execute button gating for high-risk nodes | ✅ |
| Synthetic smoke scaffold (skipped by default) | ✅ |
| Pre-execution regression matrix | ✅ |
| Real MATLAB/SPM execution | ❌ NOT IMPLEMENTED |
| Safe allowlist entry | ❌ NOT PRESENT |

---

## 3. Allowlist Inclusion Preconditions

`spm_realign_subject` may NOT be added to the safe execution allowlist
until ALL of the following are true:

1. [ ] Real execution design review (`SPM_REALIGN_REAL_EXECUTION_DESIGN_REVIEW.md`) has been updated from **NO-GO to GO**.
2. [ ] Command-template pure-function tests pass.
3. [ ] Execution contract schemas are consumed by real execution code.
4. [ ] Approval gate passes with all 6 external-tool fields.
5. [ ] Audit record is persisted BEFORE MATLAB is called.
6. [ ] Dry-run manifest is reused for output path prediction.
7. [ ] Output manifest is verified after execution.
8. [ ] Provenance JSON is written with all required fields.
9. [ ] stdout and stderr are captured to log files.
10. [ ] Timeout and cancellation strategy is implemented.
11. [ ] Rawdata unchanged test passes (checksum before/after).
12. [ ] Synthetic smoke passes behind explicit environment flags.
13. [ ] External BIDS smoke passes behind explicit environment flags.
14. [ ] Frontend warnings remain present on all relevant panels.
15. [ ] README and README_CN are updated.
16. [ ] Explicit maintainer approval is recorded (commit message / PR review).

---

## 4. Required Environment Flags

Any future real execution of `spm_realign_subject` must require ALL of
the following environment flags:

| Flag | Value | Purpose |
|---|---|---|
| `MEDIMAGE_MATLAB_ENABLED` | `1` | Confirms MATLAB is present |
| `MEDIMAGE_SPM_SMOKE_ENABLED` | `1` | Explicitly gates SPM-specific execution |
| `MEDIMAGE_ENABLE_REVIEWED_EXECUTION` | `1` | Gates reviewed-plan execution |
| `MEDIMAGE_ENABLE_SPM_REALIGN_EXECUTION` | `1` | Node-specific execution gate |

If ANY flag is missing or not `"1"`, real execution must be blocked
regardless of allowlist state.

---

## 5. Forbidden Shortcuts

The following are **never sufficient** to enable `spm_realign_subject`:

- [x] Environment health check alone
- [x] Frontend checkbox alone
- [x] Planner output alone
- [x] Dry-run manifest success alone
- [x] Wrapper skeleton / batch preview success alone
- [x] Approval gate passing alone
- [x] Audit record existing alone
- [x] Adding a runner without tests
- [x] Setting `MEDIMAGE_MATLAB_ENABLED=1` alone
- [x] Safe output root existing alone

Every precondition in section 3 must be satisfied.

---

## 6. Guard Test Requirements

The following guard tests must remain **green** in the current phase
(they test that SPM execution is correctly disabled):

| Guard Test | Assertion |
|---|---|
| Tool catalog metadata | `spm_realign_subject` has `not-executable` tag and `manual_required: True` |
| Safe allowlist | `spm_realign_subject` is NOT in the safe execution allowlist |
| Dry-run manifest | `execution_enabled: False`, `safe_allowlist_enabled: False` |
| Wrapper skeleton | `execution_disabled` safety flag is `True` |
| Wrapper skeleton preview | No `matlab -batch` in batch preview |
| Synthetic smoke | Skipped without env flags |
| Approval gate | Not sufficient alone for execution |
| Subprocess | No MATLAB/SPM call in dry-run/wrapper-skeleton path |

---

## 7. Future Change Procedure

Before enabling `spm_realign_subject`:

1. Update `SPM_REALIGN_REAL_EXECUTION_DESIGN_REVIEW.md` from NO-GO to GO.
2. Implement real runner behind env flag.
3. Add execution tests behind env flag.
4. Add rawdata unchanged tests.
5. Add artifact and provenance verification tests.
6. Add allowlist entry ONLY after all test evidence is reviewed.
7. Update README, README_CN, and user-facing warnings.
8. Record explicit maintainer approval.

---

## 8. Rollback Procedure

If problems are discovered after enabling real execution:

1. Remove `spm_realign_subject` from safe allowlist.
2. Unset `MEDIMAGE_ENABLE_SPM_REALIGN_EXECUTION`.
3. Hide or disable execute button in frontend (button gating already
   handles this when `externalToolApprovalComplete` is false).
4. Keep dry-run manifest and wrapper skeleton fully functional.
5. Preserve old run artifacts for investigation — never delete
   automatically.
6. Record the disable event in an audit record.

---

*End of safe-allowlist policy document.  `spm_realign_subject` remains
outside the safe execution allowlist in the current phase.*
