---
name: bids-inspection
description: Scan and validate BIDS / BIDS-like NIfTI datasets for completeness, naming, metadata, and NIfTI readability.
---

# BIDS Inspection Skill

## Inputs
- `rawdata/` directory
- `participants.tsv` (optional)
- `dataset_description.json` (optional)

## Outputs
- `dataset_index.json`
- `data_completeness_report.json`
- `missing_files.csv`
- `naming_issues.csv`

## Procedure
1. Scan rawdata for subject/session/run hierarchy.
2. Validate BIDS naming conventions.
3. Check T1w, BOLD, DWI, fmap presence.
4. Verify NIfTI files are readable (nibabel).
5. Extract TR, slice timing, phase encoding direction from sidecar JSON.
6. Check participants.tsv / phenotype.csv linkage.

## Rules
- Do not modify rawdata.
- Report all issues before any processing.
- Flag missing critical files (T1w, BOLD) as BLOCKER.
- Flag naming issues as WARNING.
