---
name: spm-rsfmri-preprocessing
description: Run SPM12-based rs-fMRI preprocessing pipeline including slice timing, realignment, coregistration, segmentation, normalization, and smoothing.
---

# SPM rs-fMRI Preprocessing Skill

## Inputs
- T1w NIfTI (anatomical)
- BOLD NIfTI (functional)
- BIDS sidecar JSON (for TR, slice timing)

## Outputs
- `derivatives/spm_preproc/` with stage outputs
- SPM matlabbatch `.mat` files
- Stage-level QC JSON files

## Stages
1. **Slice Timing** — `spm_slice_timing_runner.py`
2. **Realign** — `spm_realign_runner.py`
3. **Coregister** — `spm_coregister_runner.py`
4. **Segment** — `spm_segment_runner.py`
5. **Normalize** — `spm_normalize_runner.py`
6. **Smooth** — `spm_smooth_runner.py`

## Rules
- Do not modify rawdata. All outputs go to derivatives/.
- Save every matlabbatch for reproducibility.
- Capture stdout/stderr for error diagnosis.
- Run stage-level QC after each node.
- Do not modify SPM12 source files.
