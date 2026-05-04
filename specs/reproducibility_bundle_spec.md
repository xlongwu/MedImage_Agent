# Reproducibility Bundle Specification

This document defines the MVP project packaging and reproducibility bundle system.

## Goals

The reproducibility bundle should capture enough project state for review, audit, and reproduction of synthetic pipeline experiments.

It should include:

- project configs
- example pipelines
- specs
- selected reports
- selected logs
- experiment indexes
- artifact index
- DPABI wrapper metadata
- template library metadata
- environment snapshot
- file hashes
- reproducibility README

## Scope

Supported in this step:

- create reproducibility manifest
- create environment snapshot
- create artifact manifest
- copy selected text artifacts
- copy selected reports
- copy selected configs
- generate README
- generate ZIP bundle
- list bundles
- inspect bundle manifest
- API and frontend visibility
- lightweight unit test

Unsupported in this step:

- executing pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- packaging rawdata
- packaging third_party toolboxes
- packaging node_modules
- packaging .git
- packaging large binary data by default
- deleting files

## Outputs

```text
work/bundles/{bundle_id}/manifest.json
work/bundles/{bundle_id}/environment_snapshot.json
work/bundles/{bundle_id}/artifact_manifest.json
work/bundles/{bundle_id}/README.md
work/bundles/{bundle_id}/bundle.zip
work/bundles/bundle_index.json
reports/bundles/{bundle_id}_bundle_report.md
```

## Included Paths

Default included paths:

- specs/
- examples/*.yaml
- examples/*.json
- README.md
- work/experiments/
- work/artifacts/artifact_index.json
- work/dpabi/*.json
- work/dpabi/*.yaml
- work/dpabi/templates/
- reports/
- logs/*.log

## Excluded Paths

Always excluded:

- third_party/
- .git/
- node_modules/
- frontend/node_modules/
- __pycache__/
- rawdata/
- derivatives/
- *.nii
- *.nii.gz
- *.mat
- *.zip

## Safety Rules

- Do not execute pipelines.
- Do not launch MATLAB.
- Do not run DPABI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
- Do not package third_party source code.
- Do not package rawdata by default.
- Do not package large binary outputs by default.

## API Endpoints

```
GET  /api/bundles          - List all bundles
POST /api/bundles/create   - Create new bundle
GET  /api/bundles/{id}     - Inspect specific bundle
```

## Workflow

1. **Scan** - Collect candidate files from allowed paths
2. **Filter** - Exclude sensitive paths and large binaries
3. **Copy** - Copy files to bundle directory with SHA256 hashes
4. **Snapshot** - Record environment information
5. **Generate** - Create manifest, README, and ZIP
6. **Index** - Update bundle index
7. **Report** - Generate Markdown report
