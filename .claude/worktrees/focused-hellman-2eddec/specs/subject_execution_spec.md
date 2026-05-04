# Subject-Level Execution Specification

This document defines the MVP subject-level execution behavior.

## Scope

The MVP supports sequential subject-level execution only.

Supported subject-level nodes:

- spm_smooth_subject
- subject_qc

Unsupported in this step:

- parallel execution
- GPU execution
- Slurm execution
- DPABI preprocessing
- real medical imaging data
- UI
- database

## Subject Selection

Subject-level nodes should run only on subjects whose dataset_index status is:

```text
COMPLETE
```

Subjects with these statuses are skipped:

- MISSING_T1W
- MISSING_BOLD
- INCOMPLETE
- WARNING

## State Files

Project-level node state:

```text
work/states/{run_id}/{node_id}.json
```

Subject-level node state:

```text
work/states/{run_id}/{subject_id}/{node_id}.json
```

Example:

```text
work/states/run_subject_preprocess_001/sub-001/spm_smooth_subject.json
work/states/run_subject_preprocess_001/sub-001/subject_qc.json
```

## Derivatives Layout

SPM smoothing outputs should be written to:

```text
derivatives/spm_smooth/{subject_id}/func/
```

Example:

```text
derivatives/spm_smooth/sub-001/func/sub-001_task-rest_bold_smoothed.nii
```

## Minimal Subject QC

For each smoothed BOLD output, compute:

- shape
- dtype
- mean
- std
- min
- max
- nan_count
- finite_voxel_count

## Safety Rules

- Do not modify rawdata.
- Do not delete files.
- Do not modify third_party.
- Write intermediate files only to work/.
- Write outputs only to derivatives/.
- Write logs only to logs/.
