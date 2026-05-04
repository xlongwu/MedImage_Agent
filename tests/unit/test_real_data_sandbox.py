from pathlib import Path

from src.backend.app.tools.real_data_inspector import inspect_real_dataset
from src.backend.app.tools.real_data_risk_reporter import build_risk_report
from src.backend.app.tools.real_data_protocol_advisor import recommend_protocol_from_inventory


def test_inspect_synthetic_bids_readonly(tmp_path: Path):
    """Test that inspection works on synthetic BIDS data without modifying anything."""
    # Use existing synthetic BIDS if available, or skip
    rawdata = Path("examples/synthetic_bids/rawdata")
    if not rawdata.exists():
        # Create minimal synthetic structure
        rawdata = tmp_path / "test_bids"
        (rawdata / "sub-001" / "anat").mkdir(parents=True)
        (rawdata / "sub-001" / "func").mkdir(parents=True)
        (rawdata / "sub-001" / "anat" / "sub-001_T1w.nii.gz").write_text("mock")
        (rawdata / "sub-001" / "func" / "sub-001_task-rest_bold.nii.gz").write_text("mock")
        (rawdata / "dataset_description.json").write_text('{"Name":"test"}')

    out_dir = str(tmp_path / "reports")
    result = inspect_real_dataset(str(rawdata), output_dir=out_dir)
    assert result["ok"] is True
    assert result["mode"] == "readonly_sandbox"
    assert result["completeness"]["subjects_total"] >= 1

    # Verify the inventory file exists
    assert Path(out_dir, "data_inventory.json").exists()


def test_risk_report_from_inventory(tmp_path: Path):
    inventory = {
        "subjects": [
            {"subject_id": "sub-001", "t1w": "/data/sub-001/anat/sub-001_T1w.nii.gz", "bold": "/data/sub-001/func/sub-001_task-rest_bold.nii.gz", "tr": 2.0, "slice_count": 32},
            {"subject_id": "sub-002", "t1w": "/data/sub-002/anat/sub-002_T1w.nii.gz", "bold": None, "tr": 1.5, "slice_count": 36},
        ],
        "completeness": {"subjects_total": 2, "has_t1w": 2, "has_bold": 1, "has_fieldmap": 0, "naming_issues": 0},
    }
    out_dir = str(tmp_path / "reports")
    result = build_risk_report(inventory=inventory, output_dir=out_dir)
    assert result["ok"] is True
    assert result["risks_total"] >= 2  # missing_bold + no_fieldmap + tr variation
    assert Path(out_dir, "risk_report.json").exists()


def test_protocol_recommendation(tmp_path: Path):
    inventory = {
        "subjects": [
            {"subject_id": "sub-001", "t1w": "/data/sub-001/anat/T1w.nii.gz", "bold": "/data/sub-001/func/bold.nii.gz", "tr": 2.0, "slice_count": 32},
        ],
        "completeness": {"subjects_total": 1, "has_t1w": 1, "has_bold": 1, "has_fieldmap": 0},
    }
    out_dir = str(tmp_path / "reports")
    result = recommend_protocol_from_inventory(inventory=inventory, output_dir=out_dir)
    assert result["ok"] is True
    assert result["recommended_pipeline"] in ("rsfmri_spm_standard_v1", "rsfmri_python_quickstart")
    assert result["requires_manual_review"] is True
    assert Path(out_dir, "protocol_recommendation.json").exists()
