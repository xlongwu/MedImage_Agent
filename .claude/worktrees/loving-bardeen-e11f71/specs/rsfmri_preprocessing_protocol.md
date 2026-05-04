# rs-fMRI Preprocessing Protocol

This document defines the MVP rs-fMRI preprocessing protocol for MedImage Agent.

## Goal

The goal is to define a transparent, auditable, and extensible preprocessing pipeline for resting-state fMRI datasets.

This protocol is not a clinical recommendation. It is an engineering protocol used to structure preprocessing execution, QC, acceleration, and reporting.

## Core Pipeline

The MVP rs-fMRI preprocessing pipeline contains the following stages:

1. Dataset inspection
2. Subject/session/run indexing
3. Anatomical-functional pairing
4. Slice timing correction
5. Realignment
6. Motion QC
7. Coregistration
8. Segmentation
9. Normalization
10. Spatial smoothing
11. Nuisance regression
12. Temporal filtering
13. ALFF
14. fALFF
15. ReHo
16. Functional connectivity preparation
17. Subject-level QC
18. Dataset-level report

## Step Categories

Each step belongs to one of these categories:

- data_inspection
- spm_preprocessing
- dpabi_preprocessing
- python_qc
- gpu_candidate
- reporting

## Backend Types

Supported backend types:

- python
- matlab-spm
- matlab-dpabi
- python-gpu
- report

## Parallelization Levels

Supported parallelization levels:

- project
- subject
- session
- run
- volume

## Safety Rules

The protocol must not:

- modify rawdata
- call DPARSF_run
- call DPARSFA_run
- call DPABI GUI
- execute full DPABI pipelines without explicit approval
- delete files
- overwrite source data

## QC Metrics

The protocol should support at least:

- framewise displacement
- mean FD
- max FD
- number of high-motion frames
- DVARS
- tSNR
- registration quality
- normalization quality
- output existence
- shape consistency
- voxel size consistency
- subject-level pass/warning/fail state

## Agent Responsibilities

The preprocessing agent should:

1. inspect the dataset
2. infer a preprocessing plan
3. explain the plan
4. request approval before execution
5. execute approved steps
6. monitor progress
7. diagnose failures
8. collect QC metrics
9. generate reports

## Current Step Scope

This step only defines the protocol, registry, DAG, and plan report.

It does not execute real preprocessing.
