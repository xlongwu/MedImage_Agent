# Changelog

## [0.2.0] - 2026-05-23

### Added
- GPU-accelerated ReHo computation (`reho_compute.py`) with CuPy backend and z-slice chunking
- GPU-accelerated Nuisance Regression (`nuisance_regression_compute.py`) with cuBLAS GEMM
- GPU-accelerated Temporal Filtering (`temporal_filtering_compute.py`) with cuFFT batch FFT
- GPU-accelerated Functional Connectivity (`functional_connectivity_compute.py`) with matrix-based correlation
- GPU memory monitoring utility (`gpu_memory.py`) with estimation and safety checks
- 5 GPU runner modules (gpu_reho_runner, gpu_nuisance_regression_runner, gpu_temporal_filtering_runner, gpu_functional_connectivity_runner)
- 5 GPU pipeline node handlers under `src/backend/app/nodes/`
- 4 GPU pipeline YAML examples (`pipeline_gpu_*.yaml`)
- GPU-aware scheduler: `gpu_max_workers`, `gpu_mode` (prefer/require/off), `gpu_subject_nodes` in scheduler plan
- Pipeline executor GPU support: reads `gpu_supported`, injects `_gpu_info`, manages GPU worker pool
- CPU vs GPU benchmark comparison (max_abs_diff, mean_abs_diff, speedup) in all runners
- 6 new unit test files + 1 benchmark test file (22 new tests, all passing)
- ReHo and FC GPU contracts updated from CONTRACT_ONLY to IMPLEMENTED

### Changed
- All `*_runner.py` (reho, nuisance_regression, temporal_filtering, functional_connectivity) now support `backend="gpu"` dispatch
- Default scheduler config includes `gpu_max_workers: 1` and `gpu_mode: "prefer"`
- GPU max workers capped at 4 for memory safety
- Node registry expanded with 5 new GPU node entries

## [0.1.0] - 2026-05-03

### Added
- Deterministic pipeline engine with 50+ registered nodes
- Plan-then-Execute mode with Hook lifecycle (before_plan / after_plan / before_execute / after_execute / on_error)
- Full rs-fMRI preprocessing chain (Python backend): Slice Timing, Realign, Coregister, Segment, Normalize, Smooth
- Nuisance Regression (Friston24 model)
- Temporal Filtering (FFT band-pass)
- ALFF / fALFF computation
- ReHo computation (KCC)
- Functional Connectivity (ROI correlation + seed-to-voxel maps)
- Per-stage QC modules (Motion, Registration, Normalization, Tissue, Smoothing, Slice Timing, ALFF/fALFF, ReHo, FC)
- Group Dataset Summary
- Dataset Evaluation Report with Exclusion Recommendations
- SPM/DPABI wrapper contracts (contract-only mode)
- Synthetic BIDS dataset generator with SliceTiming
- Report export (ZIP + SHA256)
- Report package validator
- Release readiness checker (37 checks)
- Docs inventory
- Quickstart demo CLI
- Run history CLI
- 60+ REST API endpoints (FastAPI + CORS)
- React + TypeScript frontend (25 panels)
- Path traversal safety (path_safety.py)
- Tool permission registry (read_only, writes_files, destructive, requires_confirmation, parallel_safe)
- Error knowledge base (ERROR_KB.yaml, 5 initial error patterns)
- Error diagnosis + retry plan generation
- Background review with memory patch proposal
- Memory store (3-tier layout: global / projects / sessions)
- Skill files (9 domain skills)
- Docker demo deployment (backend + frontend + nginx)
- 36 unit tests + 3 integration tests (all passing)
- .gitignore with Python/Node/IDE/OS patterns

### Changed
- Pipeline schema made lenient: `name` and `agent` fields now default to `id` and `"system"` if omitted
- Circular imports resolved (node_registry ↔ gpu_alff_node, dpabi_template_instantiator → pipeline_executor)
- Missing `load_dataset_index` and `get_complete_subjects` functions added to pipeline_executor.py

### Fixed
- float32 JSON serialization in registration_qc.py (numpy types now converted via custom encoder)
- test_validator_passes_valid_package (MANIFEST.json hash mismatch)
- test_synthetic_bids_to_alff_integration (missing residual NIfTI file)
- test_registration_qc_computes_header_metrics (float32 JSON error)

[0.1.0]: https://github.com/anthropics/MedImage_Agent/releases/tag/v0.1.0
