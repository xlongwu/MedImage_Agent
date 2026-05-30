from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

import nibabel as nib
import numpy as np
import pytest

from src.backend.app.tools.spm_coregister_runner import run_spm_coregister_subject
from src.backend.app.tools.spm_normalize_runner import run_spm_normalize_subject
from src.backend.app.tools.spm_realign_runner import run_spm_realign_subject
from src.backend.app.tools.spm_segment_runner import run_spm_segment_subject
from src.backend.app.tools.spm_slice_timing_runner import run_spm_slice_timing_subject
from src.backend.app.tools.spm_smooth_runner import run_spm_smooth_subject


Runner = Callable[[Path], dict[str, Any]]


def _write_nifti(path: Path, shape: tuple[int, ...] = (4, 4, 4, 3)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.random.default_rng(7).normal(size=shape).astype("float32")
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(path))


def _write_text(path: Path, content: str = "0 0 0 0 0 0\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _extract_result_json(cmd: list[str]) -> Path:
    joined = " ".join(str(part) for part in cmd)
    matches = re.findall(r"'([^']*spm_[^']*result\.json)'", joined)
    if not matches:
        raise AssertionError(f"Could not find SPM result JSON in command: {cmd}")
    return Path(matches[-1])


def _subject_dirs(tmp_path: Path) -> dict[str, Path]:
    return {
        "raw_func": tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func",
        "raw_anat": tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "anat",
        "derivatives": tmp_path / "derivatives",
        "work": tmp_path / "work",
        "logs": tmp_path / "logs",
    }


def _make_raw_bold(tmp_path: Path) -> Path:
    dirs = _subject_dirs(tmp_path)
    bold = dirs["raw_func"] / "sub-001_task-rest_bold.nii"
    _write_nifti(bold)
    bold.with_suffix(".json").write_text(
        json.dumps({"RepetitionTime": 2.0, "SliceTiming": [0.0, 0.5, 1.0, 1.5]}),
        encoding="utf-8",
    )
    return bold


def _make_raw_t1w(tmp_path: Path) -> Path:
    t1w = _subject_dirs(tmp_path)["raw_anat"] / "sub-001_T1w.nii"
    _write_nifti(t1w, shape=(4, 4, 4))
    return t1w


def _fake_subprocess_run(monkeypatch: pytest.MonkeyPatch, *, returncode: int = 0, create_outputs: bool = True) -> None:
    def fake_run(cmd: list[str], stdout=None, stderr=None, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        if stdout:
            stdout.write("fake MATLAB stdout\n")
        if stderr:
            stderr.write("fake MATLAB stderr\n")

        result_json = _extract_result_json(cmd)
        subject_id = "sub-001"
        payload: dict[str, Any] = {"ok": returncode == 0, "warnings": [], "errors": []}

        def add_nifti(key: str, path: Path, shape: tuple[int, ...] = (4, 4, 4, 3)) -> None:
            payload[key] = str(path)
            if create_outputs and returncode == 0:
                _write_nifti(path, shape=shape)

        def add_text(key: str, path: Path) -> None:
            payload[key] = str(path)
            if create_outputs and returncode == 0:
                _write_text(path)

        name = result_json.name
        if name == "spm_slice_timing_result.json":
            add_nifti("corrected_file", result_json.parent / f"a{subject_id}_bold.nii")
        elif name == "spm_realign_result.json":
            realigned = result_json.parent / f"ra{subject_id}_bold.nii"
            payload["realigned_files"] = [str(realigned)]
            if create_outputs and returncode == 0:
                _write_nifti(realigned)
            add_nifti("mean_file", result_json.parent / f"mean{subject_id}_bold.nii", shape=(4, 4, 4))
            add_text("motion_parameter_file", result_json.parent / f"rp_{subject_id}_bold.txt")
        elif name == "spm_coregistration_result.json":
            add_nifti("coregistered_file", result_json.parent / f"coreg_{subject_id}_T1w.nii", shape=(4, 4, 4))
        elif name == "spm_segmentation_result.json":
            add_nifti("gm_file", result_json.parent / f"c1coreg_{subject_id}_T1w.nii", shape=(4, 4, 4))
            add_nifti("wm_file", result_json.parent / f"c2coreg_{subject_id}_T1w.nii", shape=(4, 4, 4))
            add_nifti("csf_file", result_json.parent / f"c3coreg_{subject_id}_T1w.nii", shape=(4, 4, 4))
            add_nifti("deformation_field", result_json.parent / f"y_coreg_{subject_id}_T1w.nii", shape=(4, 4, 4))
        elif name == "spm_normalization_result.json":
            add_nifti("normalized_file", result_json.parent / f"wra{subject_id}_bold.nii")
            add_nifti("normalized_mean_file", result_json.parent / f"wmean{subject_id}_bold.nii", shape=(4, 4, 4))
        elif name == "spm_smoothing_result.json":
            add_nifti("smoothed_file", result_json.parent / f"swra{subject_id}_bold.nii")
        else:
            raise AssertionError(f"Unexpected SPM result JSON: {result_json}")

        result_json.parent.mkdir(parents=True, exist_ok=True)
        result_json.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)


def _slice_runner(tmp_path: Path) -> dict[str, Any]:
    dirs = _subject_dirs(tmp_path)
    return run_spm_slice_timing_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(dirs["derivatives"]),
        work_dir=str(dirs["work"]),
        log_dir=str(dirs["logs"]),
        approved=True,
    )


