from __future__ import annotations

from pathlib import Path

from backend.app.tools.data_inspector import inspect_dataset
from backend.app.tools.synthetic_bids import create_synthetic_bids_dataset


def test_synthetic_bids_and_inspection(tmp_path: Path):
    rawdata = tmp_path / "synthetic_bids" / "rawdata"
    output = tmp_path / "work" / "dataset_index"

    created = create_synthetic_bids_dataset(str(rawdata), subjects=["sub-001", "sub-002"])
    assert created["ok"] is True

    result = inspect_dataset(
        rawdata_dir=str(rawdata),
        output_dir=str(output),
        read_nifti_metadata=True,
    )

    assert result["ok"] is True
    assert result["metrics"]["subjects_total"] == 2
    assert result["metrics"]["subjects_complete"] == 2
    assert (output / "dataset_index.json").exists()
    assert (output / "data_completeness_report.json").exists()
    assert (output / "subject_table.csv").exists()
