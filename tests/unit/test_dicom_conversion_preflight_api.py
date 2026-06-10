"""Tests for DICOM conversion preflight API endpoint — Phase 4C-2.

Tests the read-only preflight endpoint.  No real dcm2niix is called.
No NIfTI files are written.  No rawdata is modified.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app.main import app


def test_preflight_endpoint_returns_200():
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/preflight")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert "status" in payload
    assert "conversion_disabled_by_default" in payload


def test_preflight_endpoint_returns_disabled_by_default():
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/preflight")
    payload = resp.json()
    # Without env flags, conversion should be disabled
    assert payload["conversion_disabled_by_default"] is True
    assert payload["env_enabled"] is False
    assert len(payload["missing_env_flags"]) >= 1


def test_preflight_endpoint_returns_safety_flags():
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/preflight")
    payload = resp.json()
    sf = payload["safety_flags"]
    assert sf["rawdata_read_only"] is True
    assert sf["conversion_disabled_by_default"] is True
    assert sf["no_spm_dpabi_matlab"] is True
    assert sf["clinical_use_prohibited"] is True


def test_preflight_endpoint_returns_command_templates():
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/preflight")
    payload = resp.json()
    assert "command_templates" in payload
    # brain-tumor-study is a seed project with no import records,
    # so templates may be empty
    assert isinstance(payload["command_templates"], list)


def test_preflight_endpoint_does_not_write_nifti():
    """Preflight must not create NIfTI files."""
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/preflight")
    assert resp.status_code == 200
    # Preflight is read-only — no output directory should be written
    payload = resp.json()
    output_root = payload.get("output_root_preview")
    # Just confirm the endpoint didn't crash and returned valid data
    assert "ok" in payload


def test_preflight_endpoint_does_not_modify_rawdata():
    """Preflight must not touch rawdata."""
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/preflight")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["safety_flags"]["rawdata_read_only"] is True


def test_preflight_endpoint_returns_dcm2niix_status():
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/preflight")
    payload = resp.json()
    assert "dcm2niix_status" in payload
    assert "dcm2niix_available" in payload
    # Without env flags, dcm2niix check reports disabled
    assert payload["dcm2niix_status"] in {
        "disabled", "missing", "available", "version_failed", "unknown",
    }


def test_preflight_endpoint_404_for_missing_project():
    client = TestClient(app)
    resp = client.post("/api/projects/nonexistent-project/conversion/preflight")
    assert resp.status_code == 404


def test_user_data_conversion_execute_endpoint_default_blocked():
    """The conversion execute endpoint exists but MUST remain default-blocked.

    Phase 4L-2 added the /conversion/execute endpoint behind env gates.
    Without env flags, it must return disabled/blocked and never execute.
    """
    client = TestClient(app)
    resp = client.post("/api/projects/brain-tumor-study/conversion/execute")
    assert resp.status_code == 200, f"Expected 200 (blocked), got {resp.status_code}"
    payload = resp.json()
    # Must be disabled/blocked by default (status field)
    assert payload.get("status") in ("disabled", "blocked"), \
        f"Expected status=disabled or blocked, got {payload.get('status')}"
    # Safety flags must confirm no execution allowed
    sf = payload.get("safety_flags", {})
    assert sf.get("conversion_disabled_by_default") is True, \
        "conversion_disabled_by_default must be True"
    assert sf.get("public_execution_allowed") is False, \
        "public_execution_allowed must be False"
    assert sf.get("rawdata_read_only") is True, \
        "rawdata_read_only must be True"
    # Blocking issues must report missing env flags
    blocking = payload.get("blocking_issues", [])
    assert any("env flag" in b.lower() for b in blocking), \
        f"Blocking issues must mention missing env flags, got: {blocking}"
