# Dataset Index Specification

This document defines the dataset indexing format for MedImage Agent.

## Scope

The dataset index is a project-level summary of BIDS-like medical imaging data.

The MVP supports:

- subject-level folders: sub-xxx
- optional session folders: ses-xxx
- anatomical images: anat/*T1w.nii or anat/*T1w.nii.gz
- functional images: func/*bold.nii or func/*bold.nii.gz
- functional sidecar JSON files
- participants.tsv

The MVP does not perform preprocessing.

## Output Files

The Data Inspector node writes:

```text
work/dataset_index/dataset_index.json
work/dataset_index/data_completeness_report.json
work/dataset_index/subject_table.csv
```

## dataset_index.json

Minimal structure:

```json
{
  "dataset_root": "examples/synthetic_bids/rawdata",
  "subjects_total": 2,
  "subjects": [
    {
      "subject_id": "sub-001",
      "sessions": [
        {
          "session_id": null,
          "anat": {
            "t1w": "examples/synthetic_bids/rawdata/sub-001/anat/sub-001_T1w.nii.gz",
            "exists": true
          },
          "func": [
            {
              "bold": "examples/synthetic_bids/rawdata/sub-001/func/sub-001_task-rest_bold.nii.gz",
              "json": "examples/synthetic_bids/rawdata/sub-001/func/sub-001_task-rest_bold.json",
              "exists": true,
              "metadata": {
                "RepetitionTime": 2.0
              }
            }
          ]
        }
      ],
      "status": "COMPLETE",
      "issues": []
    }
  ]
}
```

## data_completeness_report.json

Minimal structure:

```json
{
  "subjects_total": 2,
  "subjects_complete": 2,
  "subjects_missing_t1w": 0,
  "subjects_missing_bold": 0,
  "subjects_with_issues": 0,
  "issues": []
}
```

## Subject Status

- **COMPLETE**: required T1w and BOLD files exist
- **MISSING_T1W**: no T1w file found
- **MISSING_BOLD**: no BOLD file found
- **INCOMPLETE**: multiple required files or metadata are missing
- **WARNING**: files exist but metadata or naming may be questionable

## Safety Rules

- The Data Inspector must not modify rawdata.
- The Data Inspector must not delete files.
- The Data Inspector may write only to work/, logs/, and reports/.
