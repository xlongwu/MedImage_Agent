---
name: dataset-evaluation
description: Aggregate all subject-level QC metrics into a dataset-level evaluation with exclusion recommendations and downstream analysis readiness assessment.
---

# Dataset Evaluation Skill

## Inputs
- `dataset_index.json`
- All subject-level QC JSON files
- `participants.tsv` / phenotype data (optional)
- Preprocessing status per subject

## Outputs
- `dataset_summary.json`
- `subject_qc_table.csv`
- `exclusion_recommendations.csv`
- `dataset_evaluation_report.html` / `.md`
- Figures directory

## Report Sections
1. Executive Summary
2. Dataset Overview
3. Data Completeness
4. Preprocessing Success Rate
5. Motion QC Summary
6. Registration / Normalization QC Summary
7. Signal Quality Assessment (tSNR, ALFF, fALFF, ReHo)
8. Group / Site / Scanner Balance
9. Outlier Subjects
10. Recommended Exclusion List
11. Downstream Analysis Readiness
12. Reproducibility Information
13. Appendix

## Rules
- Do not make clinical diagnoses.
- Separate subjects into Include / Manual Review / Exclude.
- Always report thresholds used.
- Always preserve subject-level traceability.
- Frame exclusion as "recommended for review", not automatic removal.
