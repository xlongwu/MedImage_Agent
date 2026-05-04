from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.motion_qc import compute_motion_qc_for_subject


def test_motion_qc_computes_fd(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    motion_file = tmp_path / "rp_test.txt"

    motion_file.write_text(
        "\n".join([
            "0 0 0 0 0 0",
            "1 0 0 0 0 0",
            "1 1 0 0 0.01 0",
        ]),
        encoding="utf-8",
    )

    result = compute_motion_qc_for_subject(
        subject_id="sub-001",
        motion_parameter_file=str(motion_file),
        derivatives_dir=str(derivatives),
        fd_threshold=0.5,
        head_radius_mm=50.0,
    )

    assert result["ok"] is True
    assert result["frames_total"] == 3
    assert result["fd"][0] == 0.0
    assert result["fd"][1] == 1.0
    assert result["fd"][2] == 1.5
    assert result["high_motion_frame_count"] == 2

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "motion_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
