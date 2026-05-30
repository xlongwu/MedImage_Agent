from __future__ import annotations

import json
from pathlib import Path

from src.backend.app.tools.run_import_diagnostics_cli import main


def test_import_diagnostics_cli_package_and_verify(tmp_path: Path, capsys):
    demo = tmp_path / "DemoData" / "FunRaw" / "Sub_001"
    demo.mkdir(parents=True)
    (demo / "0000001.dcm").write_bytes(b"DICOM placeholder")

    exit_code = main([
        "--project-id",
        "brain-tumor-study",
        "--import-path",
        str(tmp_path / "DemoData"),
        "--dataset-type",
        "auto",
        "--mode",
        "all",
    ])
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["import"]["success"] is True
    assert payload["import"]["image_source_count"] >= 0
    assert payload["package"]["zip_path"].endswith("import_diagnostics_package.zip")
    assert payload["package"]["file_inventory"]["extension_counts"][".dcm"] >= 1
    assert payload["verification"]["ok"] is True
