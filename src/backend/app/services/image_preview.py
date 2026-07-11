from __future__ import annotations

import base64
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.backend.app.schemas.desktop import (
    ImagePlane,
    ImagePreviewResponse,
    ImageSourceFile,
    ImageSourcesResponse,
    ImageSourceSubject,
    ImageValidationIssue,
    ImageValidationReport,
)


PREVIEW_SEARCH_ROOTS = [
    Path("examples/synthetic_bids/rawdata"),
    Path("outputs/derivatives"),
    Path("outputs/work"),
]


def build_image_preview(
    *,
    project_id: str,
    subject_id: str | None,
    sequence: str,
    slice_index: int | None = None,
    plane: ImagePlane = "axial",
    search_roots: Iterable[str | Path] | None = None,
) -> ImagePreviewResponse:
    selected_subject = subject_id or "sub-001"
    candidate = find_nifti_preview_file(sequence=sequence, subject_id=selected_subject, search_roots=search_roots)
    if not candidate:
        return ImagePreviewResponse(
            project_id=project_id,
            subject_id=selected_subject,
            sequence=sequence,
            plane=plane,
            preview_url=None,
            source="fallback",
            message="No matching local NIfTI preview file was found; using bundled synthetic MRI fallback.",
        )

    try:
        preview = render_nifti_svg_preview(candidate, requested_slice_index=slice_index, plane=plane)
    except Exception as exc:
        return ImagePreviewResponse(
            project_id=project_id,
            subject_id=selected_subject,
            sequence=sequence,
            plane=plane,
            preview_url=None,
            source="fallback",
            source_path=str(candidate),
            message=f"Failed to render NIfTI preview: {exc}. Using bundled synthetic MRI fallback.",
        )

    return ImagePreviewResponse(
        project_id=project_id,
        subject_id=selected_subject,
        sequence=sequence,
        plane=preview["plane"],
        preview_url=preview["preview_url"],
        source="nifti",
        source_path=str(candidate),
        slice_index=preview["slice_index"],
        slice_count=preview["slice_count"],
        dimensions=preview["dimensions"],
        message=f"Rendered {preview['plane']} slice from local NIfTI: {candidate}",
    )


def list_image_sources(*, project_id: str, search_roots: Iterable[str | Path] | None = None) -> ImageSourcesResponse:
    subjects: dict[str, dict[str, object]] = {}
    manifest: list[ImageSourceFile] = []
    warnings: list[str] = []
    for root in _preview_search_roots(search_roots):
        if not root.exists():
            continue
        for path in _iter_nifti_files(root):
            subject_id = _subject_from_path(path)
            sequence = _canonical_sequence_from_name(path.name)
            if not subject_id or not sequence:
                continue
            source_file = build_image_source_manifest_item(
                path=path,
                root=root,
                subject_id=subject_id,
                sequence=sequence,
            )
            manifest.append(source_file)
            warnings.extend(source_file.warnings)
            subject_entry = subjects.setdefault(subject_id, {"files": {}, "file_details": []})
            files = subject_entry["files"]
            file_details = subject_entry["file_details"]
            if isinstance(files, dict):
                files.setdefault(sequence, str(path))
            if isinstance(file_details, list):
                file_details.append(source_file)

    subject_items = [
        ImageSourceSubject(
            subject_id=subject_id,
            sequences=sorted(files.keys()) if isinstance(files, dict) else [],
            files=dict(sorted(files.items())) if isinstance(files, dict) else {},
            file_details=sorted(file_details, key=lambda item: (item.sequence, item.file_path)) if isinstance(file_details, list) else [],
        )
        for subject_id, entry in sorted(subjects.items())
        for files, file_details in [(entry.get("files"), entry.get("file_details"))]
    ]
    sequences = sorted({sequence for item in subject_items for sequence in item.sequences})
    roots = [str(root) for root in _preview_search_roots(search_roots) if root.exists()]
    response = ImageSourcesResponse(
        project_id=project_id,
        subjects=subject_items,
        sequences=sequences,
        roots=roots,
        manifest=sorted(manifest, key=lambda item: (item.subject_id, item.sequence, item.file_path)),
        warnings=sorted(set(warnings)),
    )
    response.manifest_path = write_image_source_manifest(response)
    return response


