from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.backend.app.native_preproc.orchestrator.stage_graph import iter_native_full_stage_specs
from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext
from src.backend.app.runtime.node_registry_plugins.create import create_registry
from src.backend.app.schemas.pipeline_schema import PipelineNode


def test_native_preproc_nodes_are_registered_with_legacy_external_ids_fail_closed() -> None:
    registry = create_registry()

    assert "native_preproc_full_dry_run" in registry
    assert "native_preproc_full_execute" in registry
    for spec in iter_native_full_stage_specs():
        assert spec.node_id in registry

    assert "spm_realign_subject" in registry
    assert "dpabi_capability_inspection" in registry
    assert registry["native_preproc_full_execute"] is not registry["spm_realign_subject"]


def test_legacy_spm_and_dpabi_execution_nodes_do_not_launch_external_tools(tmp_path) -> None:
    registry = create_registry()
    context = NodeExecutionContext(
        run_id="legacy-block-test",
        project_config={"project_id": "project-1", "project_dir": str(tmp_path)},
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        matlab_command="must-not-run",
        spm_dir="must-not-run",
        dpabi_dir="must-not-run",
        derivatives_dir=str(tmp_path / "derivatives"),
    )
    for node_id in (
        "spm_realign_subject",
        "spm_smooth_subject",
        "dpabi_subject_smooth",
        "dpabi_template_execute",
    ):
        result = registry[node_id](
            context,
            PipelineNode(id=node_id, name=node_id, agent="system", backend="native_python"),
        )
        assert result["status"] == "blocked"
        assert result["safety_flags"]["no_external_tools_executed"] is True
        assert "native_preproc_full_execute" in result["errors"][0]


def test_native_stage_boundary_node_blocks_direct_uncoordinated_execution(tmp_path) -> None:
    registry = create_registry()
    runner = registry["native_preproc_slice_timing"]
    context = NodeExecutionContext(
        run_id="native-test",
        project_config={"project_id": "project-1", "project_dir": str(tmp_path)},
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        matlab_command="matlab",
        spm_dir="",
        dpabi_dir="",
        derivatives_dir=str(tmp_path / "derivatives"),
    )
    node = PipelineNode(
        id="native_preproc_slice_timing",
        name="Native slice timing",
        agent="system",
        backend="native_python",
    )

    result = runner(context, node)

    assert result["status"] == "blocked"
    assert result["backend"] == "native_python"
    assert result["safety_flags"]["no_external_tools_executed"] is True
    assert "native_preproc_full_execute" in result["errors"][0]


def test_conversion_handoff_cannot_bypass_reviewed_execution_context(tmp_path) -> None:
    runner = create_registry()["native_preproc_full_execute"]
    context = NodeExecutionContext(
        run_id="native-conversion-bypass",
        project_config={"project_id": "project-1", "project_dir": str(tmp_path)},
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        matlab_command="disabled",
        spm_dir="",
        dpabi_dir="",
        derivatives_dir=str(tmp_path / "derivatives"),
    )
    node = PipelineNode(
        id="native_preproc_full_execute",
        name="Native full",
        agent="system",
        backend="native_python",
        params={
            "project_id": "project-1",
            "project_dir": str(tmp_path),
            "conversion_run_id": "conv-001",
            "confirmations": {},
        },
    )

    result = runner(context, node)

    assert result["status"] == "blocked"
    assert "VERIFIED_EXECUTION_CONTEXT_REQUIRED" in result["errors"][0]


def test_reviewed_conversion_handoff_precedes_native_preprocessing(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.backend.app.runtime.node_registry_plugins import native_preproc_nodes

    project = SimpleNamespace(
        metadata={
            "project_dir": str(tmp_path),
            "rawdata_dir": str(tmp_path / "rawdata"),
            "preprocessing_input_registry_path": str(tmp_path / "registry.json"),
            "preprocessing_conversion_run_id": "conv-001",
        }
    )

    class Store:
        def get_project(self, project_id):
            return project

    store = Store()
    tool_context = SimpleNamespace(ticket_service=SimpleNamespace(store=store))
    context = NodeExecutionContext(
        run_id="native-conversion-reviewed",
        project_config={
            "project_id": "project-1",
            "project_dir": str(tmp_path),
            "scheduler": {"gpu_mode": "require"},
        },
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        matlab_command="disabled",
        spm_dir="",
        dpabi_dir="",
        derivatives_dir=str(tmp_path / "derivatives"),
        tool_execution_context=tool_context,
    )
    node = PipelineNode(
        id="native_preproc_full_execute",
        name="Native full",
        agent="system",
        backend="native_python",
        params={
            "project_id": "project-1",
            "project_dir": str(tmp_path),
            "conversion_run_id": "conv-001",
            "compute_policy": {
                "backend": "gpu",
                "device": "cuda:0",
                "allow_cpu_fallback": False,
            },
            "confirmations": {},
        },
    )
    calls = []
    captured_request = []
    monkeypatch.setattr(
        native_preproc_nodes,
        "ensure_reviewed_native_conversion_handoff",
        lambda *args, **kwargs: (
            calls.append("conversion")
            or {
                "ok": True,
                "status": "registered",
            }
        ),
    )
    monkeypatch.setattr(
        native_preproc_nodes,
        "run_native_full_execute",
        lambda _project_id, request, **kwargs: (
            calls.append("preprocessing"),
            captured_request.append(request),
            SimpleNamespace(model_dump=lambda mode: {"ok": True, "status": "succeeded"}),
        )[-1],
    )

    result = native_preproc_nodes.run_native_full_execute_node(context, node)

    assert calls == ["conversion", "preprocessing"]
    assert captured_request[0].compute_policy.backend == "gpu"
    assert captured_request[0].compute_policy.allow_cpu_fallback is False
    assert result["ok"] is True
    assert result["conversion_handoff"]["status"] == "registered"


def test_reviewed_gpu_policy_is_blocked_when_project_scheduler_disables_gpu(
    tmp_path,
) -> None:
    runner = create_registry()["native_preproc_full_execute"]
    context = NodeExecutionContext(
        run_id="native-gpu-policy-conflict",
        project_config={
            "project_id": "project-1",
            "project_dir": str(tmp_path),
            "scheduler": {"gpu_mode": "off"},
        },
        work_dir=str(tmp_path / "work"),
        log_dir=str(tmp_path / "logs"),
        matlab_command="disabled",
        spm_dir="",
        dpabi_dir="",
        derivatives_dir=str(tmp_path / "derivatives"),
    )
    node = PipelineNode(
        id="native_preproc_full_execute",
        name="Native full",
        agent="system",
        backend="native_python",
        params={
            "input_bold": str(tmp_path / "input.nii.gz"),
            "compute_policy": {"backend": "gpu", "allow_cpu_fallback": False},
            "confirmations": {},
        },
    )

    result = runner(context, node)

    assert result["status"] == "blocked"
    assert "GPU_POLICY_CONFLICT" in result["errors"][0]
