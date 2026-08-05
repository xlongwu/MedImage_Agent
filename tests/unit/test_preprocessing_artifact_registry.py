"""Tests for preprocessing artifact registry and lineage."""

from __future__ import annotations

import json
from pathlib import Path


def _make_bids(project_dir: Path) -> Path:
    root = project_dir / "converted_bids"
    func = root / "sub-001" / "ses-02" / "func"
    anat = root / "sub-001" / "ses-02" / "anat"
    func.mkdir(parents=True)
    anat.mkdir(parents=True)
    bold = func / "sub-001_ses-02_task-rest_acq-mb_dir-AP_run-1_bold.nii.gz"
    sidecar = func / "sub-001_ses-02_task-rest_acq-mb_dir-AP_run-1_bold.json"
    t1w = anat / "sub-001_ses-02_run-1_T1w.nii.gz"
    t1w_sidecar = anat / "sub-001_ses-02_run-1_T1w.json"
    bold.write_bytes(b"FAKE_BOLD")
    sidecar.write_text('{"TaskName":"rest","RepetitionTime":2.0}', encoding="utf-8")
    t1w.write_bytes(b"FAKE_T1W")
    t1w_sidecar.write_text("{}", encoding="utf-8")
    return root


def _setup_store(tmp_path: Path, monkeypatch, module_name: str):
    from src.backend.app.services.mock_store import SQLiteDesktopStore

    store = SQLiteDesktopStore(tmp_path / f"{module_name.replace('.', '_')}.sqlite")
    monkeypatch.setattr(f"{module_name}.mock_store", store)
    return store


def test_parse_bids_entities_handles_session_run_acq_dir(tmp_path):
    from src.backend.app.services.preprocessing_artifact_registry import parse_bids_entities

    path = (
        tmp_path
        / "sub-001"
        / "ses-02"
        / "func"
        / "sub-001_ses-02_task-rest_acq-mb_dir-AP_run-1_bold.nii.gz"
    )

    entities = parse_bids_entities(path)

    assert entities.subject_id == "sub-001"
    assert entities.session_id == "ses-02"
    assert entities.task == "rest"
    assert entities.run_id == "run-1"
    assert entities.acquisition == "acq-mb"
    assert entities.direction == "dir-AP"
    assert entities.datatype == "func"
    assert entities.suffix == "bold"


def test_write_converted_input_registry_reload_and_checksums(tmp_path):
    from src.backend.app.services.preprocessing_artifact_registry import (
        load_artifact_registry,
        write_converted_input_registry,
    )

    project_dir = tmp_path / "project"
    bids_root = _make_bids(project_dir)
    manifest = project_dir / "conversion_runs" / "conv-1" / "output_manifest.json"
    provenance = project_dir / "conversion_runs" / "conv-1" / "execution_provenance.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    provenance.write_text("{}", encoding="utf-8")

    result = write_converted_input_registry(
        project_id="proj-1",
        conversion_run_id="conv-1",
        converted_bids_dir=str(bids_root),
        project_dir=str(project_dir),
        rawdata_dir=str(tmp_path / "rawdata"),
        manifest_path=str(manifest),
        provenance_path=str(provenance),
    )

    assert result.ok
    data = load_artifact_registry(result.registry_path)
    assert data["_schema_version"] == 1
    assert data["conversion_run_id"] == "conv-1"
    assert result.artifacts_by_type["converted_bold"] == 1
    assert result.artifacts_by_type["converted_t1w"] == 1
    assert result.artifacts_by_type["sidecar_json"] == 2
    assert data["safety_flags"]["no_preprocessing_executed"] is True
    bold = next(a for a in data["artifacts"] if a["artifact_type"] == "converted_bold")
    assert bold["path_kind"] == "project_relative"
    assert bold["checksum"]
    assert bold["bids_entities"]["session_id"] == "ses-02"


def test_handoff_writes_registry_path_to_metadata(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch, "src.backend.app.services.preprocessing_handoff")
    project_dir = tmp_path / "project"
    bids_root = _make_bids(project_dir)

    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.services.preprocessing_handoff import (
        register_converted_bids_as_preprocessing_input,
    )

    result = register_converted_bids_as_preprocessing_input(
        "brain-tumor-study",
        PreprocessingInputRegistrationRequest(
            conversion_run_id="conv-1",
            converted_bids_dir=str(bids_root),
        ),
        project_dir=str(project_dir),
    )

    project = store.get_project("brain-tumor-study")
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    assert result.ok
    assert Path(result.artifact_registry_path).exists()
    assert metadata["preprocessing_input_registry_path"] == result.artifact_registry_path
    assert result.bids_entities


