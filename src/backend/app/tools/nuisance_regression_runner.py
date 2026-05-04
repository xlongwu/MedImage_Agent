from __future__ import annotations
from pathlib import Path
from typing import Any
from src.backend.app.tools.confound_matrix import build_confound_matrix_for_subject
from src.backend.app.tools.dpabi_nuisance_contract import write_dpabi_nuisance_regression_contract
from src.backend.app.tools.nuisance_regression import run_python_nuisance_regression_subject

def _find_smoothed_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists(): return None
    preferred = func_dir / f"swra{subject_id}_bold.nii"
    if preferred.exists(): return preferred
    candidates = sorted(func_dir.glob("swr*.nii"))
    return candidates[0] if candidates else None

def _find_motion_params(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists(): return None
    candidates = sorted(func_dir.glob("rp_*.txt"))
    return candidates[0] if candidates else None

def _is_safe_subject_func_path(path: Path, subject_id: str, derivatives_dir: str) -> bool:
    func_dir = (Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func").resolve()
    try: path.resolve().relative_to(func_dir)
    except ValueError: return False
    return True

def run_nuisance_regression_subject(
    subject_id: str, derivatives_dir: str, backend: str = "python",
    model: str = "friston24", include_intercept: bool = True,
    include_linear_trend: bool = True, include_global_signal: bool = False,
) -> dict[str, Any]:
    if backend == "dpabi_contract":
        contract = write_dpabi_nuisance_regression_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract
    if backend != "python":
        return {"ok": False, "node_id": "nuisance_regression_subject", "backend": backend, "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"Unsupported nuisance regression backend: {backend}"]}

    input_func = _find_smoothed_functional(subject_id, derivatives_dir)
    if not input_func:
        return {"ok": False, "node_id": "nuisance_regression_subject", "backend": "python", "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"No smoothed functional input found for subject {subject_id}."]}
    if not _is_safe_subject_func_path(input_func, subject_id, derivatives_dir) or not input_func.name.startswith("swr"):
        return {"ok": False, "node_id": "nuisance_regression_subject", "backend": "python", "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"Unsafe smoothed functional input: {input_func}"]}

    motion = _find_motion_params(subject_id, derivatives_dir)
    if not motion:
        return {"ok": False, "node_id": "nuisance_regression_subject", "backend": "python", "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"No motion parameter file found for subject {subject_id}."]}
    if not _is_safe_subject_func_path(motion, subject_id, derivatives_dir):
        return {"ok": False, "node_id": "nuisance_regression_subject", "backend": "python", "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"Unsafe motion parameter input: {motion}"]}

    confounds = build_confound_matrix_for_subject(subject_id=subject_id, motion_parameter_file=str(motion), output_dir=derivatives_dir, model=model, include_intercept=include_intercept, include_linear_trend=include_linear_trend, include_global_signal=include_global_signal)
    if not confounds.get("ok"): confounds["node_id"] = "nuisance_regression_subject"; return confounds

    regression = run_python_nuisance_regression_subject(subject_id=subject_id, input_nii=str(input_func), confounds_tsv=confounds["confounds_tsv"], derivatives_dir=derivatives_dir)
    outputs = []; outputs.extend(confounds.get("outputs", [])); outputs.extend(regression.get("outputs", []))
    return {"ok": bool(regression.get("ok")), "node_id": "nuisance_regression_subject", "backend": "python", "subject_id": subject_id, "input_nii": str(input_func), "motion_parameter_file": str(motion), "confounds": confounds, "regression": regression, "outputs": sorted(set(outputs)), "warnings": confounds.get("warnings", []) + regression.get("warnings", []), "errors": confounds.get("errors", []) + regression.get("errors", [])}
