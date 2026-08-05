"""Reproducible generator for the scientific-computation golden fixtures.

Run to (re)generate every artifact under ``tests/fixtures/scientific/``:

    D:\\Anaconda3\\envs\\mamba\\python.exe tests/fixtures/scientific/generate_golden.py

Design rules:
- Deterministic: all randomness uses fixed seeds, so reruns produce
  byte-identical outputs (NumPy `.npy` writes are deterministic for a given
  dtype/order on the same platform).
- Kernel-grounded: golden values are produced by the *same* unified compute
  kernels the execution services call, then cross-checked by an independent
  reference implementation in the test suite. The golden files lock the
  kernel's current output; the tests assert the kernel still matches them and
  that an independent reference also agrees (catching silent kernel drift).
- Small + fast: shapes are intentionally tiny so the suite runs in CI seconds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# Allow running as a standalone script from the repo root by putting the repo
# root on sys.path (pytest does this automatically for the test suite).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.backend.app.tools.alff_compute import compute_alff_numpy  # noqa: E402
from src.backend.app.tools.functional_connectivity_compute import (  # noqa: E402
    _generate_atlas,
    compute_fc_numpy,
)
from src.backend.app.tools.reho_compute import compute_reho_numpy  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent
INPUT_DIR = FIXTURE_DIR / "input"
GOLDEN_DIR = FIXTURE_DIR / "golden"

# Fixed parameters shared by generator and tests.
TR = 2.0
FREQ_BAND = (0.01, 0.08)
BOLD_SHAPE = (10, 10, 8, 50)  # x,y,z,t
ATLAS_ROI = 5
REHO_SHAPE = (8, 8, 8, 40)
FC_SHAPE = (16, 16, 12, 60)
SEED = 42


def _make_bold(shape: tuple[int, int, int, int], seed: int) -> np.ndarray:
    """Synthetic 4D BOLD with a low-frequency oscillation in the ALFF band."""
    rng = np.random.default_rng(seed)
    data = rng.normal(0, 1, shape).astype(np.float32)
    t = np.linspace(0, 2 * np.pi, shape[3]).reshape(1, 1, 1, -1)
    data = data + 2.0 * np.sin(0.1 * t) + 0.01 * np.arange(shape[3]).reshape(1, 1, 1, -1)
    return data.astype(np.float32)


def main() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    # ── Inputs ──
    bold = _make_bold(BOLD_SHAPE, SEED)
    np.save(INPUT_DIR / "tiny_bold.npy", bold)
    atlas, atlas_defs = _generate_atlas(BOLD_SHAPE[:3], roi_count=ATLAS_ROI)
    np.save(INPUT_DIR / "tiny_atlas.npy", atlas)
    gm_mask = np.ones(BOLD_SHAPE[:3], dtype=np.uint8)
    gm_mask[0, :, :] = 0  # one boundary plane excluded to exercise masking
    np.save(INPUT_DIR / "tiny_gm_mask.npy", gm_mask)
    reho_bold = _make_bold(REHO_SHAPE, SEED + 1)
    np.save(INPUT_DIR / "tiny_reho_bold.npy", reho_bold)
    fc_bold = _make_bold(FC_SHAPE, SEED + 2)
    np.save(INPUT_DIR / "tiny_fc_bold.npy", fc_bold)
    (INPUT_DIR / "sidecar.json").write_text(
        json.dumps(
            {
                "RepetitionTime": TR,
                "TaskName": "rest",
                "freq_band": list(FREQ_BAND),
                "seed": SEED,
                "shapes": {
                    "bold": list(BOLD_SHAPE),
                    "reho": list(REHO_SHAPE),
                    "fc": list(FC_SHAPE),
                    "atlas_roi": ATLAS_ROI,
                },
            },
            indent=2,
        )
    )

    # ── ALFF / fALFF golden ──
    alff, falff, _ = compute_alff_numpy(bold, tr=TR, freq_band=FREQ_BAND)
    np.save(GOLDEN_DIR / "alff_golden.npy", alff.astype(np.float32))
    np.save(GOLDEN_DIR / "falff_golden.npy", falff.astype(np.float32))

    # ── ReHo golden (7/19/27 neighborhoods) ──
    for nb in (7, 19, 27):
        res = compute_reho_numpy(reho_bold, neighborhood=nb)
        np.save(GOLDEN_DIR / f"reho_{nb}_golden.npy", np.asarray(res["reho"]).astype(np.float32))

    # ── FC golden (atlas matches the FC BOLD spatial shape, not BOLD_SHAPE) ──
    fc_atlas, _ = _generate_atlas(FC_SHAPE[:3], roi_count=ATLAS_ROI)
    fc_res = compute_fc_numpy(fc_bold, fc_atlas)
    np.save(
        GOLDEN_DIR / "fc_matrix_golden.npy",
        np.asarray(fc_res["correlation_matrix"]).astype(np.float32),
    )
    np.save(
        GOLDEN_DIR / "fisherz_golden.npy", np.asarray(fc_res["fisher_z_matrix"]).astype(np.float32)
    )

    # ── Edge-case golden (constant series -> finite, bounded output) ──
    const_bold = np.full((6, 6, 6, 50), 3.14, dtype=np.float32)
    calff, cfalff, _ = compute_alff_numpy(const_bold, tr=TR, freq_band=FREQ_BAND)
    np.save(GOLDEN_DIR / "alff_constant_golden.npy", calff.astype(np.float32))
    np.save(GOLDEN_DIR / "falff_constant_golden.npy", cfalff.astype(np.float32))

    # Manifest describing what was generated.
    (GOLDEN_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "generator": "tests/fixtures/scientific/generate_golden.py",
                "tr": TR,
                "freq_band": list(FREQ_BAND),
                "seed": SEED,
                "files": sorted(p.name for p in GOLDEN_DIR.iterdir() if p.suffix == ".npy"),
                "kernels": {
                    "alff": "tools/alff_compute.py::compute_alff_numpy",
                    "reho": "tools/reho_compute.py::compute_reho_numpy",
                    "fc": "tools/functional_connectivity_compute.py::compute_fc_numpy",
                },
            },
            indent=2,
        )
    )
    print(f"Golden fixtures written to {GOLDEN_DIR}")


if __name__ == "__main__":
    main()
