# Release Readiness Specification

This document defines the MVP release checklist and deployment readiness scanner.

## Goals

The release readiness scanner should verify that MedImage Agent is ready for demo, handoff, or deployment preparation.

It should check:

- required project structure
- required specs
- backend tools
- API routes
- frontend panels
- unit tests
- reproducibility bundle
- artifact browser
- experiment dashboard
- DPABI safety gates
- template approval defaults
- blocked DPABI full-pipeline execution paths

## Scope

Supported in this step:

- static release checklist
- file existence checks
- safety string scan
- generated template safety check
- reproducibility bundle check
- artifact index check
- experiment dashboard check
- API and frontend visibility
- Markdown readiness report
- lightweight unit test

Unsupported in this step:

- automatic deployment
- cloud upload
- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- real medical image processing
- rawdata modification
- file deletion

## Outputs

```text
work/release/release_checklist.yaml
work/release/release_readiness.json
reports/release/release_readiness_report.md
```

## Readiness Status

- **READY**: no blockers and only minor warnings
- **WARNING**: no blockers but meaningful warnings exist
- **BLOCKED**: at least one deployment blocker exists

## Required Safety Guarantees

The scanner should verify:

- generated templates default to approved=false
- DPARSF_run / DPARSFA_run are blocked in wrapper contracts
- template library does not promote full pipeline runners
- artifact browser rejects path traversal
- bundles exclude rawdata and third_party
- release scanner itself does not execute pipelines or MATLAB

## Safety Rules

- Do not execute pipelines.
- Do not launch MATLAB.
- Do not run DPABI.
- Do not call DPABI GUI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
- Do not deploy automatically.
