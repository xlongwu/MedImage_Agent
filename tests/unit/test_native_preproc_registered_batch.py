from __future__ import annotations

import json
from pathlib import Path

from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.native_preproc_api import (
    NativeFullPreprocConfirmations,
    NativeFullPreprocRequest,
    NativeFullPreprocResponse,
    NativeFullStageApiResult,
)
from src.backend.app.services import native_preproc_full as service


def _confirmations() -> NativeFullPreprocConfirmations:
    return NativeFullPreprocConfirmations(
        confirm_reviewed_native_execution=True,
        confirm_rawdata_readonly=True,
        confirm_no_external_tools=True,
        confirm_research_use_only=True,
        confirm_no_clinical_use=True,
    )


def _write_conversion_registry(project_dir: Path, registry_path: Path) -> None:
    artifacts: list[dict[str, object]] = []
    for subject in ("sub-001", "sub-002", "sub-003"):
        artifacts.extend(
            [
                {
                    "artifact_type": "converted_bold",
                    "subject_id": subject,
                    "path": f"converted_bids/{subject}/func/{subject}_task-rest_bolda.nii.gz",
                    "path_kind": "project_relative",
                },
                {
                    "artifact_type": "converted_bold",
                    "subject_id": subject,
                    "path": f"converted_bids/{subject}/func/{subject}_task-rest_bold.nii.gz",
                    "path_kind": "project_relative",
                },
                {
                    "artifact_type": "sidecar_json",
                    "subject_id": subject,
                    "path": f"converted_bids/{subject}/func/{subject}_task-rest_bold.json",
                    "path_kind": "project_relative",
                },
                {
                    "artifact_type": "converted_t1w",
                    "subject_id": subject,
                    "path": f"converted_bids/{subject}/anat/{subject}_T1wa.nii.gz",
                    "path_kind": "project_relative",
                },
                {
                    "artifact_type": "converted_t1w",
                    "subject_id": subject,
                    "path": f"converted_bids/{subject}/anat/{subject}_T1w.nii.gz",
                    "path_kind": "project_relative",
                },
            ]
        )
    atomic_write_json(
        registry_path,
        {
            "conversion_run_id": "conv-001",
            "project_id": "demo-project",
            "artifacts": artifacts,
        },
        schema_version=1,
    )


def _write_project_resources(project_dir: Path, *, extra_atlas: bool = False) -> None:
    template_dir = project_dir / "resources" / "templates"
    atlas_dir = project_dir / "resources" / "atlases"
    template_dir.mkdir(parents=True)
    atlas_dir.mkdir(parents=True)
    (template_dir / "MNI152_T1_1mm.nii.gz").write_bytes(b"template")
    (atlas_dir / "aal.nii").write_bytes(b"atlas")
    (atlas_dir / "aal.json").write_text(
        json.dumps({"labels": [{"label": 1, "name": "ROI_1"}]}),
        encoding="utf-8",
    )
    if extra_atlas:
        (atlas_dir / "other_atlas.nii.gz").write_bytes(b"other-atlas")


def _write_registered_input_files(project_dir: Path) -> None:
    for subject in ("sub-001", "sub-002", "sub-003"):
        func_dir = project_dir / "converted_bids" / subject / "func"
        anat_dir = project_dir / "converted_bids" / subject / "anat"
        func_dir.mkdir(parents=True)
        anat_dir.mkdir(parents=True)
        (func_dir / f"{subject}_task-rest_bold.nii.gz").write_bytes(b"bold")
        (func_dir / f"{subject}_task-rest_bold.json").write_text(
            json.dumps({"RepetitionTime": 2.0, "SliceTiming": [0.0, 1.0]}),
            encoding="utf-8",
        )
        (anat_dir / f"{subject}_T1w.nii.gz").write_bytes(b"t1w")


