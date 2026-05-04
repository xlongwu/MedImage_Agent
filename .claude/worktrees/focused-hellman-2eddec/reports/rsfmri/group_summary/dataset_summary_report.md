# rs-fMRI Group Dataset Summary

## Overview

- Subjects total: 2
- Subjects with QC: 2
- Warnings: 2
- Errors: 0

## Key Metrics

- mean_fd: None
- max_fd: None
- gm_volume_mm3: None
- wm_volume_mm3: None
- csf_volume_mm3: None
- normalization_finite_fraction: None
- smoothing_variance_ratio: None
- regression_variance_ratio: None
- filtering_retained_frequency_fraction: None
- filtering_variance_ratio: None
- alff_mean: 3.739657402038574
- falff_mean: 1.0955212116241455
- reho_mean: 0.061445336788892746
- reho_valid_voxel_count: 8.0
- fc_roi_count: 2.0
- fc_empty_roi_count: 0.0
- fc_diagonal_mean: 1.0

## Stage Status Counts

| Stage | PASS | WARNING | FAIL | MISSING |
|---|---:|---:|---:|---:|
| slice_timing | 0 | 0 | 0 | 2 |
| motion | 0 | 0 | 0 | 2 |
| registration | 0 | 0 | 0 | 2 |
| segmentation | 0 | 0 | 0 | 2 |
| normalization | 0 | 0 | 0 | 2 |
| smoothing | 0 | 0 | 0 | 2 |
| confounds | 0 | 0 | 0 | 2 |
| nuisance_regression | 0 | 0 | 0 | 2 |
| temporal_filtering | 2 | 0 | 0 | 0 |
| alff_falff | 0 | 2 | 0 | 0 |
| reho | 2 | 0 | 0 | 0 |
| functional_connectivity | 2 | 0 | 0 | 0 |

## Subject Table

| Subject | FC | ALFF/fALFF | ReHo | Warnings | Errors |
|---|---|---|---|---:|---:|
| sub-001 | PASS | WARNING | PASS | 1 | 0 |
| sub-002 | PASS | WARNING | PASS | 1 | 0 |

## Safety

Read-only aggregation. No rawdata modification, no SPM/MATLAB/DPABI/GPU execution, no statistical inference.
