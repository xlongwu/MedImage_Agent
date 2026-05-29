# MedImage Agent User Guide

## Quick Start

```bash
# Start backend
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000

# Start frontend
cd src/frontend && npm run dev
```

## Running rs-fMRI Pipelines

Each pipeline is defined as a YAML file in `examples/`. Run with:

```bash
python -m src.backend.app.tools.run_rsfmri_{pipeline_name}_cli --approve
```

For pipelines requiring MATLAB/SPM, the `--approve` flag is mandatory. Without it, SPM steps fail safely.

## API Access

All results are accessible via REST API at `http://127.0.0.1:8000`. Key endpoints:
- Preprocessing: `/api/rsfmri/spm-{stage}`
- QC: Motion, Registration, Tissue, Normalization, Smoothing
- Post-processing: Nuisance Regression, Temporal Filtering
- Metrics: ALFF/fALFF, ReHo, Functional Connectivity
- Reports: Group Summary, Report Export, Report Validator
- Release: `/api/release-readiness`

## Safety

This project processes synthetic data only. No real medical images are handled. SPM/MATLAB steps require explicit approval. DPABI and GPU backends are contract-only.
