from __future__ import annotations

from pathlib import Path

from src.backend.app.tools.confound_matrix import build_confound_matrix_for_subject


def test_confound_matrix_friston24_has_expected_columns(tmp_path: Path):
    motion_file = tmp_path / "rp_test.txt"
    motion_file.write_text(
        "\n".join(["0 0 0 0 0 0", "1 0 0 0 0 0", "1 1 0 0 0.01 0", "1 1 1 0 0.01 0.02"]),
        encoding="utf-8",
    )
    result = build_confound_matrix_for_subject(
        subject_id="sub-001",
        motion_parameter_file=str(motion_file),
        output_dir=str(tmp_path),
        model="friston24",
        include_intercept=True,
        include_linear_trend=True,
    )
    assert result["ok"] is True
    assert result["qc"]["rows"] == 4
    assert result["qc"]["columns"] == 26
    assert "intercept" in result["qc"]["column_names"]
    assert "linear_trend" in result["qc"]["column_names"]
    assert Path(result["confound_qc_json"]).exists()
