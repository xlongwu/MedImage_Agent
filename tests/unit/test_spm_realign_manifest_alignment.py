"""Tests for SPM realign manifest adapter — pure schema alignment helpers."""

from __future__ import annotations

from src.backend.app.services.spm_realign_manifest_adapter import (
    build_output_manifest_from_dry_run_input,
    build_provenance_preview_from_dry_run,
    predicted_output_to_manifest_item,
)
from src.backend.app.services.spm_realign_params import default_spm_realign_params


def _pred(kind: str = "realigned_bold", path: str = "/out/sub-01/func/rbold.nii", **kw) -> dict:
    return {"kind": kind, "path": path, "exists": False, "would_overwrite": False, **kw}


def _input_preview(**kw) -> dict:
    base = {
        "subject_id": "sub-01",
        "session_id": None,
        "bold_path": "/data/sub-01/func/bold.nii",
        "warnings": [],
        "predicted_outputs": [_pred()],
    }
    base.update(kw)
    return base


# ── predicted_output_to_manifest_item tests ──────────────────────────────────


def test_predicted_output_converts_kind_and_path():
    item = predicted_output_to_manifest_item(_pred(kind="motion_params", path="/out/rp.txt"))
    assert item.kind == "motion_params"
    assert item.path == "/out/rp.txt"


def test_would_overwrite_becomes_warning():
    item = predicted_output_to_manifest_item(_pred(would_overwrite=True, warning="File exists"))
    assert len(item.warnings) >= 1
    assert "File exists" in item.warnings[0]


def test_would_overwrite_without_warning_defaults():
    item = predicted_output_to_manifest_item(_pred(would_overwrite=True, path="/out/file.nii"))
    assert len(item.warnings) >= 1
    assert "overwritten" in item.warnings[0]


def test_required_kinds_are_marked_required():
    required_kinds = (
        "realigned_bold",
        "mean_bold",
        "motion_params",
        "stdout_log",
        "stderr_log",
        "provenance_json",
        "node_state_json",
    )
    for kind in required_kinds:
        item = predicted_output_to_manifest_item(_pred(kind=kind, path="/out/x"))
        assert item.required is True, f"{kind} should be required"


def test_verified_stays_false():
    item = predicted_output_to_manifest_item(_pred(exists=True))
    assert item.exists is True
    assert item.verified is False


def test_relative_path_computed():
    item = predicted_output_to_manifest_item(
        _pred(path="/root/sub-01/func/rbold.nii"),
        relative_to="/root",
    )
    assert item.relative_path == "sub-01/func/rbold.nii"


# ── build_output_manifest_from_dry_run_input tests ───────────────────────────


def test_manifest_computes_counts():
    inp = {
        "subject_id": "sub-01",
        "bold_path": "/data/sub-01/func/bold.nii",
        "warnings": [],
        "predicted_outputs": [
            _pred("realigned_bold", "/out/rbold.nii", exists=True),
            _pred("mean_bold", "/out/meanbold.nii", exists=False),  # missing
            _pred("motion_params", "/out/rp.txt", exists=True),
        ],
    }
    manifest = build_output_manifest_from_dry_run_input(
        project_id="p1",
        run_id="r1",
        input_preview=inp,
        output_root="/out",
    )
    assert len(manifest.items) == 3
    assert manifest.missing_required_count == 1  # mean_bold
    assert manifest.verified_count == 0


def test_manifest_preserves_subject_session():
    inp = _input_preview(subject_id="sub-99", session_id="ses-1")
    manifest = build_output_manifest_from_dry_run_input(
        project_id="p1",
        run_id="r1",
        input_preview=inp,
        output_root="/out",
    )
    assert manifest.subject_id == "sub-99"
    assert manifest.session_id == "ses-1"


# ── build_provenance_preview_from_dry_run tests ─────────────────────────────


def test_provenance_includes_input_paths():
    dry_run = {
        "params": default_spm_realign_params(),
        "inputs": [
            {"bold_path": "/data/sub-01/func/bold.nii", "predicted_outputs": []},
            {"bold_path": "/data/sub-02/func/bold.nii", "predicted_outputs": []},
        ],
        "warnings": [],
    }
    prov = build_provenance_preview_from_dry_run(
        project_id="p1",
        reviewed_plan_id="rplan1",
        run_id="r1",
        dry_run=dry_run,
        command_template_id="spm12_realign_estwrite_v1",
    )
    assert "/data/sub-01/func/bold.nii" in prov.input_paths
    assert "/data/sub-02/func/bold.nii" in prov.input_paths


def test_provenance_includes_predicted_output_paths():
    dry_run = {
        "params": default_spm_realign_params(),
        "inputs": [
            {
                "bold_path": "/data/sub-01/func/bold.nii",
                "predicted_outputs": [
                    _pred("realigned_bold", "/out/rbold.nii"),
                    _pred("motion_params", "/out/rp.txt"),
                ],
            }
        ],
        "warnings": [],
    }
    prov = build_provenance_preview_from_dry_run(
        project_id="p1",
        reviewed_plan_id="rplan1",
        run_id="r1",
        dry_run=dry_run,
        command_template_id="spm12_realign_estwrite_v1",
    )
    assert "/out/rbold.nii" in prov.predicted_output_paths
    assert "/out/rp.txt" in prov.predicted_output_paths


def test_provenance_includes_approval_context():
    dry_run = {"params": {}, "inputs": [], "warnings": []}
    prov = build_provenance_preview_from_dry_run(
        project_id="p1",
        reviewed_plan_id="rplan1",
        run_id="r1",
        dry_run=dry_run,
        command_template_id="spm12_realign_estwrite_v1",
        approval_context={"approved": True, "overwrite_policy": "fail_if_exists"},
    )
    assert prov.approval_context["approved"] is True
    assert prov.approval_context["overwrite_policy"] == "fail_if_exists"


def test_provenance_keeps_actual_output_paths_empty():
    dry_run = {"params": {}, "inputs": [], "warnings": []}
    prov = build_provenance_preview_from_dry_run(
        project_id="p1",
        reviewed_plan_id="rplan1",
        run_id="r1",
        dry_run=dry_run,
        command_template_id="spm12_realign_estwrite_v1",
    )
    assert prov.actual_output_paths == []


def test_helpers_are_pure_no_files(tmp_path):
    before = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    predicted_output_to_manifest_item(_pred())
    build_output_manifest_from_dry_run_input(
        project_id="p1",
        run_id="r1",
        input_preview=_input_preview(),
        output_root="/o",
    )
    build_provenance_preview_from_dry_run(
        project_id="p1",
        reviewed_plan_id="rplan1",
        run_id="r1",
        dry_run={"params": {}, "inputs": [], "warnings": []},
        command_template_id="spm12_realign_estwrite_v1",
    )
    after = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    assert after == before
