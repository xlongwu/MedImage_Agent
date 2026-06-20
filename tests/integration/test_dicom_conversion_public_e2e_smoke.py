"""Controlled public DICOM conversion E2E smoke — Phase 4L-5.

Runs the full public execution path end to end:
1. Creates a project with DemoData rawdata
2. Persists a review package + release approval
3. Calls the PUBLIC /conversion/execute endpoint
4. Verifies output manifest, provenance, audit records, checksum, rollback evidence
5. Verifies rawdata unchanged (1104 DICOM)
6. Confirms no SPM/DPABI/MATLAB or shell=True

ALL tests skipped by default — requires ALL env flags set to "1":
  MEDIMAGE_ALLOW_USER_DATA_CONVERSION
  MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT
  MEDIMAGE_ENABLE_DICOM_CONVERSION
  MEDIMAGE_ENABLE_REVIEWED_EXECUTION
  MEDIMAGE_ENABLE_REAL_PREPROCESSING
  MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE
  MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE
  MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION
  MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE
  MEDIMAGE_ALLOW_INTERNAL_USER_DICOM_CONVERSION_PROTOTYPE
  MEDIMAGE_MATLAB_ENABLED
  MEDIMAGE_SPM_SMOKE_ENABLED
Plus: dcm2niix on PATH, pydicom available, MEDIMAGE_E2E_SMOKE_RAWDATA_DIR set
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


# ── Skip predicates ──────────────────────────────────────────────────────

_REQUIRED_PUBLIC_FLAGS = (
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION",
    "MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT",
    "MEDIMAGE_ENABLE_DICOM_CONVERSION",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
    "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
    "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE",
    "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE",
    "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION",
    "MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE",
    "MEDIMAGE_ALLOW_INTERNAL_USER_DICOM_CONVERSION_PROTOTYPE",
    "MEDIMAGE_MATLAB_ENABLED",
    "MEDIMAGE_SPM_SMOKE_ENABLED",
)


def _all_public_flags() -> bool:
    return all(os.environ.get(f) == "1" for f in _REQUIRED_PUBLIC_FLAGS)


def _dcm2niix_ok() -> bool:
    import os
    import shutil
    # First check explicit path from env override or known locations
    explicit = os.environ.get("DCM2NIIX_PATH", "")
    if explicit and __import__("pathlib").Path(explicit).exists():
        return True
    # Check common install paths
    candidates = [
        r"D:\Anaconda3\envs\mamba\Scripts\dcm2niix.exe",
        r"D:\Anaconda3\Scripts\dcm2niix.exe",
        "/usr/local/bin/dcm2niix",
    ]
    for c in candidates:
        if __import__("pathlib").Path(c).exists():
            return True
    return shutil.which("dcm2niix") is not None


def _pydicom_ok() -> bool:
    try:
        import pydicom  # noqa: F401
        return True
    except ImportError:
        return False


_SKIP_REASON = "all 12 MEDIMAGE env flags + dcm2niix + pydicom + MEDIMAGE_E2E_SMOKE_RAWDATA_DIR"


# ═══════════════════════════════════════════════════════════════════════════
# E2E smoke — public endpoint
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not _all_public_flags(), reason=_SKIP_REASON)
@pytest.mark.skipif(not _dcm2niix_ok(), reason="dcm2niix not on PATH")
@pytest.mark.skipif(not _pydicom_ok(), reason="pydicom not installed")
class TestPublicE2ESmoke:
    """End-to-end public DICOM conversion through /conversion/execute."""

    def test_full_public_e2e_conversion_smoke(self, tmp_path):
        """Run full public execution path and verify all evidence artifacts."""
        rawdata_dir = os.environ.get("MEDIMAGE_E2E_SMOKE_RAWDATA_DIR", "")
        if not rawdata_dir or not Path(rawdata_dir).exists():
            pytest.skip("MEDIMAGE_E2E_SMOKE_RAWDATA_DIR not set or not found")

        from src.backend.app.services.mock_store import mock_store
        from src.backend.app.schemas.desktop import ProjectDetail

        # ── 1. Create project ─────────────────────────────────────────
        project_id = f"e2e-public-smoke-{abs(hash(str(tmp_path))) & 0xffffffff:x}"
        project_dir = str(tmp_path / "project")
        Path(project_dir).mkdir(parents=True, exist_ok=True)

        project = ProjectDetail(
            id=project_id,
            name="E2E Public Smoke",
            study_id="E2E-001",
            modality="rs-fMRI",
            sequences=["BOLD", "T1"],
            subjects_count=3,
            scans_count=6,
            total_size="1 GB",
            created_date="2026-06-10",
            current_pipeline_id="dicom-to-nifti",
            current_model_id="dcm2niix",
            metadata={
                "rawdata_dir": rawdata_dir,
                "project_dir": project_dir,
            },
        )
        mock_store.add_project(project, health_status="Review", rawdata_dir=rawdata_dir)

        # ── 2. Persist approval package ───────────────────────────────
        from src.backend.app.services.dicom_conversion_plan_persistence import (
            persist_conversion_plan,
        )
        from src.backend.app.schemas.dicom_conversion_approval import (
            DicomConversionApprovalRecord,
        )
        from src.backend.app.services.dicom_conversion_execution import (
            run_conversion_preflight,
        )

        preflight = run_conversion_preflight(project_id)
        assert preflight.status == "ready", (
            f"Preflight must be ready: status={preflight.status} "
            f"blocking={preflight.blocking_issues}"
        )
        assert len(preflight.mappings) == 6
        assert len(preflight.command_templates) == 6

        approval = DicomConversionApprovalRecord(
            approval_id="e2e-public-test",
            project_id=project_id,
            status="approved",
            approved=True,
            approved_by="e2e-smoke-maintainer",
            mappings_reviewed=True,
            output_root=preflight.output_root_preview,
            output_root_confirmed=True,
            output_root_under_project=True,
            output_root_not_rawdata=True,
            overwrite_policy="fail_if_exists",
            rawdata_read_only_confirmed=True,
            command_templates_reviewed=True,
            no_shell_string_confirmed=True,
            dcm2niix_availability_confirmed=True,
            dcm2niix_version=preflight.executable_path,
            env_flags_confirmed=True,
            rollback_policy_acknowledged=True,
            clinical_use_prohibited_acknowledged=True,
            external_tool_acknowledgement=True,
            risk_acknowledgement=True,
            confirm_execution=True,
        )

        persist_result = persist_conversion_plan(
            project_id=project_id,
            approval_record=approval,
            preflight_snapshot=preflight.model_dump(),
            mappings=[m.model_dump() for m in preflight.mappings],
            command_templates=[t.model_dump() for t in preflight.command_templates],
            project_dir=project_dir,
            rawdata_dir=rawdata_dir,
            preflight_ok=True,
        )
        assert persist_result.ok, f"Persist failed: {persist_result.errors}"
        conversion_run_id = persist_result.conversion_run_id

        # ── 3. Persist release approval ───────────────────────────────
        from src.backend.app.services.dicom_conversion_release_approval import (
            persist_release_approval,
        )
        from src.backend.app.schemas.dicom_conversion_release_approval import (
            DicomConversionReleaseApprovalRecord,
        )

        release_record = DicomConversionReleaseApprovalRecord(
            approval_id="rel-e2e-001",
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            status="approved",
            approved_by="e2e-smoke-maintainer",
            human_approval_statement="E2E smoke test — approved for controlled execution.",
            rawdata_readonly_acknowledged=True,
            no_clinical_use_acknowledged=True,
            rollback_acknowledged=True,
            approval_audit_acknowledged=True,
            public_endpoint_acknowledged=True,
            frontend_execute_acknowledged=True,
            spm_dpabi_matlab_disabled_acknowledged=True,
        )
        release_decision = persist_release_approval(
            release_record,
            project_dir=project_dir,
            conversion_run_id=conversion_run_id,
        )
        # May be blocked if readiness isn't ready — that's expected when
        # the public endpoint flag causes readiness to block
        # We still proceed to test the endpoint at minimum

        # ── 4. Call public endpoint via TestClient ────────────────────
        from fastapi.testclient import TestClient
        from src.backend.app.main import app

        client = TestClient(app)

        body = {
            "conversion_run_id": conversion_run_id,
            "release_approval_id": "rel-e2e-001",
            "confirm_user_data_conversion": True,
            "confirm_rawdata_readonly": True,
            "confirm_research_use_only": True,
            "confirm_no_clinical_use": True,
            "confirm_rollback_available": True,
            "confirm_disk_space_checked": True,
            "confirm_public_execution_risk": True,
            "requested_by": "e2e-smoke-operator",
            "reason": "E2E public conversion smoke test",
            "dry_run_first": False,
            "rollback_mode_on_failure": "quarantine",
        }

        resp = client.post(
            f"/api/projects/{project_id}/conversion/execute",
            json=body,
        )
        assert resp.status_code == 200, f"Endpoint returned {resp.status_code}: {resp.text[:500]}"
        data = resp.json()

        # ── 5. Validate response structure ────────────────────────────
        assert "ok" in data
        assert "status" in data
        assert "safety_flags" in data

        sf = data["safety_flags"]
        assert sf["rawdata_read_only"] is True
        assert sf["spm_dpabi_matlab_disabled"] is True
        assert sf["full_preprocessing_disabled"] is True
        assert sf["no_shell_execution"] is True
        assert sf["human_release_approval_required"] is True

        assert data["ok"] is True, data
        assert data["status"] == "succeeded", data

        # status is already asserted == "succeeded" above. The previous
        # blocked/disabled branch was unreachable and has been removed.
        # ── 6. Verify evidence artifacts ──────────────────────────
        _assert_artifact_exists(data, "output_manifest_path")
        _assert_artifact_exists(data, "execution_provenance_path")
        _assert_artifact_exists(data, "audit_execution_start_path")
        _assert_artifact_exists(data, "audit_execution_final_path")
        if data.get("checksum_comparison_path"):
            assert data.get("checksum_verified") is True, (
                "Checksum should be verified when succeeded"
            )

        # ── 7. Verify rawdata unchanged ───────────────────────────
        dcm_count = len(list(Path(rawdata_dir).rglob("*.dcm")))
        assert dcm_count == 1104, (
            f"Rawdata DICOM count changed: expected 1104, got {dcm_count}"
        )

        # ── 8. Verify no output leaked to rawdata ─────────────────
        if data.get("output_root"):
            out_root = Path(data["output_root"])
            if out_root.exists():
                for p in out_root.rglob("*"):
                    if p.is_file():
                        assert not str(p).startswith(rawdata_dir), (
                            f"Output leaked to rawdata: {p}"
                        )

        out_root = Path(data["output_root"])
        nifti_files = list(out_root.rglob("*.nii*"))
        sidecar_files = list(out_root.rglob("*.json"))
        assert len(nifti_files) == 6
        assert len(sidecar_files) >= 6

        manifest = json.loads(Path(data["output_manifest_path"]).read_text(encoding="utf-8"))
        assert manifest["output_root"] == str(out_root)
        assert sum(1 for item in manifest["items"] if item["kind"] == "nifti") == 6

        provenance = json.loads(Path(data["execution_provenance_path"]).read_text(encoding="utf-8"))
        meta = provenance["metadata"]
        assert meta["dcm2niix_command_count"] == 6
        assert meta["mapping_success_count"] == 6
        assert meta["mapping_failure_count"] == 0
        assert len(provenance["output_paths"]) == 6

    def test_public_endpoint_blocked_without_env_flags(self, tmp_path):
        """Public endpoint returns blocked when env flags are not all set."""
        from fastapi.testclient import TestClient
        from src.backend.app.main import app

        # Don't set any env flags explicitly — rely on test environment
        client = TestClient(app)
        resp = client.post(
            "/api/projects/test/conversion/execute",
            json={"conversion_run_id": "test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert data["status"] in ("disabled", "blocked")

    def test_public_vs_internal_run_conversion_execute_still_blocked(self):
        """run_conversion_execute() — the original internal function — still blocked."""
        from src.backend.app.services.dicom_conversion_execution import (
            run_conversion_execute,
        )
        from src.backend.app.schemas.dicom_conversion_execution import (
            DicomConversionExecutionRequest,
        )
        result = run_conversion_execute("test", DicomConversionExecutionRequest())
        # In Phase 4B, run_conversion_execute is always disabled
        assert result.status in ("disabled", "blocked") or result.safety_flags.conversion_disabled_by_default


def _assert_artifact_exists(data: dict, key: str):
    """Assert that the artifact path in data[key] exists on disk.

    Called only after status == "succeeded" is asserted, so the artifact
    MUST exist. A missing artifact is a test failure, not a soft warning.
    """
    path_str = data.get(key)
    assert path_str, f"Response missing required artifact key '{key}': {data}"
    assert Path(path_str).exists(), (
        f"Artifact for '{key}' does not exist on disk: {path_str}")