def _realign_runner(tmp_path: Path) -> dict[str, Any]:
    dirs = _subject_dirs(tmp_path)
    return run_spm_realign_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        input_bold=str(_make_raw_bold(tmp_path)),
        derivatives_dir=str(dirs["derivatives"]),
        work_dir=str(dirs["work"]),
        log_dir=str(dirs["logs"]),
        approved=True,
    )


def _coreg_runner(tmp_path: Path) -> dict[str, Any]:
    dirs = _subject_dirs(tmp_path)
    mean_func = dirs["derivatives"] / "rsfmri_preproc" / "sub-001" / "func" / "mean_sub-001_bold.nii"
    _write_nifti(mean_func, shape=(4, 4, 4))
    t1w = _make_raw_t1w(tmp_path)
    return run_spm_coregister_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        subject_record={"sessions": [{"anat": {"t1w": str(t1w)}}]},
        derivatives_dir=str(dirs["derivatives"]),
        work_dir=str(dirs["work"]),
        log_dir=str(dirs["logs"]),
        approved=True,
    )


def _segment_runner(tmp_path: Path) -> dict[str, Any]:
    dirs = _subject_dirs(tmp_path)
    coreg = dirs["derivatives"] / "rsfmri_preproc" / "sub-001" / "anat" / "coreg_sub-001_T1w.nii"
    _write_nifti(coreg, shape=(4, 4, 4))
    # Create TPM required by segment preflight
    tpm_dir = tmp_path / "spm12" / "tpm"
    tpm_dir.mkdir(parents=True, exist_ok=True)
    (tpm_dir / "TPM.nii").write_text("dummy")
    return run_spm_segment_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(dirs["derivatives"]),
        work_dir=str(dirs["work"]),
        log_dir=str(dirs["logs"]),
        approved=True,
    )


def _normalize_runner(tmp_path: Path) -> dict[str, Any]:
    dirs = _subject_dirs(tmp_path)
    func = dirs["derivatives"] / "rsfmri_preproc" / "sub-001" / "func"
    anat = dirs["derivatives"] / "rsfmri_preproc" / "sub-001" / "anat"
    _write_nifti(func / "ra_sub-001_bold.nii")
    _write_nifti(func / "mean_sub-001_bold.nii", shape=(4, 4, 4))
    _write_nifti(anat / "y_coreg_sub-001_T1w.nii", shape=(4, 4, 4))
    return run_spm_normalize_subject(
        matlab_command="matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(dirs["derivatives"]),
        work_dir=str(dirs["work"]),
        log_dir=str(dirs["logs"]),
        approved=True,
    )


def _smooth_runner(tmp_path: Path) -> dict[str, Any]:
    dirs = _subject_dirs(tmp_path)
    _write_nifti(dirs["derivatives"] / "rsfmri_preproc" / "sub-001" / "func" / "wra_sub-001_bold.nii")
    return run_spm_smooth_subject(
        matlab_command="fake-matlab",
        spm_dir=str(tmp_path / "spm12"),
        subject_id="sub-001",
        derivatives_dir=str(dirs["derivatives"]),
        work_dir=str(dirs["work"]),
        log_dir=str(dirs["logs"]),
        approved=True,
    )


SPM_CASES: list[tuple[str, Runner]] = [
    ("slice_timing", _slice_runner),
    ("realign", _realign_runner),
    ("coregister", _coreg_runner),
    ("segment", _segment_runner),
    ("normalize", _normalize_runner),
    ("smooth", _smooth_runner),
]


@pytest.mark.parametrize(("name", "runner"), SPM_CASES)
def test_spm_fake_matlab_success_has_contract(name: str, runner: Runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=True)

    result = runner(tmp_path)

    assert result["ok"] is True, name
    assert result["external_tool_result"]["returncode"] == 0
    assert result["external_tool_result"]["logs"]["stdout"].endswith(".log")
    assert result["outputs"]


@pytest.mark.parametrize(("name", "runner"), SPM_CASES)
def test_spm_fake_matlab_missing_outputs_fail(name: str, runner: Runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_subprocess_run(monkeypatch, returncode=0, create_outputs=False)

    result = runner(tmp_path)

    assert result["ok"] is False, name
    assert any("Expected output not found" in item for item in result["errors"])
    assert result["external_tool_result"]["errors"]


@pytest.mark.parametrize(("name", "runner"), SPM_CASES)
def test_spm_fake_matlab_nonzero_returncode_diagnoses_logs(name: str, runner: Runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_subprocess_run(monkeypatch, returncode=7, create_outputs=False)

    result = runner(tmp_path)

    assert result["ok"] is False, name
    assert result["returncode"] == 7
    assert any("MATLAB exited with return code 7" in item for item in result["errors"])
    logs = result["external_tool_result"]["logs"]
    assert Path(logs["stdout"]).exists()
    assert Path(logs["stderr"]).exists()
