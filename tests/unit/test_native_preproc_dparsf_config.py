from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from src.backend.app.native_preproc.dpabi_compat.dparsf_config import convert_dparsf_config
from src.backend.app.native_preproc.orchestrator.runner import dry_run_native_full_preproc
from src.backend.app.schemas.native_preproc_api import NativeFullPreprocRequest


def test_dparsf_config_maps_common_time_series_options() -> None:
    conversion = convert_dparsf_config(
        {
            "remove_first_timepoints": 5,
            "slice_timing": {"enabled": True, "reference_slice": 10},
            "nuisance": {
                "enabled": True,
                "motion_model": "friston24",
                "include_wm": True,
                "include_csf": True,
                "include_global_signal": False,
                "polynomial_order": 2,
            },
            "filtering": {"enabled": True, "low_hz": 0.01, "high_hz": 0.08, "method": "fft"},
            "scrubbing": {"fd_threshold_mm": 0.5},
            "reho": True,
            "atlas_resampling": {"enabled": True},
            "roi_timeseries": {"enabled": True},
            "group_summary": {"enabled": False},
            "unexpected_gui_setting": "ignored",
        }
    )

    stages = conversion.stage_map()

    assert stages["dummy_scan_removal"].enabled is True
    assert stages["dummy_scan_removal"].parameters["remove_first"] == 5
    assert stages["slice_timing"].enabled is True
    assert stages["nuisance_regression"].parameters["include_wm"] is True
    assert stages["nuisance_regression"].parameters["scrub_threshold_mm"] == 0.5
    assert stages["temporal_filtering"].enabled is True
    assert stages["temporal_filtering"].parameters["method"] == "fft"
    assert stages["reho"].enabled is True
    assert stages["atlas_resampling"].enabled is True
    assert stages["roi_timeseries"].enabled is True
    assert stages["group_summary"].enabled is False
    assert conversion.unsupported_keys == ["unexpected_gui_setting"]
    assert "Unsupported DPARSF config key" in conversion.warnings[0]


def test_dparsf_config_preserves_disabled_downstream_stages() -> None:
    conversion = convert_dparsf_config({"filtering": {"enabled": False}, "fc": False})
    stages = conversion.stage_map()

    assert stages["temporal_filtering"].enabled is False
    assert stages["functional_connectivity"].enabled is False
    assert stages["detrending"].enabled is True


def _bold_with_sidecar(tmp_path: Path) -> tuple[Path, Path]:
    bold = tmp_path / "sub-001_task-rest_bold.nii.gz"
    sidecar = tmp_path / "sub-001_task-rest_bold.json"
    data = np.ones((3, 3, 3, 10), dtype=np.float32)
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(bold))
    sidecar.write_text(
        json.dumps({"RepetitionTime": 2.0, "SliceTiming": [0.0, 0.7, 1.4]}),
        encoding="utf-8",
    )
    return bold, sidecar


def test_native_full_dry_run_applies_dparsf_stage_controls_and_parameters(tmp_path: Path) -> None:
    bold, sidecar = _bold_with_sidecar(tmp_path)

    response = dry_run_native_full_preproc(
        "project-1",
        NativeFullPreprocRequest(
            run_id="dparsf-native",
            input_bold=str(bold),
            sidecar_json=str(sidecar),
            stage_overrides={
                "motion_qc": False,
                "coregistration": False,
                "segmentation": False,
            },
            dparsf_config={
                "remove_first_timepoints": 3,
                "slice_timing": {"enabled": False, "reference_slice": 2},
                "realignment": {"enabled": False},
                "nuisance": {
                    "enabled": False,
                    "include_global_signal": True,
                    "polynomial_order": 2,
                },
                "detrending": {"enabled": False},
                "filtering": {"enabled": False, "low_hz": 0.02, "high_hz": 0.09},
                "fc": False,
                "group_summary": {"enabled": False},
                "unsupported_key": "warning",
            },
        ),
        project_dir=str(tmp_path),
    )

    by_stage = {stage.stage_id: stage for stage in response.stage_results}

    assert response.status == "planned"
    assert by_stage["dummy_scan_removal"].status == "planned"
    assert by_stage["slice_timing"].status == "skipped"
    assert by_stage["realignment"].status == "skipped"
    assert by_stage["nuisance_regression"].status == "skipped"
    assert by_stage["detrending"].status == "skipped"
    assert by_stage["temporal_filtering"].status == "skipped"
    assert by_stage["functional_connectivity"].status == "skipped"
    assert by_stage["group_summary"].status == "skipped"
    assert any("Unsupported DPARSF config key" in warning for warning in response.warnings)
