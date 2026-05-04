# MedImage Agent Architecture

## Overview

MedImage Agent is a full-stack medical image processing pipeline orchestration system focused on rs-fMRI preprocessing and analysis. It combines Python-based computation, MATLAB/SPM neuroimaging tools, and DPABI wrappers into a unified pipeline runtime with web-based monitoring.

## System Components

### Backend (Python/FastAPI)
- **Pipeline Runtime**: Sequential/parallel execution engine with dependency resolution via `pipeline_executor.py`
- **Node Registry**: Pluggable architecture mapping node IDs to runner functions
- **Agent Runtime**: Plan/Execute/Approve mechanism for controlled MATLAB/SPM execution
- **API Layer**: FastAPI endpoints exposing all pipeline stages, QC results, and dashboards

### SPMMATLAB Integration
- MATLAB wrappers for SPM12: slice timing, realignment, coregistration, segmentation, normalization, smoothing
- Safety: `approved=true` required; only synthetic BIDS input; no rawdata modification

### Python Processing Modules
- Motion QC, nuisance regression (Friston24), temporal filtering (FFT band-pass), ALFF/fALFF, ReHo (KCC), functional connectivity (ROI-based)
- GPU candidate backend contracts for future acceleration
- DPABI backend contracts for future MATLAB integration

### Frontend (React/TypeScript)
- Modular monitoring panels for each pipeline stage
- Real-time run monitoring, error diagnosis, retry mechanisms
- QC visualization and report viewing

### Report & Export Layer
- Group-level dataset summary and cross-subject dashboard
- Report package exporter with SHA256 checksums and safety manifest
- Report package validator for integrity audits
- Release readiness checker

## Safety Principles
- All SPM/MATLAB execution requires explicit approval
- Derivative-only output (never modify rawdata)
- Contract-only DPABI/GPU backends (no execution)
- Path safety enforcement on all file operations
