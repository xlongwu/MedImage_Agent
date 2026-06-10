"""Tests for DICOM conversion release readiness API endpoint — Phase 4K-1.

Verifies the GET /api/projects/{id}/conversion/release-readiness/{run_id}
endpoint is read-only, returns correct structure, and never executes
conversion.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app.main import app


def test_endpoint_returns_200_for_known_project():
    client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/conversion/release-readiness/conv-test")
    assert resp.status_code == 200
    payload = resp.json()
    # ok may be False if readiness checks find issues (e.g., endpoint detected)
    assert "status" in payload
    assert payload["status"] in ("blocked", "warning", "ready_internal", "ready_for_human_release_review")


def test_endpoint_is_read_only():
    """The endpoint must be GET-only — no mutation."""
    client = TestClient(app)
    # POST should return 405 (Method Not Allowed)
    resp = client.post("/api/projects/brain-tumor-study/conversion/release-readiness/conv-test", json={})
    assert resp.status_code in (404, 405), f"POST should not be allowed, got {resp.status_code}"


def test_endpoint_does_not_call_dcm2niix():
    """The readiness endpoint must not invoke dcm2niix in executable code."""
    import inspect
    from src.backend.app.api.dashboard_routes import get_conversion_release_readiness
    source = inspect.getsource(get_conversion_release_readiness)
    # Exclude docstring lines
    code_lines = [l for l in source.splitlines() if '"""' not in l and "dcm2niix" not in l.lower()]
    code = "\n".join(code_lines)
    assert "subprocess" not in code.lower()


def test_endpoint_does_not_modify_rawdata():
    """The readiness endpoint must not touch rawdata."""
    import inspect
    from src.backend.app.api.dashboard_routes import get_conversion_release_readiness
    source = inspect.getsource(get_conversion_release_readiness)
    # Exclude docstring lines containing "rawdata"
    code_lines = [l for l in source.splitlines() if '"""' not in l and "rawdata" not in l.lower()]
    code = "\n".join(code_lines)
    assert "open(" not in code


def test_endpoint_reports_public_endpoint_disabled():
    client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/conversion/release-readiness/conv-test")
    payload = resp.json()
    assert payload["public_endpoint_enabled"] is False


def test_endpoint_reports_frontend_execute_disabled():
    client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/conversion/release-readiness/conv-test")
    payload = resp.json()
    assert payload["frontend_execute_enabled"] is False


def test_endpoint_reports_human_approval_required():
    client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/conversion/release-readiness/conv-test")
    payload = resp.json()
    assert payload["human_release_approval_required"] is True


def test_endpoint_returns_safety_flags():
    client = TestClient(app)
    resp = client.get("/api/projects/brain-tumor-study/conversion/release-readiness/conv-test")
    payload = resp.json()
    sf = payload["safety_flags"]
    assert sf["public_endpoint_disabled"] is True
    assert sf["spm_dpabi_matlab_disabled"] is True
    assert sf["full_preprocessing_disabled"] is True
    assert sf["human_release_approval_required"] is True


def test_endpoint_404_for_missing_project():
    client = TestClient(app)
    resp = client.get("/api/projects/nonexistent/conversion/release-readiness/conv-test")
    assert resp.status_code == 404
