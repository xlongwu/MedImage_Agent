from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import DicomPreflightResponse, DicomSeriesSummary

DICOM_SUFFIXES = {".dcm", ".ima"}


def build_dicom_preflight(
    *,
    project_id: str,
    roots: Iterable[str | Path],
    max_files: int = 2000,
) -> DicomPreflightResponse:
    """Inspect DICOM headers only and write an auditable metadata report."""

    normalized_roots = [Path(root) for root in roots if str(root).strip()]
    checked_at = _utc_now()
    warnings: list[str] = []
    errors: list[str] = []
    existing_roots = [root for root in normalized_roots if root.exists()]
    missing_roots = [str(root) for root in normalized_roots if not root.exists()]
    for root in missing_roots:
        warnings.append(f"Root does not exist and was skipped: {root}")

    dicom_files = sorted(
        path
        for root in existing_roots
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in DICOM_SUFFIXES
    )
    sampled_files = dicom_files[: max(1, max_files)]
    series_map: dict[str, dict[str, Any]] = {}

    if not normalized_roots:
        errors.append("No DICOM roots were provided.")
    elif not dicom_files:
        errors.append("No .dcm or .ima files were discovered under the provided roots.")

    try:
        import pydicom
    except Exception as exc:  # pragma: no cover - exercised in optional dependency environments
        pydicom = None
        errors.append(f"pydicom is unavailable; DICOM metadata could not be inspected: {exc}")

    if pydicom is not None:
        parse_warning_count = 0
        for path in sampled_files:
            try:
                dataset = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
            except Exception as exc:
                parse_warning_count += 1
                if parse_warning_count <= 20:
                    warnings.append(f"Failed to read DICOM header for {path}: {exc}")
                continue

            subject_id = _subject_from_path(path)
            modality = _as_text(getattr(dataset, "Modality", None))
            series_description = _as_text(getattr(dataset, "SeriesDescription", None))
            protocol_name = _as_text(getattr(dataset, "ProtocolName", None))
            study_uid = _as_text(getattr(dataset, "StudyInstanceUID", None))
            series_uid = _as_text(getattr(dataset, "SeriesInstanceUID", None))
            if not series_uid:
                series_uid = f"unknown:{subject_id or path.parent.name}:{modality or 'NA'}:{series_description or path.parent.name}"

            entry = series_map.setdefault(
                series_uid,
                {
                    "series_instance_uid": _hash_identifier(series_uid),
                    "study_instance_uid": _hash_identifier(study_uid),
                    "subject_id": subject_id,
                    "modality": modality,
                    "series_description": series_description,
                    "protocol_name": protocol_name,
                    "sequence_name": _as_text(getattr(dataset, "SequenceName", None)),
                    "manufacturer": _as_text(getattr(dataset, "Manufacturer", None)),
                    "magnetic_field_strength": _as_float(getattr(dataset, "MagneticFieldStrength", None)),
                    "repetition_time": _as_float(getattr(dataset, "RepetitionTime", None)),
                    "echo_time": _as_float(getattr(dataset, "EchoTime", None)),
                    "flip_angle": _as_float(getattr(dataset, "FlipAngle", None)),
                    "rows": _as_int(getattr(dataset, "Rows", None)),
                    "columns": _as_int(getattr(dataset, "Columns", None)),
                    "instances": 0,
                    "sample_file": _display_path(path, existing_roots),
                    "warnings": [],
                },
            )
            entry["instances"] = int(entry.get("instances") or 0) + 1

        if parse_warning_count > 20:
            warnings.append(f"{parse_warning_count - 20} additional DICOM header read warnings were omitted.")

    series = [
        DicomSeriesSummary(**entry)
        for entry in sorted(
            series_map.values(),
            key=lambda item: (
                str(item.get("subject_id") or ""),
                str(item.get("modality") or ""),
                str(item.get("series_description") or ""),
                str(item.get("series_instance_uid") or ""),
            ),
        )
    ]
    subjects = sorted({item.subject_id for item in series if item.subject_id})
    modalities = sorted({item.modality for item in series if item.modality})
    response = DicomPreflightResponse(
        ok=bool(dicom_files) and not errors,
        project_id=project_id,
        checked_at=checked_at,
        roots=[str(root) for root in normalized_roots],
        dicom_file_count=len(dicom_files),
        sampled_file_count=len(sampled_files),
        series_count=len(series),
        subjects=subjects,
        modalities=modalities,
        series=series,
        safety_flags=_dicom_preflight_safety_flags(),
        warnings=warnings,
        errors=errors,
    )
    return response.model_copy(update=write_dicom_preflight_report(response))


