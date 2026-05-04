from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def compute_subject_qc(
    subject_id: str,
    input_nii: str,
    output_dir: str,
) -> dict[str, Any]:
    try:
        import numpy as np
        import nibabel as nib
    except ImportError as exc:
        return {
            "ok": False,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"Missing dependency: {exc.name}. Install with: pip install numpy nibabel"],
        }

    path = Path(input_nii)
    if not path.exists():
        return {
            "ok": False,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"QC input not found: {path}"],
        }

    out_dir = Path(output_dir) / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "subject_qc.json"

    try:
        img = nib.load(str(path))
        data = img.get_fdata(dtype="float32")

        finite_mask = np.isfinite(data)
        finite_values = data[finite_mask]

        metrics = {
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "mean": float(np.mean(finite_values)) if finite_values.size else None,
            "std": float(np.std(finite_values)) if finite_values.size else None,
            "min": float(np.min(finite_values)) if finite_values.size else None,
            "max": float(np.max(finite_values)) if finite_values.size else None,
            "nan_count": int(np.isnan(data).sum()),
            "finite_voxel_count": int(finite_mask.sum()),
        }

        payload = {
            "ok": True,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "input": str(path),
            "outputs": [str(qc_json)],
            "metrics": metrics,
            "errors": [],
        }

        qc_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    except Exception as exc:
        return {
            "ok": False,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"Failed to compute QC metrics: {exc}"],
        }