def test_registered_conversion_inputs_run_all_subjects(monkeypatch, tmp_path) -> None:
    project_dir = tmp_path / "project"
    registry_path = project_dir / "preprocessing_inputs" / "conv-001" / "preprocessing_artifact_registry.json"
    registry_path.parent.mkdir(parents=True)
    _write_conversion_registry(project_dir, registry_path)

    calls: list[NativeFullPreprocRequest] = []

    def _fake_execute(
        project_id: str,
        request: NativeFullPreprocRequest,
        *,
        project_dir: str = "",
    ) -> NativeFullPreprocResponse:
        calls.append(request)
        run_dir = Path(request.output_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = run_dir / "native_full_run_manifest.json"
        response = NativeFullPreprocResponse(
            ok=True,
            status="succeeded",
            project_id=project_id,
            run_id=request.run_id,
            run_dir=str(run_dir),
            stage_results=[
                NativeFullStageApiResult(
                    stage_id="input_validation",
                    status="succeeded",
                    result={"input_bold": request.input_bold},
                )
            ],
            completed_stages=["input_validation"],
            manifest_path=str(manifest_path),
            safety_flags={"no_external_tools_executed": True},
        )
        atomic_write_json(manifest_path, response.model_dump(mode="json"), schema_version=1)
        return response

    monkeypatch.setattr(service, "execute_native_full_preproc", _fake_execute)

    result = service.run_native_full_execute(
        "demo-project",
        NativeFullPreprocRequest(
            run_id="native-batch",
            conversion_run_id="conv-001",
            confirmations=_confirmations(),
        ),
        project_dir=str(project_dir),
        project_metadata={
            "project_dir": str(project_dir),
            "preprocessing_conversion_run_id": "conv-001",
            "preprocessing_input_registry_path": str(registry_path),
        },
    )

    assert result.status == "succeeded"
    assert result.ok is True
    assert [request.subject_id for request in calls] == ["sub-001", "sub-002", "sub-003"]
    assert [Path(request.input_bold).name for request in calls] == [
        "sub-001_task-rest_bold.nii.gz",
        "sub-002_task-rest_bold.nii.gz",
        "sub-003_task-rest_bold.nii.gz",
    ]
    assert [Path(request.t1w).name for request in calls] == [
        "sub-001_T1w.nii.gz",
        "sub-002_T1w.nii.gz",
        "sub-003_T1w.nii.gz",
    ]
    assert [Path(request.output_dir).relative_to(Path(result.run_dir)) for request in calls] == [
        Path("sub-001"),
        Path("sub-002"),
        Path("sub-003"),
    ]
    assert all("subjects" not in Path(request.output_dir).parts for request in calls)
    assert Path(result.manifest_path).exists()
    group_summary = json.loads(
        (
            Path(result.run_dir)
            / "artifacts"
            / "group_summary"
            / "native_group_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert group_summary["subject_count"] == 3
    assert group_summary["completed_subject_count"] == 3


def test_registered_conversion_dry_run_discovers_unique_project_resources(tmp_path) -> None:
    project_dir = tmp_path / "project"
    registry_path = project_dir / "preprocessing_inputs" / "conv-001" / "preprocessing_artifact_registry.json"
    registry_path.parent.mkdir(parents=True)
    _write_conversion_registry(project_dir, registry_path)
    _write_registered_input_files(project_dir)
    _write_project_resources(project_dir)

    result = service.run_native_full_dry_run(
        "demo-project",
        NativeFullPreprocRequest(
            run_id="native-resource-dry-run",
            conversion_run_id="conv-001",
            confirmations=_confirmations(),
        ),
        project_dir=str(project_dir),
        project_metadata={
            "project_dir": str(project_dir),
            "preprocessing_conversion_run_id": "conv-001",
            "preprocessing_input_registry_path": str(registry_path),
        },
        persist_artifacts=False,
    )

    assert result.status == "planned"
    assert result.ok is True
    assert result.blocked_stages == []
    assert any("template from project resources" in warning for warning in result.warnings)
    assert any("atlas from project resources" in warning for warning in result.warnings)
    assert any("atlas label file from project resources" in warning for warning in result.warnings)


def test_registered_conversion_dry_run_blocks_ambiguous_project_atlases(tmp_path) -> None:
    project_dir = tmp_path / "project"
    registry_path = project_dir / "preprocessing_inputs" / "conv-001" / "preprocessing_artifact_registry.json"
    registry_path.parent.mkdir(parents=True)
    _write_conversion_registry(project_dir, registry_path)
    _write_registered_input_files(project_dir)
    _write_project_resources(project_dir, extra_atlas=True)

    result = service.run_native_full_dry_run(
        "demo-project",
        NativeFullPreprocRequest(
            run_id="native-ambiguous-atlas-dry-run",
            conversion_run_id="conv-001",
            confirmations=_confirmations(),
        ),
        project_dir=str(project_dir),
        project_metadata={
            "project_dir": str(project_dir),
            "preprocessing_conversion_run_id": "conv-001",
            "preprocessing_input_registry_path": str(registry_path),
        },
        persist_artifacts=False,
    )

    assert result.status == "partial"
    assert result.ok is False
    assert any("atlas_resampling" in stage for stage in result.blocked_stages)
    assert any("Multiple atlas candidates" in warning for warning in result.warnings)


def test_explicit_input_dry_run_discovers_resources_without_registry(tmp_path) -> None:
    project_dir = tmp_path / "project"
    _write_registered_input_files(project_dir)
    _write_project_resources(project_dir)

    result = service.run_native_full_dry_run(
        "demo-project",
        NativeFullPreprocRequest(
            run_id="native-explicit-input-dry-run",
            subject_id="sub-001",
            input_bold=str(
                project_dir
                / "converted_bids"
                / "sub-001"
                / "func"
                / "sub-001_task-rest_bold.nii.gz"
            ),
            sidecar_json=str(
                project_dir
                / "converted_bids"
                / "sub-001"
                / "func"
                / "sub-001_task-rest_bold.json"
            ),
            t1w=str(
                project_dir
                / "converted_bids"
                / "sub-001"
                / "anat"
                / "sub-001_T1w.nii.gz"
            ),
            confirmations=_confirmations(),
        ),
        project_dir=str(project_dir),
        project_metadata={"project_dir": str(project_dir)},
        persist_artifacts=False,
    )

    assert result.status == "planned"
    assert result.ok is True
    assert result.blocked_stages == []
    assert any("template from project resources" in warning for warning in result.warnings)
    assert any("atlas from project resources" in warning for warning in result.warnings)
