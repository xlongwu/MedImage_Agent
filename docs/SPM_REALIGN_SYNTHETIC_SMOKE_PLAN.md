# SPM Realign Synthetic Smoke Plan

**Status:** Design only — NOT IMPLEMENTED.
**Version:** v1.0-draft
**Date:** 2026-06-18

---

## 1. Purpose

This document defines a **future** synthetic smoke test for real SPM
realignment execution behind explicit environment flags.  The smoke test
validates the full execution chain from synthetic data generation through
output verification without requiring external BIDS datasets.

Explicit constraints:

- **The current phase does not run MATLAB/SPM.**  This document and any
  associated test scaffold are design-only.
- Smoke tests are **disabled by default** and must not run on CI unless
  explicitly configured.
- Smoke tests are **only for local developer machines** with MATLAB and
  SPM installed.
- **Rawdata must remain read-only.**  Synthetic fixtures are generated
  under pytest `tmp_path`, never in the repository data tree.
- This is **research-use only**, not clinical diagnosis or validation.

---

## 2. Required Environment Flags

All three flags must be present before any synthetic smoke executes:

| Flag | Value | Purpose |
|---|---|---|
| `MEDIMAGE_MATLAB_ENABLED` | `1` | Confirms MATLAB is present and execution is permitted |
| `MEDIMAGE_SPM_SMOKE_ENABLED` | `1` | Explicitly gates SPM smoke tests (separate from other MATLAB tests) |
| `MEDIMAGE_ENABLE_REVIEWED_EXECUTION` | `1` | Existing gate for reviewed-plan execution |

Additionally:

- MATLAB path must be configured (desktop config `matlab_command` or env override).
- SPM path must be configured (desktop config `spm_dir` or env override).
- Environment health must report `status != "not_configured"`.

Tests must `skip` (not `xfail`, not `pass`) when any flag or prerequisite is
missing.

---

## 3. Preconditions

Before smoke execution:

- MATLAB executable path exists and is callable.
- SPM directory exists and contains `spm.m`.
- Synthetic BOLD fixture is generated under `pytest tmp_path` — no
  repository rawdata is used.
- Output root is set to `tmp_path / "derivatives"` — no repository
  `outputs/` directory is used.
- Approval record with all 6 external-tool fields is present.
- Audit record is persisted before MATLAB is called.
- `spm_realign_subject` remains **outside** the safe execution allowlist
  (the smoke test must explicitly override or mock the allowlist policy
  for local testing).

---

## 4. Synthetic Data Design

Future synthetic BOLD fixture (generated via `nibabel` under `tmp_path`):

| Property | Value |
|---|---|
| Dimensions | 5 × 5 × 5 × 4 (4 volumes) |
| Data type | `int16` |
| Affine | Identity with 3mm isotropic voxels |
| Filename | `sub-001_task-rest_bold.nii.gz` |
| BIDS layout | `sub-001/func/sub-001_task-rest_bold.nii.gz` |
| Sidecar JSON | `sub-001/func/sub-001_task-rest_bold.json` |

Minimal sidecar:

```json
{
  "RepetitionTime": 2.0,
  "TaskName": "rest",
  "Manufacturer": "synthetic",
  "Description": "Synthetic 4D BOLD for SPM realign smoke testing"
}
```

No clinical data.  No external dataset.  Reproducible by construction.

---

## 5. Expected Future Smoke Flow

```text
1.  Generate synthetic BIDS fixture (nibabel + json).
2.  Create project referencing synthetic fixture.
3.  Run BOLD reference readiness — must not be blocked.
4.  Run SPM dry-run manifest — must produce predicted outputs.
5.  Build wrapper skeleton — batch preview + manifests.
6.  Validate approval (all 6 external-tool fields).
7.  Persist audit record.
8.  [FUTURE] Invoke real MATLAB/SPM execution behind env flags.
9.  Verify outputs exist and are non-zero:
    a. Realigned BOLD (r<sub>_bold.nii)
    b. Mean/reference BOLD (mean<sub>_bold.nii)
    c. Motion parameters (rp_*.txt)
    d. stdout log
    e. stderr log
    f. Provenance JSON
    g. Node state JSON
10. Verify rawdata fixture is unchanged (checksum before/after).
11. Verify artifacts are previewable through existing artifact discovery.
12. Verify motion QC readiness picks up rp_*.txt.
13. Verify motion metrics draft can parse rp_*.txt.
```

