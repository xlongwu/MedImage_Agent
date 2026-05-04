from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app.main import app


def test_health_api():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True


def test_pipelines_api():
    client = TestClient(app)
    response = client.get("/api/pipelines")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "pipelines" in payload


def test_path_traversal_rejected():
    client = TestClient(app)
    response = client.get("/api/files/read", params={"path": "../../etc/passwd"})

    assert response.status_code in {400, 403}
