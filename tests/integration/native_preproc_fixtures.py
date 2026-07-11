from __future__ import annotations

import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from src.backend.app.schemas.native_preproc_api import (
    NativeFullPreprocConfirmations,
    NativeFullPreprocRequest,
)
from src.backend.app.services.native_preproc_full import run_native_full_execute


def file_digest(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_atomic_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and "data" in payload and "_schema_version" in payload:
        return payload["data"]
    return payload


def native_confirmations() -> NativeFullPreprocConfirmations:
    return NativeFullPreprocConfirmations(
        confirm_reviewed_native_execution=True,
        confirm_rawdata_readonly=True,
        confirm_no_external_tools=True,
        confirm_research_use_only=True,
        confirm_no_clinical_use=True,
    )


def make_synthetic_native_inputs(root: Path) -> dict[str, str]:
    func = root / "converted_bids" / "sub-001" / "func"
    anat = root / "converted_bids" / "sub-001" / "anat"
    resources = root / "resources"
    func.mkdir(parents=True, exist_ok=True)
    anat.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)

    tr = 2.0
    n_timepoints = 48
    time = np.arange(n_timepoints, dtype=np.float32) * tr
    spatial_shape = (9, 9, 9)
    data = np.zeros(spatial_shape + (n_timepoints,), dtype=np.float32) + 10.0
    data[:4, :, :, :] += np.sin(2 * np.pi * 0.03 * time)
    data[4:, :, :, :] += np.cos(2 * np.pi * 0.04 * time)
    bold = func / "sub-001_task-rest_bold.nii.gz"
    nib.save(nib.Nifti1Image(data, np.eye(4)), str(bold))

    sidecar = func / "sub-001_task-rest_bold.json"
    sidecar.write_text(
        json.dumps(
            {
                "RepetitionTime": tr,
                "SliceTiming": np.linspace(0.0, tr, spatial_shape[2], endpoint=False).tolist(),
            }
        ),
        encoding="utf-8",
    )

    t1 = np.zeros(spatial_shape, dtype=np.float32)
    t1[:3] = 40.0
    t1[3:6] = 80.0
    t1[6:] = 120.0
    t1w = anat / "sub-001_T1w.nii.gz"
    nib.save(nib.Nifti1Image(t1, np.eye(4)), str(t1w))

    template = resources / "template.nii.gz"
    nib.save(nib.Nifti1Image(np.ones(spatial_shape, dtype=np.float32), np.eye(4)), str(template))

    atlas_data = np.zeros(spatial_shape, dtype=np.int16)
    atlas_data[:4] = 1
    atlas_data[4:] = 2
    atlas = resources / "atlas.nii.gz"
    nib.save(nib.Nifti1Image(atlas_data, np.eye(4)), str(atlas))
    labels = resources / "labels.tsv"
    labels.write_text("label\tname\n1\tSinROI\n2\tCosROI\n", encoding="utf-8")

    return {
        "bold": str(bold),
        "sidecar": str(sidecar),
        "t1w": str(t1w),
        "template": str(template),
        "atlas": str(atlas),
        "labels": str(labels),
    }


def native_full_request(inputs: dict[str, str], *, run_id: str) -> NativeFullPreprocRequest:
    return NativeFullPreprocRequest(
        run_id=run_id,
        subject_id="sub-001",
        session_id="ses-01",
        input_bold=inputs["bold"],
        sidecar_json=inputs["sidecar"],
        t1w=inputs["t1w"],
        template=inputs["template"],
        atlas=inputs["atlas"],
        atlas_labels=inputs["labels"],
        remove_first=2,
        confirmations=native_confirmations(),
    )


def run_synthetic_native_full(root: Path, *, run_id: str = "native-e2e"):
    inputs = make_synthetic_native_inputs(root)
    request = native_full_request(inputs, run_id=run_id)
    return inputs, run_native_full_execute("native-phase07", request, project_dir=str(root))
