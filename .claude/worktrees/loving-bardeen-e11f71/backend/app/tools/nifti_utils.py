from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def prepare_nifti_for_spm(
    input_path: str,
    output_dir: str,
    output_name: str | None = None,
) -> dict[str, Any]:
    src = Path(input_path)
    dst_dir = Path(output_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        return {
            "ok": False,
            "prepared_path": None,
            "errors": [f"Input NIfTI not found: {src}"],
        }

    if output_name is None:
        if src.name.endswith(".nii.gz"):
            output_name = src.name.replace(".nii.gz", ".nii")
        else:
            output_name = src.name

    dst = dst_dir / output_name

    try:
        if src.name.endswith(".nii.gz"):
            try:
                import nibabel as nib
            except ImportError:
                return {
                    "ok": False,
                    "prepared_path": None,
                    "errors": ["Missing dependency: nibabel. Install with: pip install nibabel"],
                }

            img = nib.load(str(src))
            nib.save(img, str(dst))
        else:
            shutil.copy2(src, dst)

        return {
            "ok": True,
            "prepared_path": str(dst),
            "errors": [],
        }
    except Exception as exc:
        return {
            "ok": False,
            "prepared_path": None,
            "errors": [f"Failed to prepare NIfTI for SPM: {exc}"],
        }
