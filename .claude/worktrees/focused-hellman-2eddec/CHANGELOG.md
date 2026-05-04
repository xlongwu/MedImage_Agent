# Changelog

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
