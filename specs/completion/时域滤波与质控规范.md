# Temporal Filtering and Filtering QC Specification

This document defines the MVP temporal filtering stage for rs-fMRI preprocessing.

## Goals

Apply temporal band-pass filtering to nuisance-regressed rs-fMRI derivatives and compute lightweight filtering QC metrics.

## Scope

Supported: synthetic derivative input only, Python FFT-based band-pass filtering, TR discovery from slice timing QC or explicit fallback, subject-level and dataset-level QC reports, DPABI contract without execution.

Unsupported: real medical image preprocessing, DPABI execution, DPARSF_run/DPARSFA_run, ALFF/fALFF/ReHo, rawdata modification.

## Inputs/Outputs

Input: `derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii`, `derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json`
Output: `filt_resid_swr*.nii`, `temporal_filtering_result.json`, `temporal_filtering_qc.json/.md`, `reports/rsfmri/temporal_filtering_qc_summary.json/.md`, `work/dpabi/contracts/temporal_filtering_backend_contract.json`

## Parameters

Default: low_hz=0.01, high_hz=0.08, TR from slice_timing_qc.json or explicit fallback.

## Safety Rules

Only derivative nuisance-regressed functional input. Do not modify rawdata. Do not execute DPABI. Write outputs only under derivatives, work, reports, logs.
