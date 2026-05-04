# Artifact Browser and File Preview Specification

This document defines the MVP artifact browser for MedImage Agent.

## Goals

The artifact browser provides a unified view of generated files.

It should:

- scan allowed artifact directories
- index generated files
- classify artifacts by category
- support safe preview of text-like files
- support metadata-only preview for NIfTI files
- expose index and preview through API
- render artifact browser in the frontend

## Scope

Supported in this step:

- scan work
- scan reports
- scan logs
- scan derivatives
- scan examples pipeline/config YAML files
- generate artifact index JSON
- preview JSON, YAML, Markdown, CSV, TXT, LOG, HTML as text
- preview NIfTI metadata only
- frontend artifact list and preview
- lightweight unit test

Unsupported in this step:

- arbitrary filesystem browsing
- file editing
- file deletion
- rawdata modification
- binary file streaming
- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- executing HTML or JavaScript reports

## Outputs

```text
work/artifacts/artifact_index.json
```

## Allowed Roots

- work/
- reports/
- logs/
- derivatives/
- examples/

## Excluded Paths

- third_party/
- .git/
- node_modules/
- __pycache__/
- rawdata/

The browser should avoid indexing rawdata paths by default, even synthetic rawdata, because the artifact browser is for generated artifacts.

## Preview Rules

### Text-like files:

- .json
- .yaml
- .yml
- .md
- .txt
- .log
- .csv
- .tsv
- .html

### NIfTI metadata-only files:

- .nii
- .nii.gz

Unsupported files should return metadata only.

## Size Limits

- Maximum text preview size: 200 KB
- Maximum indexed file size metadata only: no hard limit
- Do not return binary content

## Safety Rules

- Do not execute files.
- Do not serve arbitrary filesystem paths.
- Do not follow path traversal.
- Do not modify files.
- Do not delete files.
- Do not read rawdata.
- Do not execute HTML or JavaScript.

## API Endpoints

```
GET  /api/artifacts          - Get artifact index
POST /api/artifacts/refresh  - Refresh artifact index
POST /api/artifacts/preview  - Preview artifact file
```

## Workflow

1. **Scan** - Scan allowed directories
2. **Index** - Build artifact index with metadata
3. **Classify** - Categorize artifacts by type
4. **Preview** - Safe preview of text files and NIfTI metadata
5. **Browse** - Frontend artifact list and filtering
