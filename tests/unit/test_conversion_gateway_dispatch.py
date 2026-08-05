from __future__ import annotations

from types import SimpleNamespace

from src.backend.app.services.reviewed_conversion_service import ReviewedConversionService


def _context(execution):
    return SimpleNamespace(
        tool_execution_context=execution,
        project_config={"project_id": "project-1"},
    )


def _node(tmp_path):
    return SimpleNamespace(
        params={
            "project_id": "project-1",
            "project_dir": str(tmp_path),
            "rawdata_dir": str(tmp_path / "rawdata"),
            "conversion_run_id": "conversion-1",
        }
    )


def test_conversion_runner_requires_gateway_issued_context(tmp_path) -> None:
    result = ReviewedConversionService().execute_node(
        context=_context(None),
        node=_node(tmp_path),
        store=SimpleNamespace(get_project=lambda _project_id: None),
    )
    assert result["ok"] is False
    assert result["preprocessing_ready"] is False
    assert result["blocking_issues"] == ["VERIFIED_EXECUTION_CONTEXT_REQUIRED"]


def test_conversion_readiness_rejects_output_under_rawdata_before_package_read(tmp_path) -> None:
    rawdata = tmp_path / "rawdata"
    rawdata.mkdir()

    result = ReviewedConversionService().check_readiness(
        project_id="project-1",
        conversion_run_id="conv-1",
        project_dir=str(tmp_path),
        rawdata_dir=str(rawdata),
        output_dir=str(rawdata / "converted"),
    )

    assert result["ok"] is False
    assert result["blocking_issues"] == ["CONVERSION_OUTPUT_SCOPE_INVALID"]


def test_approved_conversion_calls_shared_handoff_once_and_rejects_partial(tmp_path) -> None:
    calls = []
    project = SimpleNamespace(
        metadata={"project_dir": str(tmp_path), "rawdata_dir": str(tmp_path / "rawdata")}
    )
    store = SimpleNamespace(get_project=lambda _project_id: project)
    execution = SimpleNamespace(
        project_id="project-1",
        approved_node_ids=frozenset({"native_dicom_conversion_execute"}),
        approved_backend_ids=frozenset({"medimage-native"}),
    )
    service = ReviewedConversionService(
        handoff=lambda *args, **kwargs: (
            calls.append((args, kwargs))
            or {
                "ok": True,
                "status": "partial",
            }
        )
    )

    result = service.execute_node(context=_context(execution), node=_node(tmp_path), store=store)

    assert len(calls) == 1
    assert result["ok"] is False
    assert result["status"] == "partial"
    assert result["preprocessing_ready"] is False