def write_dicom_preflight_report(response: DicomPreflightResponse) -> dict[str, str]:
    output_dir = Path("outputs/reports/dicom_preflight") / _safe_path_part(response.project_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "dicom_preflight_result.json"
    report_path = output_dir / "dicom_preflight_report.md"
    report_text = _render_dicom_preflight_markdown(response)
    payload = response.model_dump(exclude={"report_text"})
    payload["report_path"] = str(report_path)
    payload["json_path"] = str(json_path)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report_text, encoding="utf-8")
    return {"json_path": str(json_path), "report_path": str(report_path), "report_text": report_text}


def _render_dicom_preflight_markdown(response: DicomPreflightResponse) -> str:
    lines = [
        f"# DICOM Metadata Preflight: {response.project_id}",
        "",
        f"- Checked at: {response.checked_at}",
        f"- Status: {'pass' if response.ok else 'needs review'}",
        f"- Roots: {len(response.roots)}",
        f"- DICOM files discovered: {response.dicom_file_count}",
        f"- DICOM files sampled: {response.sampled_file_count}",
        f"- Series discovered: {response.series_count}",
        f"- Subjects: {', '.join(response.subjects) if response.subjects else 'Not detected'}",
        f"- Modalities: {', '.join(response.modalities) if response.modalities else 'Not detected'}",
        "",
        "## Safety Flags",
        "",
    ]
    for key, value in sorted(response.safety_flags.items()):
        lines.append(f"- {key}: {bool(value)}")
    lines += ["", "## Roots", ""]
    for root in response.roots:
        lines.append(f"- {root}")
    lines += ["", "## Series Summary", ""]
    if not response.series:
        lines.append("- No readable DICOM series were discovered.")
    else:
        lines.append("| Subject | Modality | Series | Protocol | Instances | Matrix | Sample |")
        lines.append("| --- | --- | --- | --- | ---: | --- | --- |")
        for item in response.series:
            matrix = f"{item.rows or '?'} x {item.columns or '?'}"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(item.subject_id or ""),
                        _md_cell(item.modality or ""),
                        _md_cell(item.series_description or item.sequence_name or item.series_instance_uid),
                        _md_cell(item.protocol_name or ""),
                        str(item.instances),
                        _md_cell(matrix),
                        _md_cell(item.sample_file or ""),
                    ]
                )
                + " |"
            )
    lines += ["", "## Warnings", ""]
    if response.warnings:
        lines.extend(f"- {warning}" for warning in response.warnings)
    else:
        lines.append("- None")
    lines += ["", "## Errors", ""]
    if response.errors:
        lines.extend(f"- {error}" for error in response.errors)
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _dicom_preflight_safety_flags() -> dict[str, bool]:
    return {
        "read_only": True,
        "stop_before_pixels": True,
        "metadata_only": True,
        "rawdata_not_bundled": True,
        "no_pixel_data_export": True,
        "dicom_uids_hashed": True,
        "sample_paths_relative": True,
    }


def _safe_path_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)[:80] or "project"


def _subject_from_path(path: Path) -> str | None:
    for part in reversed(path.parts):
        lower = part.lower()
        if lower.startswith("sub-") or lower.startswith("sub_"):
            return part
    return path.parent.name or None


def _hash_identifier(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


def _display_path(path: Path, roots: Iterable[Path]) -> str:
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return path.name


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
