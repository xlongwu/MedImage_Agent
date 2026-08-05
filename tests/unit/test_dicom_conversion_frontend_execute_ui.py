"""Source contracts for the production DICOM execution boundary."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "src/frontend/src/components/DicomConversionExecutePanel.tsx"
REVIEW_PANEL = ROOT / "src/frontend/src/components/DicomConversionReviewPanel.tsx"
EN_MESSAGES = ROOT / "src/frontend/src/i18n/messages/en.ts"
ZH_MESSAGES = ROOT / "src/frontend/src/i18n/messages/zh-CN.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestControlledProductionEntry:
    def test_feature_flag_still_controls_panel_visibility(self) -> None:
        source = _read(COMPONENT)
        assert "VITE_ENABLE_DICOM_EXECUTE_UI" in source
        assert "if (!featureEnabled)" in source
        assert "return null" in source

    def test_component_never_calls_retired_execute_endpoint(self) -> None:
        source = _read(COMPONENT)
        assert "/conversion/execute" not in source
        assert "runProjectDicomConversionExecute" not in source
        assert "handleExecute" not in source

    def test_component_has_no_prepare_or_execute_action(self) -> None:
        source = _read(COMPONENT)
        assert "<button" not in source
        assert "onClick=" not in source
        assert "workflow.prepare" not in source
        assert "prepareProjectDicomConversion" not in source

    def test_controlled_route_is_explained_in_both_locales(self) -> None:
        source = _read(COMPONENT)
        en = _read(EN_MESSAGES)
        zh = _read(ZH_MESSAGES)
        assert "technical.DicomConversionExecute.controlled.routeDescription" in source
        for catalog in (en, zh):
            assert "Reviewed Plan" in catalog or "审核方案" in catalog
            assert "Execution Ticket" in catalog or "执行票据" in catalog
            assert "Execution Gateway" in catalog

    def test_rawdata_readonly_boundary_is_visible(self) -> None:
        source = _read(COMPONENT)
        assert "technical.DicomConversionExecute.controlled.rawdataReadonly" in source
        assert "rawdata remains read-only" in _read(EN_MESSAGES)
        assert "rawdata 保持只读" in _read(ZH_MESSAGES)


class TestNativeDependencyStatus:
    def test_parent_passes_authoritative_preflight(self) -> None:
        parent = _read(REVIEW_PANEL)
        assert "preflight={data}" in parent

    def test_preflight_controls_dependency_state(self) -> None:
        source = _read(COMPONENT)
        assert "preflight.native_converter_available" in source
        assert '"available"' in source
        assert '"unavailable"' in source
        assert '"checking"' in source

    def test_required_packages_and_missing_state_are_explicit(self) -> None:
        source = _read(COMPONENT)
        en = _read(EN_MESSAGES)
        zh = _read(ZH_MESSAGES)
        assert "technical.DicomConversionExecute.controlled.dependenciesMissing" in source
        for package in ("pydicom", "nibabel", "numpy"):
            assert package in en
            assert package in zh
        assert "dependency check did not pass" in en
        assert "依赖检查未通过" in zh

    def test_dependency_versions_are_rendered_from_backend_evidence(self) -> None:
        source = _read(COMPONENT)
        assert "native_dependency_versions" in source
        assert "dependencyVersions.map" in source


class TestSafetyInvariants:
    def test_no_frontend_process_execution(self) -> None:
        source = _read(COMPONENT)
        for pattern in ("subprocess", "child_process", "execSync", "exec(", "spawn("):
            assert pattern not in source

    def test_release_readiness_panel_remains_read_only(self) -> None:
        readiness_panel = _read(
            ROOT / "src/frontend/src/components/DicomConversionReleaseReadinessPanel.tsx"
        )
        assert "/conversion/execute" not in readiness_panel
        assert "runProjectDicomConversionExecute" not in readiness_panel
