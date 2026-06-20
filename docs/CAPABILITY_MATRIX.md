# Capability Matrix

Current as of 2026-06-20. This matrix records the real capability level of
each preprocessing stage in the MedImage Agent pipeline runtime. It is a
record of **current code behavior**, not a roadmap.

When code and documentation disagree, current executable code wins
(see `AGENTS.md` "Source of Truth"). Update this matrix whenever a stage's
real output level changes.

## Capability Levels

Each stage is classified at exactly one **Capability Level**. Levels are
strictly ordered from least to most real:

| Level | Meaning |
|-------|---------|
| **Contract Only** | Only the request/response schema and safety gate exist. No execution body. |
| **Dry-run** | A dry-run plan or preview is produced without touching the functional input. |
| **Sandbox Scaffold** | Input is copied into a sandbox workspace but no metric is computed. |
| **Metadata Only** | Descriptor files (shape, status JSON) are written; no real numerical artifact persists. |
| **Numerically Implemented** | A real numeric artifact (NIfTI map / `.npy` matrix) is produced by a unified compute kernel and is reloadable. |
| **Reference Validated** | Numerically Implemented **and** validated against an independent reference / golden dataset within tolerance. |
| **Release Ready** | Reference Validated, covered by CI, and the production execution path is enabled by maintainer approval. |

## Validation Status

Separate from capability level, each stage carries a **Validation Status**
describing the state of independent verification:

| Status | Meaning |
|--------|---------|
| **Unvalidated** | Numerically implemented but no independent reference or golden test exists, OR the implementation has known gaps on certain backends (e.g. GPU ties handling). |
| **Needs Verification** | An external tool path (SPM/MATLAB) exists but is not exercised in this environment; not a claim of numerical correctness. |
| **Golden Validated** | Validated against committed golden `.npy` fixtures via `tests/test_scientific_golden.py` or `tests/golden/test_algorithm_golden.py`. |
| **Reference Validated** | Golden Validated **and** an independent from-scratch reference implementation agrees within tolerance. |
| **E2E Validated** | Validated end-to-end against DemoData via integration smoke test (default-skipped in CI). |

## Availability

Describes whether and how the stage can be exercised:

| Availability | Meaning |
|--------------|---------|
| **Default-Blocked** | Requires explicit env flags and/or external tools to run; never executes by default. |
| **Sandbox-Only** | Execution confined to sandbox workspace; no production path. |
| **CI-Covered** | Golden/regression tests run in the backend CI job on every push/PR. |
| **Manually Release-Validated** | Requires a persisted human release approval record before execution. |

## Matrix

| Stage | Capability Level | Validation Status | Availability |
|-------|-----------------|-------------------|--------------|
| DICOM Conversion | Reference Validated | E2E Validated | Manually Release-Validated; Default-Blocked (12 env flags + dcm2niix + pydicom + DemoData) |
| Slice Timing | Dry-run | Needs Verification | Default-Blocked (SPM/MATLAB-gated) |
| Realignment | Dry-run | Needs Verification | Default-Blocked (SPM/MATLAB-gated) |
| Coregistration / Normalization | Sandbox Scaffold | Needs Verification | Default-Blocked (SPM/MATLAB-gated) |
| Smoothing | Sandbox Scaffold | Needs Verification | Default-Blocked (SPM/MATLAB-gated) |
| Nuisance Regression | Numerically Implemented | Needs Verification | Sandbox-Only |
| Filtering | Numerically Implemented | Needs Verification | Sandbox-Only |
| **ALFF** | Numerically Implemented | Reference Validated | Sandbox-Only; CI-Covered (golden regression) |
| **fALFF** | Numerically Implemented | Reference Validated | Sandbox-Only; CI-Covered (golden regression) |
| **ReHo** | Numerically Implemented | Golden Validated (CPU); Unvalidated (GPU) | Sandbox-Only; CI-Covered (golden regression, CPU path) |
| **FC** | Numerically Implemented | Reference Validated (Pearson kernel only) | Sandbox-Only; CI-Covered (golden regression); Synthetic-atlas preview only — atlas-grounded FC workflow not yet validated |

### DICOM Conversion note

DICOM Conversion is classified as **Reference Validated** (not Release Ready)
because the production execution path is default-blocked by 12 env flags and
requires dcm2niix + pydicom + DemoData; the E2E smoke test
(`tests/integration/test_dicom_conversion_public_e2e_smoke.py`) is
default-skipped in CI. It is not "Release Ready" until the default-blocked
constraint is lifted by maintainer approval.

### FC capability breakdown

The FC entry above covers the **Pearson correlation kernel** only
(`tools/functional_connectivity_compute.py::compute_fc_backend`), which is
Reference Validated via golden regression. The sandbox execution service
always uses a **synthetic x-chunk atlas** (`_generate_atlas` with
`roi_count=8`), not a real brain atlas (AAL, Schaefer, Brainnetome, etc.).
Therefore:

| Sub-capability | Status |
|----------------|--------|
| ROI Pearson correlation kernel | Reference Validated |
| Synthetic x-chunk atlas FC preview | Numerically Implemented |
| External atlas loading | Not Yet Implemented |
| Atlas-grounded research FC workflow | Not Yet Validated |

### ReHo CPU vs GPU validation breakdown

The ReHo entry distinguishes CPU and GPU validation:

| Backend | Validation Status | Notes |
|---------|-------------------|-------|
| CPU (NumPy) | Golden Validated | Kendall's W with ties correction (average ranks + tie factor). Validated against committed golden fixtures and an independent pure-NumPy reference. |
| GPU (CuPy) | Unvalidated | Double-argsort ranking does NOT handle ties (no average ranks, no tie correction). Ties are common in real fMRI data (background zeros, quantized signals, scrubbed timepoints). `compute_reho_backend` auto-detects ties and falls back to CPU. |

## Traceability

Each **Numerically Implemented** or higher stage is backed by:

- A unified compute kernel under `src/backend/app/tools/*_compute.py`.
- A sandbox execution service under `src/backend/app/services/preprocessing_*_execution.py` that calls the kernel (no inline math).
- A per-metric status entry in `manifest.json` distinguishing sandbox-prepared vs numerically-computed.
- Golden/regression tests under `tests/test_scientific_golden.py`, `tests/test_scientific_gpu_consistency.py`, and `tests/golden/test_algorithm_golden.py`.

"Needs Verification" in the Validation Status column means the SPM/MATLAB
external tool path (or an equivalent Python kernel) exists but is not
exercised in this environment; it is not a claim of numerical correctness.
