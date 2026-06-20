from __future__ import annotations

import json

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.backend.app.api import planner_routes
from src.backend.app.core.config import ConfigService, get_backend_settings
from src.backend.app.core.exceptions import PipelineError
from src.backend.app.main import create_app
from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.runtime.state_store import (
    STATE_SCHEMA_VERSION,
    write_node_state,
    write_pipeline_summary,
)


def _extract_route_paths(router) -> set[str]:
    """Recursively extract route paths from a router/app, handling Mount
    and _IncludedRouter wrappers introduced in newer Starlette versions."""
    paths: set[str] = set()
    for route in router.routes:
        if hasattr(route, "routes"):
            paths.update(_extract_route_paths(route))
        elif hasattr(route, "path"):
            paths.add(route.path)
    return paths


def _extract_route_method_paths(router) -> list[tuple[str, str]]:
    """Recursively extract (method, path) pairs for duplicate detection."""
    pairs: list[tuple[str, str]] = []
    for route in router.routes:
        if hasattr(route, "routes"):
            pairs.extend(_extract_route_method_paths(route))
        elif not isinstance(route, APIRoute):
            continue
        else:
            if getattr(route, "deprecated", False):
                continue
            for method in route.methods or set():
                if method in {"HEAD", "OPTIONS"}:
                    continue
                pairs.append((method, route.path))
    return pairs


def test_request_id_and_response_time_headers_are_added():
    app = create_app()
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "req-test-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-123"
    assert "X-Response-Time-ms" in response.headers


def test_api_v1_prefix_maps_to_existing_api_routes():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-API-Version"] == "v1"
    assert response.headers["X-Original-Path"] == "/api/v1/health"


def test_api_v1_prefix_preserves_legacy_route_contract():
    app = create_app()
    client = TestClient(app)

    legacy = client.get("/api/pipelines")
    versioned = client.get("/api/v1/pipelines")

    assert legacy.status_code == 200
    assert versioned.status_code == 200
    assert versioned.json() == legacy.json()


def test_domain_split_legacy_routes_remain_registered():
    app = create_app()
    registered_paths = _extract_route_paths(app)

    expected_paths = {
        "/health",
        "/api/project-config",
        "/api/dpabi/capability",
        "/api/dpabi/function-list",
        "/api/rsfmri/preprocessing-plan",
        "/api/agent/plan",
        "/api/gpu/detect",
        "/api/gpu/synthetic-benchmark",
        "/api/pipelines",
        "/api/files/read",
        "/api/logs/read",
        "/api/sessions/index",
        "/api/history/runs",
        "/api/advisor/protocol",
        "/api/kb/errors",
        "/api/experiments/run-index",
        "/api/artifacts/preview",
        "/api/bundle/create",
        "/api/docs/inventory",
        "/api/real-data/inspect",
        "/api/sandbox/status",
        "/api/workflow/run",
        "/api/deployment/profile",
    }

    assert expected_paths <= registered_paths


def test_domain_split_routes_do_not_register_duplicate_method_paths():
    app = create_app()
    seen: set[tuple[str, str]] = set()
    duplicates: list[tuple[str, str]] = []

    for key in _extract_route_method_paths(app):
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    assert duplicates == []


