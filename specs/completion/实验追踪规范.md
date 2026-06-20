# Experiment Tracking and Run Comparison Specification

This document defines the MVP multi-run experiment tracking system for MedImage Agent.

## Goals

The experiment tracker should provide a unified view of pipeline runs and generated reports.

It should:

- index pipeline runs
- index DPABI template instance runs
- index report artifacts
- create experiment records
- compare selected runs
- generate comparison JSON
- generate Markdown comparison report
- expose data through API and frontend dashboard

## Scope

Supported in this step:

- scan work/pipeline_runs
- scan work/dpabi/template_instances
- scan reports/dataset_evaluation
- scan reports/gpu_benchmark
- scan reports/dpabi
- scan reports/validation
- create experiment records
- compare multiple run summaries
- compare status, duration, scheduler, node status, output counts
- API and frontend visibility
- lightweight unit test

Unsupported in this step:

- running pipelines
- running MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- GUI automation
- real medical image processing
- rawdata modification
- DPABI source modification
- deletion of files
- production-grade MLflow replacement

## Outputs

```text
work/experiments/run_index.json
work/experiments/records/{experiment_id}.json
reports/experiments/{experiment_id}_comparison.json
reports/experiments/{experiment_id}_comparison_report.md
```

## Run Types

- pipeline_run
- dpabi_template_instance
- dataset_evaluation
- gpu_benchmark
- dpabi_report
- validation_report
- unknown

## Comparison Metrics

- run_id
- pipeline_id
- status
- started_at
- ended_at
- duration_seconds
- scheduler_mode
- max_workers
- matlab_max_workers
- nodes_total
- nodes_success
- nodes_failed
- outputs_count
- warnings_count
- errors_count

## Safety Rules

- Do not execute pipelines.
- Do not launch MATLAB.
- Do not run DPABI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
- Read and summarize existing artifacts only.
