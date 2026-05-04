from __future__ import annotations

import numpy as np

from src.backend.app.tools.alff_compute import compute_alff_backend, compute_alff_numpy


def test_compute_alff_numpy_shapes():
    rng = np.random.default_rng(42)
    data = rng.normal(size=(4, 4, 4, 20)).astype("float32")

    alff, falff, warnings = compute_alff_numpy(data, tr=2.0, freq_band=(0.01, 0.08))

    assert alff.shape == (4, 4, 4)
    assert falff.shape == (4, 4, 4)
    assert np.isfinite(alff).all()
    assert np.isfinite(falff).all()
    assert isinstance(warnings, list)


def test_compute_alff_backend_cpu_fallback():
    rng = np.random.default_rng(42)
    data = rng.normal(size=(4, 4, 4, 20)).astype("float32")

    result = compute_alff_backend(
        data=data,
        tr=2.0,
        freq_band=(0.01, 0.08),
        prefer_gpu=False,
        require_gpu=False,
    )

    assert result["ok"] is True
    assert result["backend"] == "cpu-numpy"
    assert result["alff"].shape == (4, 4, 4)
    assert result["falff"].shape == (4, 4, 4)
