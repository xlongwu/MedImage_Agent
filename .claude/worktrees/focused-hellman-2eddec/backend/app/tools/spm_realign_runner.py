from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _prepare_bold_input(input_bold: str, subject_id: str, derivatives_dir: str) -> str:
    input_path = Path(input_bold)
    out_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / f"{subject_id}_bold.nii"

    if input_path.name.endswith(".nii"):
        shutil.copyfile(input_path, output_path)
        return str(output_path)

    if input_path.name.endswith(".nii.gz"):
        try:
            import nibabel as nib
        except ImportError as exc:
            raise RuntimeError("Missing dependency: nibabel. Install with: pip install nibabel") from exc

        img = nib.load(str(input_path))
        nib.save(img, str(output_path))
        return str(output_path)

    raise RuntimeError(f"Unsupported BOLD input extension: {input_path}")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_safe_synthetic_input(input_bold: str) -> bool:
    normalized = str(input_bold).replace("\\", "/")
    return "examples/synthetic_bids/rawdata" in normalized


def _is_safe_slice_timing_derivative(input_bold: str, subject_id: str, derivatives_dir: str) -> bool:
    target = Path(input_bold).resolve()
    expected = (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    ).resolve()
    return target == expected and target.exists()


def run_spm_realign_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
    allow_derivative_input: bool = False,
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_realign_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM realignment requires approved=true."],
        }

    safe_synthetic = _is_safe_synthetic_input(input_bold)
    safe_derivative = (
        allow_derivative_input
        and _is_safe_slice_timing_derivative(input_bold, subject_id, derivatives_dir)
    )

    if not safe_synthetic and not safe_derivative:
        return {
            "ok": False,
            "node_id": "spm_realign_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                "Refusing to run SPM realignment on unsafe input.",
                f"Input was: {input_bold}",
            ],
        }

    out_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_realign_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_realign_stderr.log"
    result_json = out_dir / "spm_realign_result.json"

    if safe_derivative:
        prepared_input = input_bold
    else:
        try:
            prepared_input = _prepare_bold_input(
                input_bold=input_bold,
                subject_id=subject_id,
                derivatives_dir=derivatives_dir,
            )
        except Exception as exc:
            return {
                "ok": False,
                "node_id": "spm_realign_subject",
                "backend": "matlab-spm",
                "subject_id": subject_id,
                "outputs": [],
                "warnings": [],
                "errors": [str(exc)],
            }

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_realign_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(Path(prepared_input).resolve()))}', "
        f"'{_matlab_quote(str(result_json.resolve()))}'); "
        "catch ME, disp(getReport(ME)); exit(1); end; exit(0);"
    )

    cmd = [
        matlab_command,
        "-nodisplay",
        "-nosplash",
        "-r",
        matlab_code,
    ]

    with stdout_log.open("w", encoding="utf-8") as out, stderr_log.open("w", encoding="utf-8") as err:
        completed = subprocess.run(cmd, stdout=out, stderr=err, check=False)

    data = _read_json(result_json) or {
        "ok": False,
        "errors": ["SPM realignment did not produce result JSON."],
    }

    data["node_id"] = "spm_realign_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["prepared_input"] = prepared_input
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    outputs = list(data.get("realigned_files", []))
    if data.get("mean_file"):
        outputs.append(data["mean_file"])
    if data.get("motion_parameter_file"):
        outputs.append(data["motion_parameter_file"])
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
