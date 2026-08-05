from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def create_synthetic_bids_dataset(
    output_dir: str,
    subjects: list[str] | None = None,
) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        return {
            "ok": False,
            "errors": [f"Missing dependency: {exc.name}. Install with: pip install numpy nibabel"],
        }

    subjects = subjects or ["sub-001", "sub-002"]
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    dataset_description = {
        "Name": "Synthetic BIDS-like dataset for MedImage Agent",
        "BIDSVersion": "1.8.0",
        "DatasetType": "raw",
    }
    (root / "dataset_description.json").write_text(
        json.dumps(dataset_description, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    participants_lines = ["participant_id\tage\tsex\tgroup"]
    for idx, subject in enumerate(subjects, start=1):
        participants_lines.append(f"{subject}\t{20 + idx}\tM\tcontrol")
    (root / "participants.tsv").write_text(
        "\n".join(participants_lines) + "\n",
        encoding="utf-8",
    )

    created_files: list[str] = []

    for subject in subjects:
        anat_dir = root / subject / "anat"
        func_dir = root / subject / "func"
        anat_dir.mkdir(parents=True, exist_ok=True)
        func_dir.mkdir(parents=True, exist_ok=True)

        t1_data = np.random.randn(16, 16, 16).astype("float32")
        bold_data = np.random.randn(16, 16, 16, 10).astype("float32")
        affine = np.eye(4)

        t1_path = anat_dir / f"{subject}_T1w.nii.gz"
        t1_json_path = anat_dir / f"{subject}_T1w.json"
        bold_path = func_dir / f"{subject}_task-rest_bold.nii.gz"
        bold_json_path = func_dir / f"{subject}_task-rest_bold.json"

        nib.save(nib.Nifti1Image(t1_data, affine), str(t1_path))
        nib.save(nib.Nifti1Image(bold_data, affine), str(bold_path))

        t1_metadata = {
            "Modality": "MR",
            "ImageType": ["ORIGINAL", "PRIMARY", "T1"],
            "Manufacturer": "Synthetic",
        }
        t1_json_path.write_text(
            json.dumps(t1_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Generate interleaved SliceTiming matching the z dimension
        n_slices = bold_data.shape[2]  # z dimension
        tr = 2.0
        slice_time_increment = tr / n_slices
        # Interleaved: even slices first, then odd slices
        even_indices = list(range(0, n_slices, 2))
        odd_indices = list(range(1, n_slices, 2))
        interleaved_order = even_indices + odd_indices
        _slice_timing = [i * slice_time_increment for i in range(n_slices)]
        # Assign timing values back to slice positions for BIDS SliceTiming
        # BIDS SliceTiming is in slice order (slice 0, 1, 2, ...), value = acquisition time
        bids_slice_timing = [0.0] * n_slices
        for time_idx, slice_idx in enumerate(interleaved_order):
            bids_slice_timing[slice_idx] = time_idx * slice_time_increment

        bold_metadata = {
            "TaskName": "rest",
            "RepetitionTime": tr,
            "SliceTiming": bids_slice_timing,
            "PhaseEncodingDirection": "j",
            "Manufacturer": "Synthetic",
        }
        bold_json_path.write_text(
            json.dumps(bold_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        created_files.extend(
            [
                str(t1_path),
                str(t1_json_path),
                str(bold_path),
                str(bold_json_path),
            ]
        )

    return {
        "ok": True,
        "dataset_root": str(root),
        "subjects": subjects,
        "created_files": created_files,
        "errors": [],
    }
