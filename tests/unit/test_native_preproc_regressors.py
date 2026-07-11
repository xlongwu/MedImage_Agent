from __future__ import annotations

import numpy as np
import pytest

from src.backend.app.native_preproc.dpabi_compat.regressors import (
    extract_mask_mean_signal,
    motion_regressors,
    scrubbing_regressors,
)


def test_motion_regressor_models_have_expected_shapes() -> None:
    motion = np.arange(30, dtype=np.float32).reshape((5, 6)) / 100.0

    assert motion_regressors(motion, model="motion6").values.shape == (5, 6)
    assert motion_regressors(motion, model="friston12").values.shape == (5, 12)
    friston24 = motion_regressors(motion, model="friston24")

    assert friston24.values.shape == (5, 24)
    assert friston24.columns[0] == "trans_x"
    assert "rot_z_derivative_power2" in friston24.columns


def test_scrubbing_regressors_preserve_timepoints() -> None:
    fd = np.asarray([0.0, 0.6, 0.1, 1.2], dtype=np.float32)

    regressors = scrubbing_regressors(fd, threshold_mm=0.5, n_timepoints=4)

    assert regressors.values.shape == (4, 2)
    assert regressors.columns == ["scrub_frame_0001", "scrub_frame_0003"]
    assert regressors.values[1, 0] == 1.0
    assert regressors.metadata["scrubbing_strategy"] == "spike_regressors_preserve_timepoints"


def test_mask_mean_signal_blocks_shape_mismatch() -> None:
    data = np.zeros((2, 2, 2, 4), dtype=np.float32)
    mask = np.ones((3, 3, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="does not match BOLD spatial shape"):
        extract_mask_mean_signal(data, mask, column_name="wm_signal")
