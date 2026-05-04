from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from backend.app.tools.slice_timing_qc import (
    build_slice_timing_parameters,
    write_slice_timing_qc_for_subject,
)


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


def run_spm_slice_timing_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    tr: float | None = None,
    slice_order: list[int] | None = None,
    reference_slice: int | None = None,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM slice timing requires approved=true."],
        }

    normalized_input = str(input_bold).replace("\\", "/")
    if "examples/synthetic_bids/rawdata" not in normalized_input:
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                "Refusing to run SPM slice timing on non-synthetic input.",
                f"Input was: {input_bold}",
            ],
        }

    out_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_slice_timing_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_slice_timing_stderr.log"
    result_json = out_dir / "spm_slice_timing_result.json"

    try:
        prepared_input = _prepare_bold_input(
            input_bold=input_bold,
            subject_id=subject_id,
            derivatives_dir=derivatives_dir,
        )
    except Exception as exc:
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [str(exc)],
        }

    params = build_slice_timing_parameters(
        input_bold=input_bold,
        prepared_nii=prepared_input,
        tr=tr,
        slice_order=slice_order,
        reference_slice=reference_slice,
    )

    qc = write_slice_timing_qc_for_subject(
        subject_id=subject_id,
        parameters=params,
        derivatives_dir=derivatives_dir,
    )

    if not params.get("ok"):
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "prepared_input": prepared_input,
            "slice_timing_parameters": params,
            "outputs": qc.get("outputs", []),
            "warnings": params.get("warnings", []),
            "errors": params.get("errors", []),
        }

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_slice_timing_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(Path(prepared_input).resolve()))}', "
        f"'{int(params['nslices'])}', "
        f"'{float(params['tr'])}', "
        f"'{float(params['ta'])}', "
        f"'{_matlab_quote(json.dumps(params['slice_order']))}', "
        f"'{int(params['reference_slice'])}', "
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
        "errors": ["SPM slice timing did not produce result JSON."],
    }

    data["node_id"] = "spm_slice_timing_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["prepared_input"] = prepared_input
    data["slice_timing_parameters"] = params
    data["slice_timing_qc"] = qc
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    outputs = []
    if data.get("corrected_file"):
        outputs.append(data["corrected_file"])
    outputs.extend(qc.get("outputs", []))
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
