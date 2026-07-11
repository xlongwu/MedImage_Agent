# Experiment Dashboard Specification

This document defines the MVP experiment dashboard and trend analytics layer.

## Goals

The dashboard should turn indexed run records into visual and summary metrics.

It should provide:

- run count summary
- status distribution
- pipeline distribution
- run duration trend
- scheduler usage distribution
- node success/failure trend
- warning/error trend
- output count trend
- latest run table

## Scope

Supported in this step:

- read work/experiments/run_index.json
- generate dashboard_data.json
- generate dashboard_data.csv
- generate dashboard_report.md
- API endpoint for dashboard data
- frontend visualization using React and SVG
- lightweight unit test

Unsupported in this step:

- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- real medical image processing
- rawdata modification
- DPABI source modification
- deletion of files
- production analytics database

## Outputs

```text
work/experiments/dashboard_data.json
work/experiments/dashboard_data.csv
reports/experiments/dashboard_report.md
```

## Dashboard Metrics

- runs_total
- success_total
- failed_total
- partial_total
- unknown_total
- mean_duration_seconds
- median_duration_seconds
- max_duration_seconds
- total_outputs
- total_warnings
- total_errors
- status_distribution
- pipeline_distribution
- scheduler_distribution
- duration_trend
- error_warning_trend
- output_trend

## Safety Rules

- Do not execute pipelines.
- Do not launch MATLAB.
- Do not run DPABI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
- Read and summarize existing artifacts only.
