# DPABI Template Instantiation Specification

This document defines the MVP DPABI template instantiation and approved synthetic execution stage.

## Goals

The template instantiator turns a validated DPABI pipeline template into a concrete, reviewable pipeline instance.

It should:

- read the DPABI template index
- select a template by template_id
- create an instantiated pipeline YAML
- create an instance manifest JSON
- create a review Markdown file
- keep approved=false by default
- require explicit approved=true before execution
- execute only synthetic BIDS-like pipelines
- record approval and execution summary

## Scope

Supported in this step:

- template selection
- safe template path validation
- run_id override
- function_name override if allowlisted
- fwhm override
- subject list override
- scheduler override
- dry-run instantiation
- approved synthetic execution
- API and frontend visibility
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
- production template registry

## Inputs

```text
work/dpabi/templates/dpabi_template_index.json
work/dpabi/templates/pipelines/{template_id}.yaml
examples/project_config_dataset.yaml
```

## Outputs

```text
work/dpabi/template_instances/{instance_id}/pipeline.yaml
work/dpabi/template_instances/{instance_id}/instance_manifest.json
work/dpabi/template_instances/{instance_id}/instance_review.md
work/dpabi/template_instances/{instance_id}/approval.json
work/dpabi/template_instances/{instance_id}/execution_summary.json
reports/dpabi/dpabi_template_instance_report.md
```

## Approval Rules

- Instantiation does not require approval.
- Execution requires approved=true.
- The instantiated pipeline must default to approved=false.
- The executor may set approved=true only after explicit request.
- Full DPABI execution remains disallowed.

## Safety Rules

- Do not execute generated instances automatically.
- Do not execute without approved=true.
- Do not run DPARSF_run.
- Do not run DPARSFA_run.
- Do not call DPABI GUI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
- Only synthetic BIDS-like templates may be instantiated.
