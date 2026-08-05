"""Read-only conversion dry-run planner for DICOM and loose NIfTI sources.

Inspects project imports using existing DICOM preflight, image source
discovery, and BIDS validation.  Produces a BIDS conversion plan preview
without writing files, executing external tools, or modifying rawdata.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    ConversionDryRunRequest,
    ConversionDryRunResponse,
    ConversionMappingPreview,
    ConversionSourceSummary,
    DatasetImportRecord,
)
from src.backend.app.services.dicom_preflight import build_dicom_preflight
from src.backend.app.services.funraw_t1raw_detector import detect_funraw_t1raw_layout
from src.backend.app.services.mock_store import mock_store

_NIFTI_EXT = (".nii", ".nii.gz")

# ── DICOM modality / protocol → BIDS mapping hints ──────────────────────────

_DICOM_MODALITY_BIDS: dict[str, str] = {
    "T1": "T1w",
    "T2": "T2w",
    "FLAIR": "FLAIR",
    "PD": "PD",
    "DTI": "dwi",
    "fMRI": "bold",
}

_DICOM_DESC_ANAT = {"T1", "T1W", "T1-WEIGHTED", "T2", "T2W", "T2-WEIGHTED", "FLAIR", "PD", "MPRAGE", "SPGR", "3D T1"}
_DICOM_DESC_FUNC = {"BOLD", "REST", "FMR", "RESTING", "RESTING_STATE", "FMRI", "EPI"}
_DICOM_DESC_DWI = {"DWI", "DTI", "DIFFUSION", "DIFF"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_subject_id(name: str) -> str | None:
    for part in name.replace("\\", "/").split("/")[-1].split("_"):
        if part.startswith("sub-"):
            return part
    if name.startswith("sub-"):
        end = name.find("_")
        return name[:end] if end > 0 else name
    return None


def _bids_suffix_from_desc(desc: str) -> str | None:
    desc = (desc or "").upper().replace("-", "").replace(" ", "").replace("_", "")
    if desc in _DICOM_DESC_ANAT:
        if "T2" in desc and "STAR" not in desc:
            return "T2w" if "FLAIR" not in desc else "FLAIR"
        return "T1w"
    if desc in _DICOM_DESC_FUNC:
        return "bold"
    if desc in _DICOM_DESC_DWI:
        return "dwi"
    return None


def _bids_modality(suffix: str) -> str:
    if suffix in {"T1w", "T2w", "T2star", "FLAIR", "PD", "PDT2", "inplaneT1", "inplaneT2"}:
        return "anat"
    if suffix == "bold":
        return "func"
    if suffix == "dwi":
        return "dwi"
    return "func"


def _confidence_for_mapping(subject_known: bool, suffix_known: bool) -> str:
    if subject_known and suffix_known:
        return "high"
    if subject_known or suffix_known:
        return "medium"
    return "manual_required"


def _relative_bids_path(subject: str, session: str | None, modality: str, suffix: str, task: str | None = None) -> str:
    ses_part = f"/{session}" if session else ""
    if task and suffix == "bold":
        name = f"{subject}_task-{task}_{suffix}.nii.gz"
    else:
        name = f"{subject}_{suffix}.nii.gz"
    return f"{subject}{ses_part}/{modality}/{name}"


def _classify_root(root: Path) -> str:
    """Classify a root as bids, dicom, loose_nifti, or unknown."""
    try:
        subject_dirs = [d for d in root.iterdir() if d.is_dir() and d.name.startswith("sub-")]
    except (OSError, PermissionError):
        return "unknown"
    if subject_dirs:
        return "bids"

    dicom_ext = {".dcm", ".ima"}
    nifti_count = 0
    dicom_found = False
    try:
        for path in root.rglob("*"):
            if path.is_file():
                sufs = "".join(path.suffixes)
                if sufs in _NIFTI_EXT:
                    nifti_count += 1
                    if nifti_count > 5:
                        break
                if path.suffix.lower() in dicom_ext:
                    dicom_found = True
    except (OSError, PermissionError):
        pass

    if dicom_found:
        return "dicom"
    if nifti_count > 0:
        return "loose_nifti"
    return "unknown"


def plan_conversion(
    project_id: str,
    request: ConversionDryRunRequest | dict[str, Any] | None,
) -> ConversionDryRunResponse:
    """Inspect imports and generate a conversion mapping preview."""
    if request is None:
        request = ConversionDryRunRequest()
    elif isinstance(request, dict) or hasattr(request, "get"):
        safe_req = {}
        for field_name in ConversionDryRunRequest.model_fields:
            if field_name in request:
                safe_req[field_name] = request[field_name]
        # Support either output_root or output_root_name
        if "output_root_name" not in safe_req:
            if "output_root_name" in request:
                safe_req["output_root_name"] = request["output_root_name"]
            elif "output_root" in request:
                safe_req["output_root_name"] = request["output_root"]
        try:
            request = ConversionDryRunRequest(**safe_req)
        except Exception:
            request = ConversionDryRunRequest()
            for k, v in safe_req.items():
                if hasattr(request, k):
                    setattr(request, k, v)

    def get_req_attr(name: str, default: Any = None) -> Any:
        if isinstance(request, dict):
            return request.get(name, default)
        return getattr(request, name, default)


    now = _now_iso()
    warnings: list[str] = []
    blocking: list[str] = []
    sources: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []

    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    rawdata_dir = str(metadata.get("rawdata_dir") or "")
    project_dir = str(metadata.get("project_dir") or "")
    config_path = str(metadata.get("project_config_path") or "")

    # Sanitize output_root_name to prevent path traversal
    safe_name = get_req_attr("output_root_name") or "conversion_output"
    safe_name = safe_name.replace("\\", "/")
    # Remove traversal patterns
    parts = [p for p in safe_name.split("/") if p and p not in (".", "..")]
    safe_name = "/".join(parts) if parts else "conversion_output"
    output_root = (
        Path(project_dir or Path(config_path).parent).expanduser().resolve()
        / safe_name
    ) if (project_dir or config_path) else None

    # ── Collect source roots ──
    imports: list[DatasetImportRecord] = []
    try:
        imports = [
            DatasetImportRecord(**item)
            for item in mock_store.list_import_records(project_id)
        ]
    except Exception as exc:
        warnings.append(f"IMPORT_LIST_FAILED: {exc}")

    root_map: dict[str, Path] = {}
    if rawdata_dir:
        root_map[rawdata_dir] = Path(rawdata_dir).expanduser().resolve()
    for imp in imports:
        if imp.path not in root_map:
            root_map[imp.path] = Path(imp.path).expanduser().resolve()

    # Filter by request source_import_ids if provided
    source_import_ids = get_req_attr("source_import_ids")
    if source_import_ids:
        filtered: dict[str, Path] = {}
        for imp in imports:
            if imp.dataset_id in source_import_ids:
                filtered[imp.path] = Path(imp.path).expanduser().resolve()
        if not filtered and rawdata_dir:
            filtered[rawdata_dir] = root_map.get(rawdata_dir, Path(rawdata_dir))
        root_map = filtered

    # ── FunRaw/T1Raw detection (check before generic DICOM preflight) ──
    funraw_t1raw_layout = detect_funraw_t1raw_layout(rawdata_dir) if rawdata_dir else None

    # ── Classify sources ──
    for root_str, root_path in root_map.items():
        source_type = _classify_root(root_path)
        exists = root_path.exists() and root_path.is_dir()
        file_count = 0
        series_count = 0
        subject_candidates: list[str] = []
        source_warnings: list[str] = []

        source_id = f"source_{hashlib_short(root_str)}"

        if source_type == "dicom" and get_req_attr("include_dicom"):
            try:
                preflight = build_dicom_preflight(
                    project_id=project_id,
                    roots=[str(root_path)],
                )
                file_count = preflight.dicom_file_count
                series_count = preflight.series_count
                for series in preflight.series:
                    sid = series.subject_id
                    if sid and sid not in subject_candidates:
                        subject_candidates.append(sid)
                source_warnings.extend(preflight.warnings[:10])
            except Exception as exc:
                source_warnings.append(f"DICOM_PREFLIGHT_FAILED: {exc}")

            for series in preflight.series:
                subj = series.subject_id or "sub-unknown"
                desc = series.series_description or series.protocol_name or ""
                suffix = _bids_suffix_from_desc(desc)
                session = None
                if get_req_attr("session_mapping_strategy") == "infer_from_dicom":
                    pass  # No session info in current preflight
                modality = _bids_modality(suffix) if suffix else "func"
                confidence = _confidence_for_mapping(
                    subject_known=series.subject_id is not None,
                    suffix_known=suffix is not None,
                )
                mappings.append({
                    "source_path": str(root_path),
                    "source_series_uid": series.series_instance_uid,
                    "source_type": "dicom_series",
                    "subject_id": subj if series.subject_id else None,
                    "session_id": session,
                    "modality": modality,
                    "suffix": suffix,
                    "task": "rest" if suffix == "bold" else None,
                    "suggested_relative_path": (
                        _relative_bids_path(subj, session, modality, suffix or "unknown", "rest" if suffix == "bold" else None)
                    ),
                    "confidence": confidence,
                    "warnings": [],
                })

        elif source_type == "loose_nifti" and get_req_attr("include_loose_nifti"):
            nifti_files = []
            try:
                for path in root_path.rglob("*"):
                    if path.is_file() and "".join(path.suffixes) in _NIFTI_EXT:
                        nifti_files.append(path)
                        file_count += 1
                        if file_count > 500:
                            break
            except (OSError, PermissionError):
                pass

            for nifti_path in nifti_files[:100]:
                subj = _parse_subject_id(nifti_path.name)
                if subj and subj not in subject_candidates:
                    subject_candidates.append(subj)
                suffix = _infer_nifti_suffix(nifti_path.name)
                confidence = _confidence_for_mapping(
                    subject_known=subj is not None,
                    suffix_known=suffix is not None,
                )
                subject = subj or "sub-unknown"
                modality = _bids_modality(suffix) if suffix else "func"
                mappings.append({
                    "source_path": str(nifti_path),
                    "source_series_uid": None,
                    "source_type": "nifti_file",
                    "subject_id": subject if subj else None,
                    "session_id": None,
                    "modality": modality,
                    "suffix": suffix,
                    "task": "rest" if suffix == "bold" else None,
                    "suggested_relative_path": (
                        _relative_bids_path(subject, None, modality, suffix or "unknown", "rest" if suffix == "bold" else None)
                    ),
                    "confidence": confidence,
                    "warnings": [],
                })

        sources.append({
            "source_id": source_id,
            "source_type": source_type,
            "root": root_str,
            "exists": exists,
            "file_count": file_count,
            "subject_candidates": subject_candidates,
            "series_count": series_count,
            "warnings": source_warnings,
        })

    # ── FunRaw/T1Raw path-based mapping ──
    if funraw_t1raw_layout and funraw_t1raw_layout["layout_type"] == "funraw_t1raw":
        ft = funraw_t1raw_layout
        # Use FunRaw/T1Raw mappings when no mappings exist or existing ones are low-confidence
        # (empty mappings → True: generic DICOM preflight failed, e.g. no pydicom)
        if not mappings or any(m["confidence"] != "high" for m in mappings):
            mappings.clear()
            # Update source summaries with detected counts
            for s in sources:
                if s["source_type"] == "dicom":
                    s["file_count"] = ft["dicom_file_count"]
                    s["series_count"] = ft["series_count"]
                    s["subject_candidates"] = ft["subject_ids"]
                    if ft["dicom_file_count"] > 0:
                        s["source_type"] = "dicom"

            # Add mapping candidates from path structure
            for entry in ft["per_subject_modality"]:
                subj = entry["subject_id"]
                root_name = entry["root_name"]
                suffix = entry["suggested_suffix"]
                mod_dir = entry["suggested_modality_dir"]
                task = "rest" if suffix == "bold" else None

                suggested_path = _relative_bids_path(
                    subj, None, mod_dir, suffix or "unknown",
                    task,
                )
                mappings.append({
                    "source_path": str(Path(rawdata_dir) / root_name / entry["raw_subject_name"]),
                    "source_series_uid": None,
                    "source_type": "dicom_series",
                    "subject_id": subj,
                    "session_id": None,
                    "modality": mod_dir,
                    "suffix": suffix,
                    "task": task,
                    "suggested_relative_path": suggested_path,
                    "confidence": "high",
                    "warnings": [],
                })

            if ft["nifti_file_count"] == 0:
                warnings.append(
                    "FunRaw/T1Raw DICOM layout detected. "
                    "No NIfTI files found; conversion to NIfTI is required "
                    "before NIfTI QC or preprocessing."
                )

    # ── Determine status ──
    if not sources or all(s["source_type"] == "unknown" for s in sources):
        status = "blocked"
        blocking.append("No convertible sources were found.")
    elif not mappings:
        status = "blocked"
        blocking.append("No mapping candidates could be generated from the available sources.")
    elif all(m["confidence"] == "manual_required" for m in mappings):
        status = "blocked"
        blocking.append("Every mapping requires manual review; no automated conversion is possible.")
    elif any(m["confidence"] == "manual_required" for m in mappings):
        status = "warning"
    else:
        status = "ready"

    # ── Check output root safety ──
    output_root_str: str | None = str(output_root) if output_root else None
    if output_root and rawdata_dir:
        try:
            output_root.relative_to(Path(rawdata_dir).expanduser().resolve())
            status = "blocked"
            blocking.append(
                "Output root preview is inside rawdata_dir. "
                "Conversion output must not overlap rawdata."
            )
        except ValueError:
            pass

    # ── Next actions ──
    next_actions: list[str] = []
    if status == "blocked":
        next_actions.append("Provide convertible DICOM or loose NIfTI sources via dataset imports.")
    if any(m["confidence"] == "manual_required" for m in mappings):
        next_actions.append("Review manual-required mappings and assign subject IDs and BIDS suffixes.")
    if status in ("ready", "warning"):
        next_actions.append("Review the conversion plan and approve before running real conversion.")
    if not next_actions:
        next_actions.append("Import a DICOM or loose NIfTI dataset to enable conversion planning.")

    return ConversionDryRunResponse(
        ok=True,
        project_id=project_id,
        status=status,
        dry_run=True,
        checked_at=now,
        target_layout=get_req_attr("target_layout", "bids"),
        output_root_name=get_req_attr("output_root_name", "converted_bids"),
        output_root_preview=output_root_str,
        source_summaries=[ConversionSourceSummary(**s) for s in sources],
        mapping_preview=[ConversionMappingPreview(**m) for m in mappings],
        blocking_issues=blocking[:10],
        warnings=warnings[:30],
        next_actions=next_actions[:10],
        safety_flags={
            "dry_run_only": True,
            "rawdata_read_only": True,
            "no_files_written": True,
            "no_external_tools_executed": True,
            "requires_user_review_before_conversion": True,
            "output_path_is_preview_only": True,
        },
    )


def _infer_nifti_suffix(name: str) -> str | None:
    """Try to infer BIDS suffix from a loose NIfTI filename."""
    base = name
    for ext in (".nii.gz", ".nii"):
        if base.endswith(ext):
            base = base[: -len(ext)]
            break
    parts = base.upper().replace("-", "").replace(" ", "").replace("_", "").replace(".", "")
    if "T1" in parts and "T2" not in parts:
        return "T1w"
    if "T2" in parts:
        return "T2w"
    if "FLAIR" in parts:
        return "FLAIR"
    if "BOLD" in parts or "REST" in parts or "FMRI" in parts:
        return "bold"
    if "DWI" in parts or "DTI" in parts:
        return "dwi"
    last = base.split("_")[-1] if "_" in base else base
    if last in {"T1w", "T2w", "FLAIR", "bold", "dwi"}:
        return last
    return None


def hashlib_short(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