def build_image_source_manifest_item(*, path: Path, root: Path, subject_id: str, sequence: str) -> ImageSourceFile:
    warnings: list[str] = []
    dimensions: list[int] = []
    voxel_spacing: list[float] = []
    plane_slice_counts: dict[ImagePlane, int] = {}

    try:
        import nibabel as nib

        image = nib.load(str(path))
        shape = [int(item) for item in image.shape]
        dimensions = shape
        voxel_spacing = [round(float(item), 6) for item in image.header.get_zooms()[: len(shape)]]
        if len(shape) >= 3:
            plane_slice_counts = {
                "sagittal": shape[0],
                "coronal": shape[1],
                "axial": shape[2],
            }
    except ImportError:
        warnings.append("nibabel is unavailable; NIfTI metadata could not be inspected.")
    except Exception as exc:
        warnings.append(f"Failed to inspect NIfTI metadata: {exc}")

    stat = path.stat()
    return ImageSourceFile(
        subject_id=subject_id,
        session_id=_session_from_path(path),
        sequence=sequence,
        file_path=str(path),
        relative_path=_relative_path(path, root),
        source_root=str(root),
        size_bytes=int(stat.st_size),
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        dimensions=dimensions,
        voxel_spacing=voxel_spacing,
        plane_slice_counts=plane_slice_counts,
        warnings=warnings,
    )