---

## 6. Skip Policy

Strict skip conditions — if any of the following is true, the smoke test
must be `pytest.mark.skip`:

| Condition | Reason |
|---|---|
| `MEDIMAGE_MATLAB_ENABLED != "1"` | MATLAB execution not permitted |
| `MEDIMAGE_SPM_SMOKE_ENABLED != "1"` | SPM smoke not explicitly enabled |
| `MEDIMAGE_ENABLE_REVIEWED_EXECUTION != "1"` | Reviewed execution not enabled |
| MATLAB path not configured | No MATLAB available |
| SPM path not configured | No SPM available |
| `spm_realign_subject` not in safe allowlist | Execution blocked by policy |
| Output root not under `tmp_path` | Safety violation |
| `nibabel` not installed | Cannot generate synthetic data |
| CI environment detected | No MATLAB on CI runners |

The test must NOT `xfail` — a skip means "not applicable", not "broken".

---

## 7. Failure Policy

When the smoke test IS executed and a failure occurs, fail closed:

| Failure | Action |
|---|---|
| MATLAB missing or not callable | `pytest.fail` with clear message |
| SPM missing or `spm.m` not found | `pytest.fail` |
| Output in rawdata | `pytest.fail` |
| Output conflict (overwrite_policy) | `pytest.fail` |
| Rawdata modified | `pytest.fail` |
| Expected outputs missing | `pytest.fail` |
| Zero-size outputs | `pytest.fail` |
| Provenance missing or incomplete | `pytest.fail` |
| Logs missing or empty | `pytest.fail` |
| Node state reports success but outputs missing | `pytest.fail` |

Every failure must include a descriptive message referencing the specific
expected vs actual condition.

---

## 8. Non-Goals

- No clinical validation or accuracy measurement.
- No performance benchmarking (timing, memory).
- No full preprocessing pipeline (slice timing, normalization, smoothing).
- No DPABI execution.
- No real dataset smoke (that is a separate external BIDS smoke test).
- No default CI execution.
- No cross-platform SPM version matrix.

---

## 9. Future Implementation Checklist

Before the synthetic smoke test is enabled:

- [ ] Command template pure-function tests pass (`test_spm_realign_command_template.py`).
- [ ] Execution contract schemas are stable (`test_spm_realign_execution_contract_schema.py`).
- [ ] Dry-run → manifest adapter is tested (`test_spm_realign_manifest_alignment.py`).
- [ ] Wrapper skeleton output manifests are tested (`test_spm_realign_wrapper_skeleton.py`).
- [ ] Approval gate external-tool fields are tested (`test_external_tool_approval_audit.py`).
- [ ] Pre-execution regression matrix is green (`test_spm_realign_preexecution_matrix.py`).
- [ ] MATLAB/SPM environment health check confirms readiness.
- [ ] Synthetic fixture generation helper exists (pure, deterministic).
- [ ] Skip policy is enforced at module level.
- [ ] All smoke tests use `tmp_path` only.
- [ ] Rawdata unchanged assertion runs after every smoke execution.
- [ ] `spm_realign_subject` is temporarily added to safe allowlist for smoke only.
- [ ] MATLAB subprocess is wrapped with timeout (default 300s for synthetic data).
- [ ] stdout/stderr capture is verified.
- [ ] Post-execution artifact discovery is verified.

---

*End of smoke plan document.  Real MATLAB/SPM execution is not implemented
in the current phase.  This document is a design reference for a future
implementation phase.*
