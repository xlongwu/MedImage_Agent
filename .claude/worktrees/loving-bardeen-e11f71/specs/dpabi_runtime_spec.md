# DPABI Runtime Specification

This document defines the MVP DPABI integration layer for MedImage Agent.

## Goals

The DPABI runtime should safely inspect and prepare DPABI integration without running full preprocessing.

The MVP supports:

- DPABI path validation
- MATLAB addpath(genpath(dpabi_dir))
- function discovery
- capability summary
- dry-run wrapper plan
- config template generation
- pipeline node integration
- API and frontend visibility

## Scope

Supported in this step:

- DPABI capability inspection
- common function discovery
- dry-run plan generation
- wrapper config template
- JSON output
- Markdown report

Unsupported in this step:

- full DPABI preprocessing
- DPARSF batch execution
- GUI automation
- real medical image preprocessing
- modifying DPABI source code
- modifying rawdata
- deleting files
- parallel DPABI execution
- GPU DPABI execution

## Outputs

```text
work/dpabi/dpabi_capabilities.json
work/dpabi/dpabi_wrapper_config_template.yaml
work/dpabi/dpabi_dry_run_plan.json
reports/dpabi/dpabi_capability_report.md
```

## Capability Categories

- dpabi_entrypoint
- rest_tools
- y_tools
- nifti_io
- preprocessing_wrappers
- gui_entrypoints
- unknown

## Safety Rules

- Do not run full DPABI preprocessing.
- Do not call DPABI GUI automatically.
- Do not modify DPABI source.
- Do not modify rawdata.
- Do not delete files.
- Treat this as a dry-run integration scaffold.
