from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_bids_sidecar_for_bold(input_bold: str) -> str | None:
    path = Path(input_bold)

    name = path.name
    if name.endswith(".nii.gz"):
        sidecar = path.with_name(name[:-7] + ".json")
    elif name.endswith(".nii"):
        sidecar = path.with_suffix(".json")
    else:
        sidecar = path.with_suffix(".json")

    return str(sidecar) if sidecar.exists() else None


def _get_nifti_shape(path: str) -> list[int]:
    try:
        import nibabel as nib
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel. Install with: pip install nibabel") from exc

    img = nib.load(path)
    return list(img.shape)


def _slice_timing_to_order(slice_timing: list[float]) -> list[int]:
    indexed = list(enumerate(slice_timing, start=1))
    indexed = sorted(indexed, key=lambda item: (float(item[1]), item[0]))
    return [item[0] for item in indexed]


def _validate_positive_number(value: Any, name: str, errors: list[str]) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        errors.append(f"{name} must be numeric.")
        return None

    if parsed <= 0:
        errors.append(f"{name} must be positive.")
        return None

    return parsed


def build_slice_timing_parameters(
    input_bold: str,
    prepared_nii: str,
    tr: float | None = None,
    slice_order: list[int] | None = None,
    reference_slice: int | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    sidecar_path = find_bids_sidecar_for_bold(input_bold)
    metadata = _read_json(Path(sidecar_path)) if sidecar_path else None

    if not metadata:
        warnings.append("BIDS sidecar JSON not found or unreadable.")

    try:
        shape = _get_nifti_shape(prepared_nii)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [str(exc)],
            "warnings": warnings,
        }

    if len(shape) < 4:
        errors.append(f"BOLD NIfTI must be 4D. Shape was: {shape}")

    nslices = int(shape[2]) if len(shape) >= 3 else None

    metadata_tr = metadata.get("RepetitionTime") if metadata else None
    final_tr = _validate_positive_number(
        tr if tr is not None else metadata_tr,
        "RepetitionTime",
        errors,
    )

    metadata_slice_timing = metadata.get("SliceTiming") if metadata else None

    final_slice_order = None
    if metadata_slice_timing:
        if not isinstance(metadata_slice_timing, list):
            errors.append("SliceTiming must be a list.")
        elif nslices is not None and len(metadata_slice_timing) != nslices:
            errors.append(
                f"SliceTiming length {len(metadata_slice_timing)} does not match nslices {nslices}."
            )
        else:
            try:
                final_slice_order = _slice_timing_to_order([float(x) for x in metadata_slice_timing])
            except Exception as exc:
                errors.append(f"Invalid SliceTiming values: {exc}")
    elif slice_order:
        final_slice_order = [int(x) for x in slice_order]
        warnings.append("Using user-provided slice_order fallback.")
    else:
        errors.append("Missing SliceTiming metadata and no slice_order fallback provided.")

    if nslices is not None and final_slice_order and len(final_slice_order) != nslices:
        errors.append("slice_order length must equal nslices.")

    if final_slice_order:
        invalid = [x for x in final_slice_order if x < 1 or nslices is not None and x > nslices]
        if invalid:
            errors.append(f"slice_order contains invalid slice indices: {invalid}")

    if reference_slice is None and final_slice_order:
        reference_slice = final_slice_order[len(final_slice_order) // 2]

    if reference_slice is not None and nslices is not None:
        reference_slice = int(reference_slice)
        if reference_slice < 1 or reference_slice > nslices:
            errors.append("reference_slice must be between 1 and nslices.")

    ta = None
    if final_tr is not None and nslices:
        ta = final_tr - final_tr / nslices

    acquisition_duration = None
    if metadata_slice_timing:
        try:
            acquisition_duration = max(float(x) for x in metadata_slice_timing)
        except Exception:
            acquisition_duration = None

    return {
        "ok": len(errors) == 0,
        "input_bold": input_bold,
        "prepared_nii": prepared_nii,
        "sidecar_path": sidecar_path,
        "metadata_found": metadata is not None,
        "shape": shape,
        "nslices": nslices,
        "frames_total": shape[3] if len(shape) >= 4 else None,
        "tr": final_tr,
        "ta": ta,
        "slice_timing_count": len(metadata_slice_timing) if isinstance(metadata_slice_timing, list) else None,
        "slice_order": final_slice_order,
        "reference_slice": reference_slice,
        "acquisition_duration": acquisition_duration,
        "slice_timing_status": "PASS" if len(errors) == 0 else "FAIL",
        "warnings": warnings,
        "errors": errors,
    }


def write_slice_timing_qc_for_subject(
    subject_id: str,
    parameters: dict[str, Any],
    derivatives_dir: str,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "slice_timing_qc.json"
    qc_md = out_dir / "slice_timing_qc.md"

    result = {
        "ok": bool(parameters.get("ok")),
        "node_id": "slice_timing_qc_subject",
        "backend": "python",
        "subject_id": subject_id,
        "metadata_found": parameters.get("metadata_found"),
        "sidecar_path": parameters.get("sidecar_path"),
        "shape": parameters.get("shape"),
        "nslices": parameters.get("nslices"),
        "frames_total": parameters.get("frames_total"),
        "tr": parameters.get("tr"),
        "ta": parameters.get("ta"),
        "slice_timing_count": parameters.get("slice_timing_count"),
        "slice_order": parameters.get("slice_order"),
        "reference_slice": parameters.get("reference_slice"),
        "acquisition_duration": parameters.get("acquisition_duration"),
        "slice_timing_status": parameters.get("slice_timing_status"),
        "outputs": [str(qc_json), str(qc_md)],
        "warnings": parameters.get("warnings", []),
        "errors": parameters.get("errors", []),
    }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Slice Timing QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('slice_timing_status')}")
    lines.append(f"- Metadata found: {result.get('metadata_found')}")
    lines.append(f"- TR: {result.get('tr')}")
    lines.append(f"- Number of slices: {result.get('nslices')}")
    lines.append(f"- Frames total: {result.get('frames_total')}")
    lines.append(f"- Reference slice: {result.get('reference_slice')}")
    lines.append(f"- SliceTiming count: {result.get('slice_timing_count')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Slice timing QC reads metadata and derivative files only. It does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result


def write_slice_timing_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/slice_timing_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid slice timing QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("slice_timing_status") == "PASS")
    fail_count = sum(1 for item in subjects if item.get("slice_timing_status") == "FAIL")
    trs = [float(item["tr"]) for item in subjects if item.get("tr") is not None]

    summary = {
        "ok": fail_count == 0 and subjects_total > 0,
        "node_id": "slice_timing_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_fail": fail_count,
        "mean_tr": float(mean(trs)) if trs else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "slice_timing_qc_summary.json"
    report_path = report_out / "slice_timing_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Slice Timing QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean TR: {summary['mean_tr']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | TR | Slices | Frames | Reference Slice |")
    lines.append("|---|---|---:|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('slice_timing_status')} | "
            f"{item.get('tr')} | {item.get('nslices')} | "
            f"{item.get('frames_total')} | {item.get('reference_slice')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes slice timing metadata and derivative outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "slice_timing_qc_dataset_report",
        "backend": "python",
        "outputs": [str(summary_path), str(report_path)],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_pass": pass_count,
            "subjects_fail": fail_count,
        },
        "warnings": warnings,
        "errors": errors,
    }
