# Nuisance Regression Specification

This document defines the MVP nuisance regression stage for rs-fMRI preprocessing.

## Goals

Build an auditable nuisance regression design, generate a confound matrix, execute a safe Python nuisance regression backend on synthetic derivatives, and define a future DPABI backend contract.

## Scope

Supported: synthetic derivative input only, confound matrix generation, motion 6, Friston 24, intercept and linear trend, tissue regressor placeholders, optional global signal (default false), Python OLS residualization backend, DPABI backend contract without execution, subject-level and dataset-level QC reports.

Unsupported: real medical image preprocessing, DPABI execution, DPARSF_run/DPARSFA_run, DPABI GUI, temporal filtering, ALFF/fALFF/ReHo, rawdata modification, file deletion.

## Inputs

- `derivatives/rsfmri_preproc/{subject_id}/func/swr*.nii`
- `derivatives/rsfmri_preproc/{subject_id}/func/rp_*.txt`
- `derivatives/rsfmri_preproc/{subject_id}/anat/c1coreg_*.nii`, `c2coreg_*.nii`, `c3coreg_*.nii`

## Outputs

- `derivatives/rsfmri_confounds/{subject_id}/confounds.tsv`, `confounds.json`, `confound_qc.json`
- `derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii`, `nuisance_regression_result.json`
- `derivatives/rsfmri_qc/{subject_id}/nuisance_regression_qc.json`, `.md`
- `reports/rsfmri/nuisance_regression_qc_summary.json`, `.md`
- `work/dpabi/contracts/nuisance_regression_backend_contract.json`

## Backend Modes

- **python**: OLS residualization directly in Python (numpy pinv).
- **dpabi_contract**: Generates only a contract/plan, does not execute DPABI.

## Safety Rules

- Only derivative smoothed normalized functional input.
- Only derivative motion parameter input.
- Do not modify rawdata. Do not delete files.
- Do not execute DPABI. Do not call DPARSF_run/DPARSFA_run/DPABI GUI.
