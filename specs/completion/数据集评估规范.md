# Dataset Evaluation Specification

This document defines the MVP dataset-level evaluation behavior.

## Scope

The Dataset Evaluator aggregates subject-level preprocessing and QC results.

The MVP supports:

- dataset_index.json
- subject_table.csv
- subject_qc.json files
- subject-level node states
- dataset-level summary JSON
- subject-level QC table CSV
- exclusion recommendation CSV
- Markdown report
- HTML report

Unsupported in this step:

- PDF generation
- statistical group comparison
- clinical diagnosis
- disease inference
- GPU metrics
- real medical imaging interpretation
- UI

## Input Files

Expected inputs:

```text
work/dataset_index/dataset_index.json
work/dataset_index/subject_table.csv
work/states/{run_id}/{subject_id}/spm_smooth_subject.json
work/states/{run_id}/{subject_id}/subject_qc.json
derivatives/qc/{subject_id}/subject_qc.json
```

## Output Files

The Dataset Evaluator writes:

```text
reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/subject_qc_table.csv
reports/dataset_evaluation/exclusion_recommendations.csv
reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html
```

## Subject Recommendation Categories

- **INCLUDE**: subject passed preprocessing and QC
- **MANUAL_REVIEW**: subject has warnings or suspicious metrics
- **EXCLUDE**: subject failed preprocessing or QC

## MVP Exclusion Rules

A subject should be **EXCLUDE** if:

- preprocessing failed
- subject_qc failed
- smoothed output is missing
- nan_count > 0
- finite_voxel_count == 0

A subject should be **MANUAL_REVIEW** if:

- QC metrics are missing
- std is 0 or null
- shape is missing
- subject status in dataset_index is not COMPLETE

Otherwise:

- **INCLUDE**

## Dataset Quality Score

MVP score ranges from 0 to 100.

Suggested scoring:

- Data completeness: 30 points
- Preprocessing success: 30 points
- QC pass rate: 30 points
- Warning penalty: 10 points

This score is only an engineering QC indicator. It is not a clinical or scientific conclusion.

## Safety Rules

- Do not modify rawdata.
- Do not delete files.
- Do not modify derivatives except writing reports.
- Do not make clinical conclusions.
- Do not infer disease status.
- Always distinguish automatic recommendation from human review.