def write_image_source_manifest(response: ImageSourcesResponse) -> str:
    output_dir = Path("outputs/reports/image_sources") / _safe_path_part(response.project_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "image_source_manifest.json"
    payload = response.model_dump(exclude={"manifest_path"})
    payload["generated_at"] = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(manifest_path)


def build_image_validation_report(
    *,
    project_id: str,
    expected_sequences: Iterable[str] | None = None,
    search_roots: Iterable[str | Path] | None = None,
) -> ImageValidationReport:
    sources = list_image_sources(project_id=project_id, search_roots=search_roots)
    expected = sorted({item for item in expected_sequences or [] if item})
    issues: list[ImageValidationIssue] = []

    if not sources.manifest:
        issues.append(
            ImageValidationIssue(
                severity="error",
                code="no_image_sources",
                message="No NIfTI image sources were discovered in configured roots or imported paths.",
            )
        )

    for source in sources.manifest:
        for warning in source.warnings:
            issues.append(
                ImageValidationIssue(
                    severity="warning",
                    code="metadata_warning",
                    message=warning,
                    subject_id=source.subject_id,
                    sequence=source.sequence,
                    file_path=source.file_path,
                )
            )
        if len(source.dimensions) < 3:
            issues.append(
                ImageValidationIssue(
                    severity="error",
                    code="invalid_dimensions",
                    message="NIfTI source is not at least 3D.",
                    subject_id=source.subject_id,
                    sequence=source.sequence,
                    file_path=source.file_path,
                )
            )
        if not source.voxel_spacing:
            issues.append(
                ImageValidationIssue(
                    severity="warning",
                    code="missing_spacing",
                    message="Voxel spacing could not be read from the NIfTI header.",
                    subject_id=source.subject_id,
                    sequence=source.sequence,
                    file_path=source.file_path,
                )
            )

    by_subject: dict[str, list[ImageSourceFile]] = {}
    by_subject_session_sequence: dict[tuple[str, str | None, str], list[ImageSourceFile]] = {}
    by_sequence_spacing: dict[str, set[tuple[float, ...]]] = {}
    for source in sources.manifest:
        by_subject.setdefault(source.subject_id, []).append(source)
        by_subject_session_sequence.setdefault((source.subject_id, source.session_id, source.sequence), []).append(source)
        if source.voxel_spacing:
            by_sequence_spacing.setdefault(source.sequence, set()).add(tuple(source.voxel_spacing[:3]))

    for subject_id, subject_sources in sorted(by_subject.items()):
        available = {source.sequence for source in subject_sources}
        for sequence in expected:
            if sequence not in available:
                issues.append(
                    ImageValidationIssue(
                        severity="warning",
                        code="missing_expected_sequence",
                        message=f"Expected sequence {sequence} is not present for {subject_id}.",
                        subject_id=subject_id,
                        sequence=sequence,
                    )
                )

    for (subject_id, session_id, sequence), matches in sorted(
        by_subject_session_sequence.items(),
        key=lambda item: (item[0][0] or "", item[0][1] or "", item[0][2] or ""),
    ):
        if len(matches) > 1:
            session_text = f" session {session_id}" if session_id else ""
            issues.append(
                ImageValidationIssue(
                    severity="warning",
                    code="duplicate_sequence",
                    message=f"{len(matches)} files found for {subject_id}{session_text} sequence {sequence}.",
                    subject_id=subject_id,
                    sequence=sequence,
                    file_path=matches[0].file_path,
                )
            )

    for sequence, spacings in sorted(by_sequence_spacing.items()):
        if len(spacings) > 1:
            issues.append(
                ImageValidationIssue(
                    severity="warning",
                    code="spacing_mismatch",
                    message=f"Sequence {sequence} has inconsistent voxel spacing across discovered sources.",
                    sequence=sequence,
                )
            )

    status = "fail" if any(issue.severity == "error" for issue in issues) else "warning" if issues else "pass"
    checked_at = _utc_now()
    report = ImageValidationReport(
        ok=status != "fail",
        project_id=project_id,
        status=status,
        checked_at=checked_at,
        source_count=len(sources.manifest),
        subject_count=len(sources.subjects),
        sequence_count=len(sources.sequences),
        expected_sequences=expected,
        issues=issues,
        manifest_path=sources.manifest_path,
    )
    report_paths = write_image_validation_report(report)
    return report.model_copy(update=report_paths)


def write_image_validation_report(report: ImageValidationReport) -> dict[str, str]:
    output_dir = Path("outputs/reports/image_validation") / _safe_path_part(report.project_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "image_validation_report.json"
    report_path = output_dir / "image_validation_report.md"
    report_text = _render_image_validation_markdown(report)
    json_path.write_text(json.dumps(report.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report_text, encoding="utf-8")
    return {"json_path": str(json_path), "report_path": str(report_path), "report_text": report_text}


def _render_image_validation_markdown(report: ImageValidationReport) -> str:
    lines = [
        f"# Image Validation Report: {report.project_id}",
        "",
        f"- Checked at: {report.checked_at}",
        f"- Status: {report.status}",
        f"- Sources: {report.source_count}",
        f"- Subjects: {report.subject_count}",
        f"- Sequences: {report.sequence_count}",
        f"- Expected sequences: {', '.join(report.expected_sequences) if report.expected_sequences else 'Not specified'}",
        f"- Manifest: {report.manifest_path or 'Not generated'}",
        "",
        "## Checklist",
        "",
    ]
    if not report.issues:
        lines.append("- [pass] No validation issues were detected.")
    else:
        for issue in report.issues:
            scope = " ".join(item for item in [issue.subject_id, issue.sequence] if item)
            scope = f" ({scope})" if scope else ""
            lines.append(f"- [{issue.severity}] {issue.code}{scope}: {issue.message}")
    return "\n".join(lines) + "\n"


def find_nifti_preview_file(
    *,
    sequence: str,
    subject_id: str | None,
    search_roots: Iterable[str | Path] | None = None,
) -> Path | None:
    aliases = _sequence_aliases(sequence)
    subject = (subject_id or "").lower()
    for root in _preview_search_roots(search_roots):
        if not root.exists():
            continue
        for path in _iter_nifti_files(root):
            name = path.name.lower()
            full = str(path).lower()
            if subject and subject not in full:
                continue
            if any(alias in name for alias in aliases):
                return path
    if subject:
        return find_nifti_preview_file(sequence=sequence, subject_id=None, search_roots=search_roots)
    return None


def render_nifti_svg_preview(
    path: Path,
    *,
    requested_slice_index: int | None = None,
    plane: ImagePlane = "axial",
) -> dict[str, object]:
    import nibabel as nib
    import numpy as np

    img = nib.load(str(path))
    data = np.asanyarray(img.dataobj)
    dimensions = [int(item) for item in data.shape]
    if data.ndim < 3:
        raise ValueError(f"Expected 3D or 4D NIfTI, got shape {data.shape}")

    if data.ndim >= 4:
        data = data[..., data.shape[3] // 2]
    slice_index, slice_count, plane_data = _extract_plane(data, plane=plane, requested_slice_index=requested_slice_index)
    plane_data = np.asarray(plane_data, dtype=np.float32)
    plane_data = np.nan_to_num(plane_data, copy=False)
    plane_data = np.rot90(plane_data)
    plane_data = _downsample_plane(plane_data, max_size=96)

    low, high = np.percentile(plane_data, [1, 99])
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        low = float(np.min(plane_data))
        high = float(np.max(plane_data)) or low + 1.0
    normalized = np.clip((plane_data - low) / max(high - low, 1e-6), 0, 1)
    svg = _plane_to_svg(normalized, title=path.name)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return {
        "preview_url": f"data:image/svg+xml;base64,{encoded}",
        "plane": plane,
        "slice_index": slice_index,
        "slice_count": slice_count,
        "dimensions": dimensions,
    }


def _extract_plane(data, *, plane: ImagePlane, requested_slice_index: int | None):
    axis_by_plane = {"sagittal": 0, "coronal": 1, "axial": 2}
    axis = axis_by_plane[plane]
    slice_count = int(data.shape[axis])
    if requested_slice_index is None:
        slice_index = int(slice_count // 2)
    else:
        slice_index = max(0, min(int(requested_slice_index), slice_count - 1))

    if plane == "sagittal":
        plane_data = data[slice_index, :, :]
    elif plane == "coronal":
        plane_data = data[:, slice_index, :]
    else:
        plane_data = data[:, :, slice_index]
    return slice_index, slice_count, plane_data


def _sequence_aliases(sequence: str) -> list[str]:
    seq = sequence.lower()
    if seq in {"t1", "t1w", "t1-weighted"}:
        return ["t1w", "t1"]
    if seq in {"bold", "rsfmri", "fmri", "rest"}:
        return ["bold", "rest"]
    if seq == "flair":
        return ["flair"]
    if seq == "t2":
        return ["t2w", "t2"]
    if seq == "t1ce":
        return ["t1ce", "post", "contrast"]
    return [seq]


def _canonical_sequence_from_name(name: str) -> str | None:
    lower = name.lower()
    if "t1w" in lower or re.search(r"(^|[_-])t1([_.-]|$)", lower):
        return "T1"
    if "bold" in lower or "rest" in lower:
        return "BOLD"
    if "flair" in lower:
        return "FLAIR"
    if "t2w" in lower or re.search(r"(^|[_-])t2([_.-]|$)", lower):
        return "T2"
    if "t1ce" in lower or "contrast" in lower:
        return "T1ce"
    return None


def _subject_from_path(path: Path) -> str | None:
    for part in path.parts:
        if part.lower().startswith("sub-"):
            return part
    match = re.search(r"(sub-[a-zA-Z0-9]+)", path.name)
    return match.group(1) if match else None


def _session_from_path(path: Path) -> str | None:
    for part in path.parts:
        if part.lower().startswith("ses-"):
            return part
    match = re.search(r"(ses-[a-zA-Z0-9]+)", path.name)
    return match.group(1) if match else None


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)[:120]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _preview_search_roots(extra_roots: Iterable[str | Path] | None = None) -> list[Path]:
    extra_list = list(extra_roots or [])
    # When real search roots are provided, do NOT include synthetic fallback
    if extra_list:
        roots: list[Path] = []
        seen: set[str] = set()
        for raw_root in extra_list:
            if not str(raw_root).strip():
                continue
            root = Path(raw_root)
            key = str(root.resolve()) if root.exists() else str(root)
            if key in seen:
                continue
            seen.add(key)
            roots.append(root)
        # If all extra roots are stale/non-existent, fall back to synthetic
        # so that stale import records (e.g. from cleaned-up tmp_path tests)
        # don't permanently block image preview.
        if any(r.exists() for r in roots):
            return roots
        # Fall through to synthetic fallback

    # No real roots — use synthetic fallback only
    roots = []
    seen = set()
    for raw_root in PREVIEW_SEARCH_ROOTS:
        root = Path(raw_root)
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        roots.append(root)
    return roots


def _iter_nifti_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.name.endswith(".nii") or root.name.endswith(".nii.gz"):
            yield root
        return
    for path in root.rglob("*"):
        if path.is_file() and (path.name.endswith(".nii") or path.name.endswith(".nii.gz")):
            yield path


def _downsample_plane(plane, *, max_size: int):
    import numpy as np

    y_step = max(1, int(np.ceil(plane.shape[0] / max_size)))
    x_step = max(1, int(np.ceil(plane.shape[1] / max_size)))
    return plane[::y_step, ::x_step]


def _plane_to_svg(plane, *, title: str) -> str:
    height, width = plane.shape
    cells: list[str] = []
    for y in range(height):
        for x in range(width):
            value = int(float(plane[y, x]) * 255)
            if value <= 2:
                continue
            cells.append(
                f'<rect x="{x}" y="{y}" width="1" height="1" fill="rgb({value},{value},{value})" />'
            )
    safe_title = html.escape(title)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'shape-rendering="crispEdges" role="img" aria-label="{safe_title}">'
        "<rect width=\"100%\" height=\"100%\" fill=\"#05070b\" />"
        f"<title>{safe_title}</title>"
        f"{''.join(cells)}"
        "</svg>"
    )