def test_rate_limiter_returns_structured_429(monkeypatch):
    monkeypatch.setenv("MEDIMAGE_RATE_LIMIT_PER_MINUTE", "1")
    app = create_app()
    client = TestClient(app)

    first = client.get("/health", headers={"X-Request-ID": "rate-1"})
    second = client.get("/health", headers={"X-Request-ID": "rate-2"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["X-Request-ID"] == "rate-2"
    assert second.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_medimage_error_handler_returns_stable_error_payload():
    app = create_app()

    @app.get("/test-only/pipeline-error")
    def _raise_pipeline_error():
        raise PipelineError("Bad pipeline", details={"pipeline_id": "p1"})

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/test-only/pipeline-error",
        headers={"X-Request-ID": "req-error-123"},
    )

    assert response.status_code == 400
    assert response.headers["X-Request-ID"] == "req-error-123"
    payload = response.json()
    assert payload == {
        "ok": False,
        "error": {
            "code": "PIPELINE_ERROR",
            "message": "Bad pipeline",
            "details": {"pipeline_id": "p1"},
        },
        "request_id": "req-error-123",
    }


def test_route_catch_all_maps_to_structured_pipeline_error(monkeypatch):
    def _raise_runtime_error(_: dict):
        raise RuntimeError("planner failed")

    monkeypatch.setattr(planner_routes, "draft_pipeline_plan", _raise_runtime_error)
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/planner/draft",
        json={"downstream_task": "ALFF analysis", "disease_type": "AD"},
        headers={"X-Request-ID": "req-planner-error"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "PIPELINE_ERROR"
    assert payload["error"]["message"] == "planner failed"
    assert payload["error"]["details"] == {"original_error": "planner failed"}
    assert payload["request_id"] == "req-planner-error"


def test_state_store_writes_versioned_json_atomically(tmp_path):
    node_path = write_node_state(
        run_id="run-1",
        node_id="node-a",
        subject="project",
        status="SUCCESS",
        started_at="2026-06-12T00:00:00+00:00",
        ended_at="2026-06-12T00:00:01+00:00",
        result={"ok": True, "outputs": ["out.txt"]},
        work_dir=str(tmp_path),
    )
    summary_path = write_pipeline_summary(
        run_id="run-1",
        pipeline_id="pipe-a",
        status="SUCCESS",
        started_at="2026-06-12T00:00:00+00:00",
        ended_at="2026-06-12T00:00:01+00:00",
        node_states=[str(node_path)],
        node_results=[{"ok": True}],
        errors=[],
        work_dir=str(tmp_path),
    )

    node_data = json.loads(node_path.read_text(encoding="utf-8"))
    summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert node_data["_schema_version"] == STATE_SCHEMA_VERSION
    assert summary_data["_schema_version"] == STATE_SCHEMA_VERSION
    assert node_data["node"] == "node-a"
    assert summary_data["nodes_success"] == 1


def test_atomic_write_json_preserves_existing_file_on_failure(tmp_path):
    target = tmp_path / "state.json"
    target.write_text('{"ok": true}', encoding="utf-8")

    class NotSerializable:
        pass

    try:
        atomic_write_json(target, {"bad": NotSerializable()})
    except TypeError:
        pass

    assert target.read_text(encoding="utf-8") == '{"ok": true}'
    assert not list(tmp_path.glob("*.tmp"))


def test_config_service_loads_server_env_with_legacy_settings_shape(monkeypatch):
    monkeypatch.setenv("MEDIMAGE_BACKEND_HOST", "0.0.0.0")
    monkeypatch.setenv("MEDIMAGE_BACKEND_PORT", "8100")
    monkeypatch.setenv("MEDIMAGE_SERVICE_NAME", "medimage-test")

    settings = get_backend_settings()
    service = ConfigService()

    assert settings.host == "0.0.0.0"
    assert settings.port == 8100
    assert settings.service_name == "medimage-test"
    assert service.snapshot().server.port == 8100


def test_config_service_invalid_port_falls_back(monkeypatch):
    monkeypatch.setenv("MEDIMAGE_BACKEND_PORT", "not-a-port")

    assert get_backend_settings().port == 8000


def test_config_service_loads_project_yaml(tmp_path):
    config_path = tmp_path / "project_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "runtime:",
                "  work_dir: ./work",
                "  log_dir: ./logs",
                "third_party:",
                "  spm_dir: ./third_party/spm12",
                "  dpabi_dir: ./third_party/DPABI",
                "safety:",
                "  rawdata_readonly: true",
            ]
        ),
        encoding="utf-8",
    )

    service = ConfigService.from_yaml(config_path)
    snapshot = service.snapshot()

    assert service.project is not None
    assert service.project.runtime.work_dir == "./work"
    assert snapshot.project is not None
    assert snapshot.project["third_party"]["spm_dir"] == "./third_party/spm12"
