# Safety and Limitations

## Safety Rules

- **Approval Gate**: All SPM/MATLAB steps require `approved=true`; default is `false`
- **Synthetic Data Only**: Input path must contain `examples/synthetic_bids/rawdata`; all other inputs rejected
- **Derivative-Only Output**: Writes only under `derivatives/`, `work/`, `reports/`, `logs/`, `exports/`
- **No Rawdata Modification**: Raw data files are never read, written, or deleted
- **No DPABI Execution**: DPABI functions blocked; single-function wrappers only; no DPARSF_run/DPARSFA_run/DPABI GUI
- **GPU Execution**: GPU acceleration is available via CuPy backend with `gpu_mode` (prefer/require/off). `require_gpu=True` fails safely when GPU unavailable. All GPU nodes auto-fallback to CPU NumPy when `prefer_gpu=True` (default).
- **No File Deletion**: Files are never deleted by any pipeline step

## Limitations

- **Not Clinical**: This is engineering validation for synthetic data; no clinical interpretation or statistical inference
- **Synthetic Data Only**: Synthetic BIDS volumes used by default; not representative of real anatomy or fMRI signal
- **No Group Statistics**: Group-level aggregation is read-only engineering summary, not statistical testing
- **GPU Optional**: GPU acceleration requires CuPy installation (`pip install cupy-cuda12x`). Without CuPy, all modules fall back to CPU NumPy automatically.
- **Contract-Only DPABI**: DPABI contracts are placeholders; real DPABI execution not implemented
- **MATLAB/SPM Required**: SPM preprocessing stages require MATLAB + SPM12 installation (contract-only without MATLAB)
- **Python-Only Postprocessing**: Nuisance regression, filtering, ALFF/fALFF, ReHo, FC are Python/CuPy-only
