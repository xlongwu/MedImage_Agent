# SPM Slice Timing Correction Specification

This document defines the MVP SPM slice timing correction and acquisition metadata QC stage for rs-fMRI preprocessing.

## Goals

The goal is to execute SPM slice timing correction on synthetic rs-fMRI BOLD data and validate acquisition timing metadata.

This step prepares corrected functional time series for later realignment and downstream preprocessing.

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM slice timing correction
- BIDS sidecar metadata parsing
- RepetitionTime validation
- SliceTiming validation
- conversion from BIDS SliceTiming to SPM slice order
- fallback user parameters
- subject-level metadata QC JSON / Markdown
- dataset-level slice timing summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- realignment
- coregistration
- segmentation
- normalization
- smoothing
- nuisance regression
- temporal filtering
- ALFF / fALFF / ReHo
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- rawdata modification
- source code modification in SPM / DPABI
- file deletion

## Inputs

```text
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.nii or *.nii.gz
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.json
work/dataset_index/dataset_index.json
examples/project_config_dataset.yaml
```

## Outputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/a{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/spm_slice_timing_result.json
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.md
reports/rsfmri/slice_timing_qc_summary.json
reports/rsfmri/slice_timing_qc_report.md
```

## QC Metrics

- metadata_found
- repetition_time
- num_slices
- slice_timing_count
- slice_order
- reference_slice
- acquisition_duration
- tr_consistency
- slice_timing_status

## Safety Rules

- Execution requires approved=true.
- Only synthetic BIDS-like input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not call DPABI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
