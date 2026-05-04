# rs-fMRI Slice Timing to Realignment Chain Specification

This document defines the MVP chained rs-fMRI core preprocessing pipeline:

```text
Slice Timing Correction → Realignment → Motion QC
```

## Goals

The goal is to connect existing SPM slice timing and SPM realignment wrappers into a continuous synthetic rs-fMRI preprocessing chain.

The pipeline should:

- generate or use synthetic BIDS-like rs-fMRI data
- validate acquisition metadata
- run approved SPM slice timing correction
- use slice-timing-corrected BOLD as realignment input
- run approved SPM realignment
- compute motion QC from SPM motion parameters
- generate subject-level and dataset-level chain reports

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM slice timing
- approved SPM realignment
- derivative input handoff from slice timing to realignment
- motion QC
- chain-level subject summary
- chain-level dataset report
- API and frontend visibility
- lightweight unit test

Unsupported in this step:

- real medical image preprocessing
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
- source modification in SPM / DPABI
- file deletion

## Inputs

```
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.nii or *.nii.gz
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.json
work/dataset_index/dataset_index.json
```

## Intermediate Outputs

```
derivatives/rsfmri_preproc/{subject_id}/func/{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/a{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/r{sub}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/mean{sub}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/rp_{sub}_bold.txt
```

## QC Outputs

```
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json
derivatives/rsfmri_qc/{subject_id}/motion_qc.json
reports/rsfmri/st_realign_motion_chain_summary.json
reports/rsfmri/st_realign_motion_chain_report.md
```

## Chain Rules

- Realignment should use a{sub}_bold.nii when slice timing is enabled and successful.
- Realignment may fall back to raw synthetic BOLD only when use_slice_timing_output=false.
- Derivative input must remain under derivatives/rsfmri_preproc.
- Rawdata must never be modified.
- Realignment must not accept arbitrary derivative files.
- Both SPM stages require explicit approval.

## Safety Rules

- Execution requires approved=true.
- Only synthetic BIDS-like input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not call DPABI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
