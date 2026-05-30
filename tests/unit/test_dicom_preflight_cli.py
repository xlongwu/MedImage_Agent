from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.backend.app.tools.run_dicom_preflight_cli import run


def test_dicom_preflight_cli_scans_demodata_headers_only():
    pytest.importorskip("pydicom")
    demo_data = Path("data/DemoData")
    if not demo_data.exists():
        pytest.skip("DemoData is not available in this checkout.")

    payload = run(project_id="brain-tumor-study", path=str(demo_data), max_files=6)

    assert payload["ok"] is True
    assert payload["dicom_file_count"] >= 1
    assert payload["sampled_file_count"] == 6
    assert payload["series_count"] >= 1
    assert payload["safety_flags"]["metadata_only"] is True
    assert payload["safety_flags"]["stop_before_pixels"] is True
    assert payload["safety_flags"]["rawdata_not_bundled"] is True
    assert payload["safety_flags"]["dicom_uids_hashed"] is True
    assert payload["safety_flags"]["sample_paths_relative"] is True
    assert all(str(item["series_instance_uid"]).startswith("sha256:") for item in payload["series"])
    assert "1.3.12.2" not in json.dumps(payload["series"])
    assert Path(payload["report_path"]).exists()
    assert Path(payload["json_path"]).exists()
