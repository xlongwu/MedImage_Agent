# DPABI Pipeline Template Library Specification

This document defines the MVP DPABI pipeline template library.

## Goals

The template library converts validated DPABI wrapper functions into reusable pipeline templates.

It should:

- read the wrapper compatibility matrix
- find promotable wrappers
- generate pipeline templates
- generate a template index
- generate a template manifest
- generate a Markdown report
- preserve approval requirements
- prevent accidental full DPABI execution

## Scope

Supported in this step:

- template generation from PROMOTABLE_TO_TEMPLATE wrappers
- subject-level DPABI single-function wrapper templates
- synthetic BIDS-like data only
- approved=false by default
- template index JSON
- template manifest YAML
- Markdown report
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
- automatic template execution

## Inputs

```text
work/dpabi/dpabi_wrapper_compatibility_matrix.json
```

## Outputs

```text
work/dpabi/templates/dpabi_template_index.json
work/dpabi/templates/dpabi_template_manifest.yaml
work/dpabi/templates/pipelines/{template_id}.yaml
reports/dpabi/dpabi_template_library_report.md
```

## Template Rules

Every generated pipeline template must:

- use approved=false by default
- require explicit future approval
- only allow synthetic BIDS-like data
- only use allowlisted wrapper functions
- include environment_check
- include data_inspection
- include dpabi_signature_probe
- include dpabi_wrapper_contracts
- include dpabi_subject_smooth
- include dpabi_subject_wrapper_report
- not include DPARSF_run
- not include DPARSFA_run
- not include DPABI GUI calls

## Safety Rules

- Do not execute generated templates.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
- Do not promote blocked functions.
- Do not promote GUI entrypoints.
- Do not promote full pipeline runners.
