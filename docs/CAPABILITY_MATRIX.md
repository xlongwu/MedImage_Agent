# Capability Matrix

Current as of 2026-06-20. This matrix records the real capability level of
each preprocessing stage in the MedImage Agent pipeline runtime. It is a
record of **current code behavior**, not a roadmap.

When code and documentation disagree, current executable code wins
(see `AGENTS.md` "Source of Truth"). Update this matrix whenever a stage's
real output level changes.

## Capability Levels

Each stage is classified at exactly one level. Levels are strictly ordered
from least to most real:

| Level | Meaning |
|-------|---------|
| **Contract Only** | Only the request/response schema and safety gate exist. No execution body. |
| **Dry-run** | A dry-run plan or preview is produced without touching the functional input. |
| **Sandbox Scaffold** | Input is copied into a sandbox workspace but no metric is computed. |
| **Metadata Only** | Descriptor files (shape, status JSON) are written; no real numerical artifact persists. |
| **Numerically Implemented** | A real numeric artifact (NIfTI map / `.npy` matrix) is produced by a unified compute kernel and is reloadable. |
| **Reference Validated** | Numerically Implemented **and** validated against an independent reference / golden dataset within tolerance. |
| **Release Ready** | Reference Validated, covered by CI, and the production execution path is enabled by maintainer approval. |

## Matrix

| Stage | Level | Notes / Provenance |
|-------|-------|--------------------|
| DICOM Conversion | Release Ready | Guarded public path verified against DemoData; default-blocked by env/approval gates. |
| Slice Timing | Needs Verification | SPM/MATLAB-gated; sandbox + dry-run available, real execution off by default. |
| Realignment | Needs Verification | SPM/MATLAB-gated; pre-execution matrix contract available. |
| Coregistration / Normalization | Needs Verification | SPM/MATLAB-gated; sandbox scaffold available. |
| Smoothing | Needs Verification | SPM/MATLAB-gated; sandbox execution available. |
| Nuisance Regression | Needs Verification | Python kernel exists; sandbox execution available. |
| Filtering | Needs Verification | Python kernel exists; sandbox execution available. |
| **ALFF** | Numerically Implemented | FFT kernel (`tools/alff_compute.py::compute_alff_backend`) wired into the sandbox execution service; outputs `ALFF` + `fALFF` NIfTI and provenance. |
| **fALFF** | Numerically Implemented | Produced alongside ALFF by the same FFT kernel. |
| **ReHo** | Numerically Implemented | KCC kernel (`tools/reho_compute.py::compute_reho_backend`) wired into the sandbox execution service; 7/19/27 neighborhoods supported. |
| **FC** | Numerically Implemented | ROI Pearson kernel (`tools/functional_connectivity_compute.py::compute_fc_backend`); persists real `.npy`/`.tsv` correlation + Fisher-Z matrices. |

## Traceability

Each **Numerically Implemented** or higher stage is backed by:

- A unified compute kernel under `src/backend/app/tools/*_compute.py`.
- A sandbox execution service under `src/backend/app/services/preprocessing_*_execution.py` that calls the kernel (no inline math).
- A per-metric status entry in `manifest.json` distinguishing sandbox-prepared vs numerically-computed.
- Golden/regression tests under `tests/golden/` and `tests/unit/`.

"Needs Verification" means the SPM/MATLAB external tool path exists but is
not exercised in this environment; it is not a claim of numerical correctness.
