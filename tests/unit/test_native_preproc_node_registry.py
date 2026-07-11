from __future__ import annotations

from src.backend.app.native_preproc.orchestrator.stage_graph import iter_native_full_stage_specs
from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext
from src.backend.app.runtime.node_registry_plugins.create import create_registry
from src.backend.app.schemas.pipeline_schema import PipelineNode


def test_native_preproc_nodes_are_registered_without_replacing_external_nodes() -> None:
    registry = create_registry()

    assert "native_preproc_full_dry_run" in registry
    assert "native_preproc_full_execute" in registry
    for spec in iter_native_full_stage_specs():
        assert spec.node_id in registry

    assert "spm_realign_subject" in registry
    assert "dpabi_capability_inspection" in registry
    assert registry["native_preproc_full_execute"] is not registry["spm_realign_subject"]


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
