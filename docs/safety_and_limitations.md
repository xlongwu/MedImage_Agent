# Safety and Limitations

## Safety Rules

- **Approval Gate**: All SPM/MATLAB steps require `approved=true`; default is `false`
- **Synthetic Data Only**: Input path must contain `examples/synthetic_bids/rawdata`; all other inputs rejected
- **Derivative-Only Output**: Writes only under `derivatives/`, `work/`, `reports/`, `logs/`, `exports/`
- **No Rawdata Modification**: Raw data files are never read, written, or deleted
- **No DPABI Execution**: DPABI functions blocked; single-function wrappers only; no DPARSF_run/DPARSFA_run/DPABI GUI
- **No GPU Execution**: GPU contracts are CONTRACT_ONLY; no CUDA/CuPy/Torch requirements
- **No File Deletion**: Files are never deleted by any pipeline step

## Limitations

- **Not Clinical**: This is engineering validation for synthetic data; no clinical interpretation or statistical inference
- **Synthetic Data Only**: 16x16x16 synthetic volumes; not representative of real anatomy
- **No Group Statistics**: Group-level aggregation is read-only engineering summary, not statistical testing
- **Contract-Only Backends**: DPABI and GPU contracts are placeholders; real execution not implemented
- **MATLAB/SPM Required**: SPM preprocessing stages require MATLAB + SPM12 installation
- **Python-Only Postprocessing**: Nuisance regression, filtering, ALFF/fALFF, ReHo, FC are Python-only
