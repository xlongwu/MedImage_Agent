from __future__ import annotations

import json, subprocess
from pathlib import Path
from typing import Any
from src.backend.app.tools.smoothing_qc import compute_smoothing_qc_for_subject


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _find_normalized_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists(): return None
    preferred = func_dir / f"wra{subject_id}_bold.nii"
    if preferred.exists(): return preferred
    candidates = []
    for path in sorted(func_dir.glob("wr*.nii")):
        name = path.name
        if name.startswith("wmean") or name.startswith("swr") or name.startswith("rp_"): continue
        candidates.append(path)
    return candidates[0] if candidates else None


def _is_safe_normalized_input(path: Path, subject_id: str, derivatives_dir: str) -> bool:
    func_dir = (Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func").resolve()
    try: path.resolve().relative_to(func_dir)
    except ValueError: return False
    name = path.name
    return name.startswith("wr") and name.endswith(".nii") and not name.startswith("wmean") and not name.startswith("swr") and not name.startswith("rp_")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None


def run_spm_smooth_subject(
    matlab_command: str, spm_dir: str, subject_id: str, derivatives_dir: str,
    work_dir: str, log_dir: str, approved: bool = False,
    fwhm: list[float] | None = None, matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {"ok": False, "node_id": "spm_smooth_subject", "backend": "matlab-spm", "subject_id": subject_id, "outputs": [], "warnings": [], "errors": ["SPM smoothing requires approved=true."]}

    fwhm = fwhm or [6.0, 6.0, 6.0]
    input_func = _find_normalized_functional(subject_id, derivatives_dir)
    if not input_func:
        return {"ok": False, "node_id": "spm_smooth_subject", "backend": "matlab-spm", "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"No normalized functional input found under derivatives/rsfmri_preproc/{subject_id}/func."]}
    if not _is_safe_normalized_input(input_func, subject_id, derivatives_dir):
        return {"ok": False, "node_id": "spm_smooth_subject", "backend": "matlab-spm", "subject_id": subject_id, "outputs": [], "warnings": [], "errors": [f"Unsafe smoothing functional input: {input_func}"]}

    func_dir = input_func.parent
    log_path = Path(log_dir); log_path.mkdir(parents=True, exist_ok=True)
    stdout_log = log_path / f"{subject_id}_spm_smooth_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_smooth_stderr.log"
    result_json = func_dir / "spm_smoothing_result.json"
    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_smooth_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(input_func.resolve()))}', "
        f"'{_matlab_quote(json.dumps(fwhm))}', "
        f"'{_matlab_quote(str(result_json.resolve()))}'); "
        "catch ME, disp(getReport(ME)); exit(1); end; exit(0);"
    )

    cmd = [matlab_command, "-nodisplay", "-nosplash", "-r", matlab_code]
    with stdout_log.open("w", encoding="utf-8") as out, stderr_log.open("w", encoding="utf-8") as err:
        completed = subprocess.run(cmd, stdout=out, stderr=err, check=False)

    data = _read_json(result_json) or {"ok": False, "errors": ["SPM smoothing did not produce result JSON."]}
    data["node_id"] = "spm_smooth_subject"
    data["backend"] = "matlab-spm"; data["subject_id"] = subject_id
    data["returncode"] = completed.returncode; data["input_func"] = str(input_func)
    data["stdout_log"] = str(stdout_log); data["stderr_log"] = str(stderr_log); data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False; data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    qc_outputs = []
    smoothed_file = data.get("smoothed_file")
    if smoothed_file:
        qc = compute_smoothing_qc_for_subject(subject_id=subject_id, input_nii=str(input_func), smoothed_nii=smoothed_file, derivatives_dir=derivatives_dir, fwhm=fwhm)
        data["smoothing_qc"] = qc; qc_outputs = qc.get("outputs", [])

    outputs = []
    if data.get("smoothed_file"): outputs.append(data["smoothed_file"])
    outputs.extend(qc_outputs); outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])
    data["outputs"] = sorted(set(outputs))
    return data
