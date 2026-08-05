from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.native_preproc.stages.motion_qc import (
    compute_framewise_displacement,
    compute_friston_24,
    run_motion_qc,
)


def _write_motion(path: Path, rows: list[list[float]]) -> Path:
    lines = ["trans_x_mm\ttrans_y_mm\ttrans_z_mm\trot_x_rad\trot_y_rad\trot_z_rad"]
    lines.extend("\t".join(str(value) for value in row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_motion_qc_computes_fd_friston24_and_threshold_report(tmp_path: Path) -> None:
    motion = _write_motion(
        tmp_path / "rp_sub-01.tsv",
        [
            [0, 0, 0, 0, 0, 0],
            [1, 0, 0, 0.01, 0, 0],
            [1, 0, 0, 0.03, 0, 0],
        ],
    )

    result = run_motion_qc(motion, tmp_path / "native", fd_threshold_mm=2.0, head_radius_mm=50.0)

    assert result.status == "succeeded"
    assert result.qc.metrics["fd_first_frame"] == 0.0
    assert result.qc.metrics["friston24_shape"] == [3, 24]
    assert result.qc.metrics["high_motion_frame_count"] == 0
    fd_artifact = next(
        artifact
        for artifact in result.output_artifacts
        if artifact.artifact_type == "fd_timeseries"
    )
    assert (
        Path(fd_artifact.path).read_text(encoding="utf-8").splitlines()[0]
        == "framewise_displacement"
    )


def test_motion_qc_flags_fd_threshold_without_hiding_warning(tmp_path: Path) -> None:
    motion = _write_motion(
        tmp_path / "rp_sub-01.tsv",
        [
            [0, 0, 0, 0, 0, 0],
            [1, 0, 0, 0.01, 0, 0],
        ],
    )

    result = run_motion_qc(motion, tmp_path / "native", fd_threshold_mm=0.5, head_radius_mm=50.0)

    assert result.status == "warning"
    assert result.qc.status == "warning"
    assert result.qc.metrics["high_motion_frame_count"] == 1


def test_motion_qc_kernel_shapes_and_fd_first_frame_strategy() -> None:
    params = np.asarray(
        [
            [0, 0, 0, 0, 0, 0],
            [1, 2, 0, 0.01, 0.02, 0],
        ],
        dtype=np.float32,
    )

    fd = compute_framewise_displacement(params, head_radius_mm=50.0)
    friston = compute_friston_24(params)

    assert fd.tolist() == [0.0, 4.5]
    assert friston.shape == (2, 24)
