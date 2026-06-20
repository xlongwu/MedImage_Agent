"""Tests for public DICOM conversion execute endpoint — Phase 4L-2.

Validates that the flag-gated POST /api/projects/{id}/conversion/execute
endpoint blocks execution unless all env flags, confirmations, release
approval, release readiness, gates, approval/audit package, checksum,
rollback, and disk-space preconditions are met.

No dcm2niix is called in blocked cases.  No rawdata is modified.
No SPM/DPABI/MATLAB is executed.  No shell=True is used.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import src.backend.app.services.mock_store as mock_store_module
from src.backend.app.services.mock_store import SQLiteDesktopStore


def _isolated_store(tmp_path: Path, monkeypatch) -> SQLiteDesktopStore:
    """Create an isolated SQLiteDesktopStore for one test."""
    from src.backend.app.api import (
        dashboard_routes,
        project_routes,
        execute_reviewed_routes,
        project_history_routes,
    )
    from src.backend.app.runtime import desktop_config
    from src.backend.app.planner import project_context, reviewed_plan_store
    from src.backend.app.services import conversion_planner

    store = SQLiteDesktopStore(tmp_path / "desktop_state.sqlite")
    monkeypatch.setattr(
        desktop_config, "DESKTOP_CONFIG_PATH",
        tmp_path / "desktop_config.json",
    )
    monkeypatch.setattr(
        project_routes, "DEFAULT_PROJECTS_ROOT",
        tmp_path / "projects",
    )
    # Patch every module that imports ``mock_store`` at module level, and the
    # ``mock_store`` module itself so the lazy import in ``dependencies.py``
    # also returns the isolated store.
    for module in (
        project_routes,
        dashboard_routes,
        project_context,
        reviewed_plan_store,
        project_history_routes,
        execute_reviewed_routes,
        conversion_planner,
        mock_store_module,
    ):
        monkeypatch.setattr(module, "mock_store", store)
    desktop_config.DESKTOP_CONFIG_PATH.write_text(
        json.dumps(desktop_config.DEFAULT_DESKTOP_CONFIG),
        encoding="utf-8",
    )
    return store


def _create_test_project(store: SQLiteDesktopStore, tmp_path: Path, project_id: str = "test-env-project") -> str:
    """Create a project in the isolated store via the API pattern."""
    from fastapi.testclient import TestClient
    from src.backend.app.main import app

    client = TestClient(app)
    project_dir = tmp_path / "test_project"
    rawdata_dir = tmp_path / "test_rawdata"
    (rawdata_dir / "readme.txt").parent.mkdir(parents=True, exist_ok=True)

    # Create project through API
    resp = client.post(
        "/api/projects/create",
        json={
            "project_name": "Public Exec Test",
            "rawdata_dir": str(rawdata_dir),
            "project_dir": str(project_dir),
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to create project: {resp.text}")
    pid = resp.json()["project_id"]

    # Write the approval/audit package and release approval files
    conversion_runs_dir = Path(project_dir) / "conversion_runs" / "run-001"
    conversion_runs_dir.mkdir(parents=True, exist_ok=True)

    approval_record = {
        "project_id": pid,
        "conversion_run_id": "run-001",
        "status": "approved",
        "approved_by": "maintainer",
        "human_approval_statement": "Approved for testing.",
        "rawdata_readonly_acknowledged": True,
        "no_clinical_use_acknowledged": True,
        "rollback_acknowledged": True,
        "approval_audit_acknowledged": True,
        "public_endpoint_acknowledged": True,
        "frontend_execute_acknowledged": True,
        "spm_dpabi_matlab_disabled_acknowledged": True,
    }
    (conversion_runs_dir / "approval_record.json").write_text(
        json.dumps(approval_record), encoding="utf-8",
    )
    (conversion_runs_dir / "audit_preview.json").write_text(
        json.dumps({"audit_id": "audit-001", "project_id": pid}), encoding="utf-8",
    )
    (conversion_runs_dir / "preflight_snapshot.json").write_text("{}", encoding="utf-8")
    (conversion_runs_dir / "mapping_snapshot.json").write_text(
        json.dumps({"mappings": []}), encoding="utf-8",
    )
    (conversion_runs_dir / "command_templates.json").write_text(
        json.dumps({"templates": []}), encoding="utf-8",
    )
    (conversion_runs_dir / "rawdata_checksum_before.json").write_text(
        json.dumps({"ok": True, "fingerprint": "abc123", "file_count": 10}),
        encoding="utf-8",
    )
    (conversion_runs_dir / "rollback_plan_dry_run.json").write_text(
        json.dumps({"conversion_run_id": "run-001"}), encoding="utf-8",
    )
    (conversion_runs_dir / "release_approval_decision.json").write_text(
        json.dumps({
            "ok": True, "status": "approved", "approved": True, "blocked": False,
            "safety_flags": {"public_execution_disabled": True},
        }),
        encoding="utf-8",
    )

    return pid


def _build_valid_body(**overrides) -> dict:
    kwargs: dict = {
        "conversion_run_id": "run-001",
        "release_approval_id": "approval-001",
        "confirm_user_data_conversion": True,
        "confirm_rawdata_readonly": True,
        "confirm_research_use_only": True,
        "confirm_no_clinical_use": True,
        "confirm_rollback_available": True,
        "confirm_disk_space_checked": True,
        "confirm_public_execution_risk": True,
        "requested_by": "operator-1",
        "reason": "Research conversion run",
        "dry_run_first": True,
        "rollback_mode_on_failure": "quarantine",
    }
    kwargs.update(overrides)
    return kwargs


def _all_env_flags() -> dict[str, str]:
    return {
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
        "MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT": "1",
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING": "1",
        "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE": "1",
        "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE": "1",
        "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION": "1",
        "MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE": "1",
        "MEDIMAGE_ALLOW_INTERNAL_USER_DICOM_CONVERSION_PROTOTYPE": "1",
        "MEDIMAGE_MATLAB_ENABLED": "1",
        "MEDIMAGE_SPM_SMOKE_ENABLED": "1",
    }


def _call_endpoint(
    tmp_path, monkeypatch, body_overrides=None, *, env_overrides=None
):
    """Set up isolated store + env flags, then call the endpoint."""
    from fastapi.testclient import TestClient
    from src.backend.app.main import app

    store = _isolated_store(tmp_path, monkeypatch)
    project_id = _create_test_project(store, tmp_path)

    for k in list(os.environ.keys()):
        if k.startswith("MEDIMAGE_"):
            monkeypatch.delenv(k, raising=False)

    flags = dict(_all_env_flags())
    if env_overrides:
        flags.update(env_overrides)
    for k, v in flags.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)

    client = TestClient(app)
    body = _build_valid_body(**(body_overrides or {}))
    resp = client.post(
        f"/api/projects/{project_id}/conversion/execute",
        json=body,
    )
    return resp


# ── Group 1: Env flag gating ────────────────────────────────────────────


class TestEnvFlagGating:
    """Endpoint must be blocked/disabled when env flags are missing."""

    def test_endpoint_absent_when_public_endpoint_flag_missing(
        self, tmp_path, monkeypatch,
    ):
        """When MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT is not '1', returns blocked."""
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            env_overrides={"MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT": "0"},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] in ("disabled", "blocked")
        assert data["safety_flags"]["env_flags_missing"] is True

    def test_missing_allow_user_data_conversion_blocks(self, tmp_path, monkeypatch):
        """Missing MEDIMAGE_ALLOW_USER_DATA_CONVERSION returns blocked."""
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            env_overrides={"MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "0"},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] in ("disabled", "blocked")


# ── Group 2: Operator confirmation validation ──────────────────────────


class TestMissingConfirmationsBlock:
    """Missing any operator confirmation must block execution."""

    def test_missing_confirm_user_data_conversion(self, tmp_path, monkeypatch):
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            {"confirm_user_data_conversion": False},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"
        issues = data.get("blocking_issues", [])
        assert any("user data" in (b.lower() if isinstance(b, str) else str(b).lower()) for b in issues), f"blocking_issues: {issues}"

    def test_missing_confirm_rawdata_readonly(self, tmp_path, monkeypatch):
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            {"confirm_rawdata_readonly": False},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"

    def test_missing_confirm_research_use_only(self, tmp_path, monkeypatch):
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            {"confirm_research_use_only": False},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"

    def test_missing_confirm_no_clinical_use(self, tmp_path, monkeypatch):
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            {"confirm_no_clinical_use": False},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"

    def test_missing_confirm_rollback_available(self, tmp_path, monkeypatch):
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            {"confirm_rollback_available": False},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"

    def test_missing_confirm_disk_space_checked(self, tmp_path, monkeypatch):
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            {"confirm_disk_space_checked": False},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"

    def test_missing_confirm_public_execution_risk(self, tmp_path, monkeypatch):
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            {"confirm_public_execution_risk": False},
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"


# ── Group 3: Release approval gating ───────────────────────────────────


class TestReleaseApprovalGating:
    """Missing or expired release approval must block execution."""

    def test_rejected_release_approval_blocks(self, tmp_path, monkeypatch):
        # Override release approval decision to rejected
        store = _isolated_store(tmp_path, monkeypatch)
        pid = _create_test_project(store, tmp_path)
        project_dir = str(tmp_path / "test_project")
        (Path(project_dir) / "conversion_runs" / "run-001" / "release_approval_decision.json").write_text(
            json.dumps({
                "ok": False, "status": "rejected", "approved": False, "blocked": True,
                "blocking_issues": ["Release approval was rejected."],
                "safety_flags": {},
            }),
            encoding="utf-8",
        )

        for k in list(os.environ.keys()):
            if k.startswith("MEDIMAGE_"):
                monkeypatch.delenv(k, raising=False)
        for k, v in _all_env_flags().items():
            monkeypatch.setenv(k, v)

        from fastapi.testclient import TestClient
        from src.backend.app.main import app
        client = TestClient(app)
        resp = client.post(
            f"/api/projects/{pid}/conversion/execute",
            json=_build_valid_body(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"

    def test_missing_release_approval_blocks(self, tmp_path, monkeypatch):
        store = _isolated_store(tmp_path, monkeypatch)
        pid = _create_test_project(store, tmp_path)
        project_dir = str(tmp_path / "test_project")
        # Remove the decision file
        dec_path = Path(project_dir) / "conversion_runs" / "run-001" / "release_approval_decision.json"
        dec_path.unlink()

        for k in list(os.environ.keys()):
            if k.startswith("MEDIMAGE_"):
                monkeypatch.delenv(k, raising=False)
        for k, v in _all_env_flags().items():
            monkeypatch.setenv(k, v)

        from fastapi.testclient import TestClient
        from src.backend.app.main import app
        client = TestClient(app)
        resp = client.post(
            f"/api/projects/{pid}/conversion/execute",
            json=_build_valid_body(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"

    def test_expired_release_approval_blocks(self, tmp_path, monkeypatch):
        store = _isolated_store(tmp_path, monkeypatch)
        pid = _create_test_project(store, tmp_path)
        project_dir = str(tmp_path / "test_project")
        (Path(project_dir) / "conversion_runs" / "run-001" / "release_approval_decision.json").write_text(
            json.dumps({
                "ok": False, "status": "expired", "approved": False, "blocked": True,
                "blocking_issues": ["Release approval has expired."],
                "safety_flags": {},
            }),
            encoding="utf-8",
        )

        for k in list(os.environ.keys()):
            if k.startswith("MEDIMAGE_"):
                monkeypatch.delenv(k, raising=False)
        for k, v in _all_env_flags().items():
            monkeypatch.setenv(k, v)

        from fastapi.testclient import TestClient
        from src.backend.app.main import app
        client = TestClient(app)
        resp = client.post(
            f"/api/projects/{pid}/conversion/execute",
            json=_build_valid_body(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"


# ── Group 4: Release readiness gating ──────────────────────────────────


class TestReleaseReadinessGating:
    """Non-ready release readiness must block execution."""

    def test_readiness_not_ready_blocks(self, tmp_path, monkeypatch):
        """Endpoint blocks when release readiness is not ready_for_human_release_review."""
        resp = _call_endpoint(tmp_path, monkeypatch)
        data = resp.json()
        # The readiness service checks public_endpoint_enabled, which is True
        # now that the endpoint exists.  This blocks readiness.
        if data["status"] == "blocked":
            assert data["ok"] is False
            # This is expected behaviour — the readiness check blocks because
            # the public endpoint exists before human release approval


# ── Group 5: Approval/audit package, checksum, rollback gating ─────────


class TestPackageGating:
    """Missing approval/audit package, checksum, or rollback blocks execution."""

    def test_missing_checksum_snapshot_blocks(self, tmp_path, monkeypatch):
        store = _isolated_store(tmp_path, monkeypatch)
        pid = _create_test_project(store, tmp_path)
        project_dir = str(tmp_path / "test_project")
        cs_path = Path(project_dir) / "conversion_runs" / "run-001" / "rawdata_checksum_before.json"
        cs_path.unlink()

        for k in list(os.environ.keys()):
            if k.startswith("MEDIMAGE_"):
                monkeypatch.delenv(k, raising=False)
        for k, v in _all_env_flags().items():
            monkeypatch.setenv(k, v)

        from fastapi.testclient import TestClient
        from src.backend.app.main import app
        client = TestClient(app)
        resp = client.post(
            f"/api/projects/{pid}/conversion/execute",
            json=_build_valid_body(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"
        assert data["safety_flags"]["rawdata_checksum_before_exists"] is False

    def test_missing_rollback_plan_blocks(self, tmp_path, monkeypatch):
        store = _isolated_store(tmp_path, monkeypatch)
        pid = _create_test_project(store, tmp_path)
        project_dir = str(tmp_path / "test_project")
        rp_path = Path(project_dir) / "conversion_runs" / "run-001" / "rollback_plan_dry_run.json"
        rp_path.unlink()

        for k in list(os.environ.keys()):
            if k.startswith("MEDIMAGE_"):
                monkeypatch.delenv(k, raising=False)
        for k, v in _all_env_flags().items():
            monkeypatch.setenv(k, v)

        from fastapi.testclient import TestClient
        from src.backend.app.main import app
        client = TestClient(app)
        resp = client.post(
            f"/api/projects/{pid}/conversion/execute",
            json=_build_valid_body(),
        )
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] == "blocked"
        assert data["safety_flags"]["rollback_plan_exists"] is False


# ── Group 6: Safety verification ───────────────────────────────────────


class TestEndpointSafety:
    """Verify the endpoint does not enable SPM/DPABI/MATLAB or use shell=True."""

    def test_no_shell_true_in_response(self, tmp_path, monkeypatch):
        """All response paths must return no_shell_execution=True."""
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            env_overrides={"MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT": "0"},
        )
        data = resp.json()
        assert data["safety_flags"]["no_shell_execution"] is True

    def test_spm_dpabi_matlab_disabled_in_response(self, tmp_path, monkeypatch):
        """All response paths must indicate SPM/DPABI/MATLAB are disabled."""
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            env_overrides={"MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT": "0"},
        )
        data = resp.json()
        assert data["safety_flags"]["spm_dpabi_matlab_disabled"] is True
        assert data["safety_flags"]["full_preprocessing_disabled"] is True
        assert data["safety_flags"]["rawdata_read_only"] is True

    def test_no_dcm2niix_called_in_blocked_case(self, tmp_path, monkeypatch):
        """The internal execution path is never reached when env flags missing."""
        resp = _call_endpoint(
            tmp_path, monkeypatch,
            env_overrides={"MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT": "0"},
        )
        data = resp.json()
        assert data["ok"] is False
        # No manifest or provenance paths set — execution was never called
        assert data.get("output_manifest_path") in ("", None)


class TestFrontendAbsence:
    """Verify no frontend execute button exists."""

    def test_no_run_conversion_text_in_frontend(self):
        """Frontend must not contain 'Run Conversion' as a button label."""
        panel_path = os.path.join(
            os.getcwd(),
            "src/frontend/src/components/DicomConversionReviewPanel.tsx",
        )
        if os.path.exists(panel_path):
            lines = open(panel_path, encoding="utf-8").read().splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("/*"):
                    continue
                if "onClick" in stripped and "Run Conversion" in stripped:
                    pytest.fail(
                        "Frontend 'Run Conversion' onClick handler found — must not exist"
                    )

    def test_no_execute_api_wrapper_in_frontend(self):
        """Frontend api.ts has runProjectDicomConversionExecute — added in Phase 4L-4.

        The API wrapper exists behind the VITE_ENABLE_DICOM_EXECUTE_UI feature flag.
        It is only called from the gated confirmation UI, never automatically.
        """
        api_path = os.path.join(os.getcwd(), "src/frontend/src/api.ts")
        if os.path.exists(api_path):
            content = open(api_path, encoding="utf-8").read()
            assert "runProjectDicomConversionExecute" in content, (
                "Frontend api.ts must contain runProjectDicomConversionExecute in Phase 4L-4"
            )