def test_create_run_and_preflight_preserve_registry_lineage(tmp_path, monkeypatch):
    store = _setup_store(tmp_path, monkeypatch, "src.backend.app.services.preprocessing_handoff")
    monkeypatch.setattr("src.backend.app.services.preprocessing_run.mock_store", store)
    project_dir = tmp_path / "project"
    bids_root = _make_bids(project_dir)

    from src.backend.app.schemas.preprocessing_handoff import PreprocessingInputRegistrationRequest
    from src.backend.app.schemas.preprocessing_run import PreprocessingRunCreateRequest
    from src.backend.app.services.preprocessing_handoff import (
        register_converted_bids_as_preprocessing_input,
    )
    from src.backend.app.services.preprocessing_run import (
        create_preprocessing_run,
        execute_python_preflight,
    )

    handoff = register_converted_bids_as_preprocessing_input(
        "brain-tumor-study",
        PreprocessingInputRegistrationRequest(
            conversion_run_id="conv-1",
            converted_bids_dir=str(bids_root),
        ),
        project_dir=str(project_dir),
    )
    created = create_preprocessing_run(
        "brain-tumor-study",
        PreprocessingRunCreateRequest(preprocessing_input_dir=str(bids_root)),
        project_dir=str(project_dir),
    )
    executed = execute_python_preflight(
        "brain-tumor-study",
        created.preprocessing_run_id,
        project_dir=str(project_dir),
    )

    assert handoff.ok and created.ok and executed.ok
    registry_path = Path(created.artifact_registry_path)
    assert registry_path.exists()
    manifest = json.loads(Path(executed.manifest_path).read_text(encoding="utf-8"))
    assert manifest["artifact_registry_path"] == str(registry_path)
    assert manifest["input_inventory"]["bids_entities"]


def test_stage_output_registration_appends_run_registry_artifacts(tmp_path, monkeypatch):
    _store = _setup_store(
        tmp_path, monkeypatch, "src.backend.app.services.preprocessing_stage_outputs"
    )
    project_dir = tmp_path
    bids_root = _make_bids(project_dir)

    from src.backend.app.schemas.preprocessing_stage_outputs import StageOutputRegistrationRequest
    from src.backend.app.services.preprocessing_artifact_registry import (
        REGISTRY_FILENAME,
        ensure_run_artifact_registry,
        load_artifact_registry,
    )
    from src.backend.app.services.preprocessing_stage_outputs import register_sandbox_spm_outputs

    run_dir = project_dir / "preprocessing_runs" / "pp-test"
    ensure_run_artifact_registry(
        project_id="brain-tumor-study",
        preprocessing_run_id="pp-test",
        run_dir=run_dir,
        input_dir=str(bids_root),
        project_dir=str(project_dir),
        conversion_run_id="conv-1",
        source_kind="converted_bids",
    )
    exec_dir = run_dir / "spm_exec" / "spm-ex-1"
    output_dir = exec_dir / "sandbox_output" / "sub-001"
    output_dir.mkdir(parents=True)
    (exec_dir / "manifest.json").write_text(
        '{"status":"succeeded","stage":"realignment"}', encoding="utf-8"
    )
    (output_dir / "rasub-001_task-rest_bold.nii").write_text("realigned", encoding="utf-8")
    (output_dir / "rp_sub-001.txt").write_text("motion", encoding="utf-8")
    (output_dir / "meansub-001_task-rest_bold.nii").write_text("mean", encoding="utf-8")

    result = register_sandbox_spm_outputs(
        "brain-tumor-study",
        "pp-test",
        StageOutputRegistrationRequest(execution_id="spm-ex-1"),
        project_dir=str(project_dir),
    )

    assert result.ok
    data = load_artifact_registry(run_dir / REGISTRY_FILENAME)
    types = {item["artifact_type"] for item in data["artifacts"]}
    assert "realigned_bold" in types
    assert data["safety_flags"]["no_preprocessing_executed"] is False
    realigned = next(
        item for item in data["artifacts"] if item["artifact_type"] == "realigned_bold"
    )
    assert realigned["source_artifact_ids"]


def test_report_and_validation_prefer_run_registry(tmp_path, monkeypatch):
    _setup_store(tmp_path, monkeypatch, "src.backend.app.services.preprocessing_pipeline_report")
    _setup_store(
        tmp_path, monkeypatch, "src.backend.app.services.preprocessing_pipeline_validation"
    )
    project_dir = tmp_path
    bids_root = _make_bids(project_dir)

    from src.backend.app.services.preprocessing_artifact_registry import (
        ensure_run_artifact_registry,
    )
    from src.backend.app.services.preprocessing_pipeline_report import generate_pipeline_report
    from src.backend.app.services.preprocessing_pipeline_validation import (
        validate_preprocessing_pipeline,
    )

    run_dir = project_dir / "preprocessing_runs" / "pp-test"
    ensure_run_artifact_registry(
        project_id="brain-tumor-study",
        preprocessing_run_id="pp-test",
        run_dir=run_dir,
        input_dir=str(bids_root),
        project_dir=str(project_dir),
        conversion_run_id="conv-1",
        source_kind="converted_bids",
    )

    report = generate_pipeline_report("brain-tumor-study", "pp-test", project_dir=str(project_dir))
    validation = validate_preprocessing_pipeline(
        "brain-tumor-study", "pp-test", project_dir=str(project_dir)
    )

    assert report.artifact_registry_path
    assert report.registered_outputs[0]["artifact_id"].startswith("ppart-")
    assert validation.artifact_registry_path
    assert validation.registered_outputs
