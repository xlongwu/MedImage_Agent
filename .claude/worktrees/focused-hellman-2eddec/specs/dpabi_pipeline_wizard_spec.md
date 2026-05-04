# DPABI Pipeline Wizard Specification

This document defines the MVP DPABI parameterized pipeline wizard.

## Goals

The wizard helps users create reviewable DPABI template instances through a structured UI.

It should:

- load available DPABI templates
- expose only safe parameters
- validate template_id, function_name, fwhm, subjects, and scheduler
- generate a preview without execution
- create a template instance without execution
- require explicit approval before execution
- display safety gates and review artifacts

## Scope

Supported in this step:

- wizard options
- parameter validation
- preview generation
- template instance creation
- approved instance execution via existing executor
- frontend wizard panel
- lightweight unit test

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- real medical image preprocessing
- rawdata modification
- DPABI source modification
- deletion of files
- production workflow builder

## Inputs

```text
work/dpabi/templates/dpabi_template_index.json
work/dpabi/dpabi_wrapper_compatibility_matrix.json
work/dpabi/template_instances/{instance_id}/...
```

## Outputs

```text
work/dpabi/template_wizard/latest_preview.json
work/dpabi/template_wizard/latest_preview.md
work/dpabi/template_instances/{instance_id}/pipeline.yaml
work/dpabi/template_instances/{instance_id}/instance_manifest.json
work/dpabi/template_instances/{instance_id}/instance_review.md
```

## Allowed Parameters

- template_id
- instance_id
- run_id
- function_name
- fwhm
- subjects
- scheduler.mode
- scheduler.max_workers
- scheduler.matlab_max_workers

## Safety Rules

- Do not execute on preview.
- Do not execute on create.
- Execute only with approved=true.
- Only allow y_Smooth and rest_Smooth.
- Only allow synthetic subject IDs such as sub-001.
- Default approved=false.
- Do not run DPARSF_run.
- Do not run DPARSFA_run.
- Do not call DPABI GUI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
