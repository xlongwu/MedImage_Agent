"""Read-only BIDS-like validation and repair-suggestion layer.

Scans project rawdata / import roots for common BIDS structural issues
and returns safe, non-destructive repair suggestions.  Never modifies
files, never executes external tools, never accepts arbitrary paths.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    BidsRepairSuggestion,
    BidsValidationIssue,
    BidsValidationResponse,
)

BIDSMODALITIES = {"anat", "func", "dwi", "fmap", "perf", "beh", "eeg", "meg", "ieeg", "pet"}
KNOWN_NIFTI_SUFFIXES = {
    "T1w",
    "T2w",
    "T2star",
    "FLAIR",
    "PD",
    "PDT2",
    "inplaneT1",
    "inplaneT2",
    "angio",
    "bold",
    "cbv",
    "phase",
    "sbref",
    "epi",
    "dwi",
    "dti",
    "fieldmap",
    "magnitude",
    "magnitude1",
    "magnitude2",
    "phase1",
    "phase2",
    "phasediff",
    "asl",
    "m0scan",
    "events",
    "channels",
    "coordsys",
    "photo",
    "defacemask",
    "head",
    "brain",
    "probseg",
    "mask",
    "label",
    "dseg",
    "ROI",
    "cbf",
    "ct",
    "pet",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _issue(
    severity: str,
    code: str,
    message: str,
    subject_id: str | None = None,
    session_id: str | None = None,
    modality: str | None = None,
    file_path: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "subject_id": subject_id,
        "session_id": session_id,
        "modality": modality,
        "file_path": file_path,
        "details": details or {},
    }


def _repair(
    action_type: str,
    title: str,
    description: str,
    *,
    source_path: str | None = None,
    suggested_path: str | None = None,
    command_preview: str | None = None,
    safe_to_auto_apply: bool = False,
    requires_user_review: bool = True,
    related_issue_codes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "action_type": action_type,
        "title": title,
        "description": description,
        "source_path": source_path,
        "suggested_path": suggested_path,
        "command_preview": command_preview,
        "safe_to_auto_apply": safe_to_auto_apply,
        "requires_user_review": requires_user_review,
        "related_issue_codes": related_issue_codes or [],
    }


def _parse_subject_id(path: Path) -> str | None:
    name = path.name
    if name.startswith("sub-"):
        end = name.find("_")
        return name[:end] if end > 0 else name
    return None


def _parse_session_id(name: str) -> str | None:
    for part in name.split("_"):
        if part.startswith("ses-"):
            return part
    return None


def _suffix_from_filename(name: str) -> str | None:
    """Extract the BIDS suffix entity from a NIfTI filename."""
    # Remove extensions
    for ext in (".nii.gz", ".nii"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    # Last underscore-separated entity is the suffix
    parts = name.split("_")
    if len(parts) >= 2:
        return parts[-1]
    return None


def validate_bids(roots: list[str]) -> BidsValidationResponse:
    """Scan BIDS-like roots and return issues + repair suggestions."""

    issues: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    now = _now_iso()

    subject_count = 0
    session_count = 0
    nifti_file_count = 0
    sidecar_json_count = 0
    tsv_file_count = 0

    valid_roots: list[str] = []
    all_roots: list[Path] = []

    for root_str in roots:
        try:
            root = Path(root_str).expanduser().resolve()
        except Exception as exc:
            warnings.append(f"BIDS_ROOT_INVALID: {root_str}: {exc}")
            continue
        if not root.exists() or not root.is_dir():
            warnings.append(f"BIDS_ROOT_MISSING: {root}")
            issues.append(
                _issue("error", "ROOT_MISSING", f"Root does not exist: {root}", file_path=str(root))
            )
            continue
        valid_roots.append(str(root))
        all_roots.append(root)

    if not all_roots:
        return BidsValidationResponse(
            ok=True,
            project_id="",
            status="fail",
            checked_at=now,
            roots=valid_roots,
            issues=[BidsValidationIssue(**i) for i in issues],
            repair_suggestions=[],
            warnings=warnings,
            errors=errors,
            next_actions=["Provide a valid BIDS or BIDS-like rawdata directory."],
        )

    # ── A. Root-level checks ──
    for root in all_roots:
        dd = root / "dataset_description.json"
        if dd.is_file():
            try:
                json.loads(dd.read_text(encoding="utf-8-sig"))
            except (JSONDecodeError, OSError):
                issues.append(
                    _issue(
                        "error",
                        "DATASET_DESC_MALFORMED",
                        f"dataset_description.json exists but is not valid JSON: {dd}",
                        file_path=str(dd),
                    )
                )
                repairs.append(
                    _repair(
                        "manual_review",
                        "Fix or regenerate dataset_description.json",
                        "The file is present but could not be parsed. Review the file and fix JSON syntax.",
                        source_path=str(dd),
                        related_issue_codes=["DATASET_DESC_MALFORMED"],
                    )
                )
        else:
            issues.append(
                _issue(
                    "warning",
                    "DATASET_DESC_MISSING",
                    f"No dataset_description.json found in root: {root}",
                    file_path=str(root),
                )
            )
            repairs.append(
                _repair(
                    "metadata_suggestion",
                    "Create dataset_description.json",
                    "A minimal dataset_description.json is required for BIDS compliance. "
                    "Create one with at least Name and BIDSVersion fields.",
                    suggested_path=str(root / "dataset_description.json"),
                    related_issue_codes=["DATASET_DESC_MISSING"],
                )
            )

        pt = root / "participants.tsv"
        if pt.is_file():
            tsv_file_count += 1

    # ── B. Subject/session structure ──
    all_subject_dirs: list[Path] = []
    loose_nifti: list[Path] = []
    for root in all_roots:
        for child in sorted(root.iterdir()):
            if child.is_dir() and child.name.startswith("sub-"):
                all_subject_dirs.append(child)
            elif child.is_file():
                for ext in (".nii.gz", ".nii"):
                    if child.name.endswith(ext):
                        loose_nifti.append(child)
                        break
                    if child.name.endswith(".json"):
                        # Check if it's a sidecar
                        stem = child.name
                        for ext2 in (".nii.gz.json", ".nii.json"):
                            if stem.endswith(ext2):
                                loose_nifti.append(child)
                                break
    subject_count = len(all_subject_dirs)

    for nifti_path in loose_nifti[:20]:
        issues.append(
            _issue(
                "error",
                "LOOSE_NIFTI",
                f"NIfTI file outside BIDS subject folder: {nifti_path.name}",
                file_path=str(nifti_path),
            )
        )
    if loose_nifti:
        repairs.append(
            _repair(
                "conversion_required",
                "Move or convert loose NIfTI files into BIDS structure",
                f"{len(loose_nifti)} NIfTI or sidecar file(s) were found outside "
                "subject folders. These should be moved into a proper sub-*/ses-*/modality/ "
                "structure. A future DICOM-to-BIDS conversion workflow can automate this.",
                related_issue_codes=["LOOSE_NIFTI"],
            )
        )

    # ── C/D/E. Per-subject checks ──
    seen_sessions: set[str] = set()
    for subj_dir in all_subject_dirs[:50]:
        subj_id = subj_dir.name
        # Check for session dirs
        ses_dirs = sorted(
            [d for d in subj_dir.iterdir() if d.is_dir() and d.name.startswith("ses-")]
        )
        if ses_dirs:
            for ses_dir in ses_dirs:
                seen_sessions.add(f"{subj_id}/{ses_dir.name}")
                _check_modality_dir(
                    subj_dir,
                    ses_dir,
                    subj_id,
                    issues,
                    repairs,
                    nifti_count_ref := [0],
                    json_count_ref := [0],
                )
                nifti_file_count += nifti_count_ref[0]
                sidecar_json_count += json_count_ref[0]
            session_count += len(ses_dirs)
        else:
            _check_modality_dir(
                subj_dir,
                subj_dir,
                subj_id,
                issues,
                repairs,
                nifti_count_ref := [0],
                json_count_ref := [0],
            )
            nifti_file_count += nifti_count_ref[0]
            sidecar_json_count += json_count_ref[0]

        # Check for files directly in subject dir (not in modality folder)
        for child in subj_dir.iterdir():
            if child.is_file():
                for ext in (".nii.gz", ".nii"):
                    if child.name.endswith(ext):
                        issues.append(
                            _issue(
                                "warning",
                                "NIFTI_OUTSIDE_MODALITY",
                                f"NIfTI file not inside a modality folder: {child.name}",
                                subject_id=subj_id,
                                file_path=str(child),
                            )
                        )
                        break

    # Detect subject mismatch between folder and filename
    for root in all_roots:
        for nifti in root.rglob("*.nii*"):
            if ".nii" not in nifti.suffix and ".gz" not in nifti.suffix:
                base = nifti.name
                for ext in (".nii.gz", ".nii"):
                    if base.endswith(ext):
                        base = base[: -len(ext)]
                        break
                continue
            base = nifti.name
            for ext in (".nii.gz", ".nii"):
                if base.endswith(ext):
                    base = base[: -len(ext)]
                    break
            file_subj = _parse_subject_id(Path(base))
            if not file_subj:
                issues.append(
                    _issue(
                        "warning",
                        "FILENAME_MISSING_SUB",
                        f"Filename does not contain sub-* entity: {nifti.name}",
                        file_path=str(nifti),
                    )
                )
                continue
            # Walk up to find parent sub- directory
            parent_subj = None
            for ancestor in nifti.parents:
                anc_subj = _parse_subject_id(ancestor)
                if anc_subj:
                    parent_subj = anc_subj
                    break
            if parent_subj and file_subj != parent_subj:
                issues.append(
                    _issue(
                        "warning",
                        "SUBJECT_MISMATCH",
                        f"Subject in filename ({file_subj}) does not match "
                        f"parent folder ({parent_subj}): {nifti.name}",
                        subject_id=parent_subj,
                        file_path=str(nifti),
                        details={"file_subject": file_subj, "folder_subject": parent_subj},
                    )
                )
                repairs.append(
                    _repair(
                        "manual_review",
                        f"Review subject mismatch: {file_subj} vs {parent_subj}",
                        f"The file {nifti.name} contains sub-{file_subj} but is inside "
                        f"a folder named {parent_subj}. Manually verify which subject "
                        "this file belongs to and rename or move accordingly.",
                        source_path=str(nifti),
                        related_issue_codes=["SUBJECT_MISMATCH"],
                    )
                )

    # ── Determine status ──
    dicom_count = 0
    from src.backend.app.services.funraw_t1raw_detector import detect_funraw_t1raw_layout

    for root in all_roots:
        ft = detect_funraw_t1raw_layout(root)
        if ft["layout_type"] == "funraw_t1raw":
            dicom_count += ft["dicom_file_count"]
        else:
            try:
                for child in root.rglob("*"):
                    if child.is_file() and (
                        child.suffix.lower() in (".dcm", ".ima") or child.name.isdigit()
                    ):
                        dicom_count += 1
                        if dicom_count > 10:
                            break
            except Exception:
                pass

    is_raw_dicom = nifti_file_count == 0 and dicom_count > 0

    if not all_roots:
        status = "fail"
    elif not subject_count and not nifti_file_count:
        if is_raw_dicom:
            status = "warning"
            warnings.append(
                "BIDS validation is expected to be incomplete before DICOM-to-NIfTI conversion. "
                "No NIfTI files found, but DICOM files are present."
            )
        else:
            status = "fail"
    elif issues and any(i["severity"] == "error" for i in issues):
        status = "fail"
    elif issues:
        status = "warning"
    else:
        status = "pass"

    # ── Next actions ──
    next_actions: list[str] = []
    issue_codes = {str(issue["code"]) for issue in issues}
    has_bids_content = bool(subject_count or nifti_file_count)
    if status == "fail":
        if "DATASET_DESC_MALFORMED" in issue_codes:
            next_actions.append("Fix or regenerate dataset_description.json in the root directory.")
        if not has_bids_content or "ROOT_MISSING" in issue_codes or "LOOSE_NIFTI" in issue_codes:
            next_actions.append("Provide a valid BIDS rawdata directory with sub-* folders.")
    elif is_raw_dicom:
        next_actions.append("Run DICOM-to-BIDS conversion to produce NIfTI/BIDS outputs.")
    if any(i["code"] == "DATASET_DESC_MISSING" for i in issues):
        next_actions.append("Create a dataset_description.json file in the root directory.")
    if loose_nifti:
        next_actions.append("Move loose NIfTI files into proper sub-*/ses-*/modality/ folders.")
    if any(i["code"] == "SUBJECT_MISMATCH" for i in issues):
        next_actions.append("Review subject-mismatch warnings and correct filenames.")

    return BidsValidationResponse(
        ok=True,
        project_id="",
        status=status,
        checked_at=now,
        roots=valid_roots,
        subject_count=subject_count,
        session_count=session_count,
        nifti_file_count=nifti_file_count,
        sidecar_json_count=sidecar_json_count,
        tsv_file_count=tsv_file_count,
        issues=[BidsValidationIssue(**i) for i in issues],
        repair_suggestions=[BidsRepairSuggestion(**r) for r in repairs],
        warnings=warnings[:30],
        errors=errors[:20],
        next_actions=next_actions[:10],
    )


def _check_modality_dir(
    subj_dir: Path,
    target_dir: Path,
    subj_id: str,
    issues: list[dict[str, Any]],
    repairs: list[dict[str, Any]],
    nifti_count_ref: list[int],
    json_count_ref: list[int],
) -> None:
    """Check modality subdirectories for NIfTI and sidecar structure."""
    ses_id = _parse_session_id(target_dir.name) if target_dir != subj_dir else None

    for mod_dir_name in sorted({d.name for d in target_dir.iterdir() if d.is_dir()}):
        if mod_dir_name in BIDSMODALITIES:
            mod_dir = target_dir / mod_dir_name
            for nifti_path in sorted(mod_dir.rglob("*.nii*")):
                suffix = "".join(nifti_path.suffixes)
                if suffix not in (".nii", ".nii.gz"):
                    continue
                nifti_count_ref[0] += 1
                name = nifti_path.name
                bids_suffix = _suffix_from_filename(name)

                # Check sidecar JSON
                base_name = name
                for ext in (".nii.gz", ".nii"):
                    if base_name.endswith(ext):
                        base_name = base_name[: -len(ext)]
                        break
                json_path = nifti_path.with_name(base_name + ".json")
                has_json = json_path.is_file()
                if has_json:
                    json_count_ref[0] += 1
                    try:
                        json.loads(json_path.read_text(encoding="utf-8"))
                    except (JSONDecodeError, OSError):
                        issues.append(
                            _issue(
                                "warning",
                                "SIDECAR_JSON_MALFORMED",
                                f"Sidecar JSON is not valid: {json_path.name}",
                                subject_id=subj_id,
                                session_id=ses_id,
                                modality=mod_dir_name,
                                file_path=str(json_path),
                            )
                        )
                        repairs.append(
                            _repair(
                                "manual_review",
                                "Fix malformed sidecar JSON",
                                f"The sidecar {json_path.name} could not be parsed. "
                                "Review and fix the JSON syntax.",
                                source_path=str(json_path),
                                related_issue_codes=["SIDECAR_JSON_MALFORMED"],
                            )
                        )

                # Bold-specific sidecar checks
                if bids_suffix == "bold" and not has_json:
                    issues.append(
                        _issue(
                            "warning",
                            "BOLD_SIDECAR_MISSING",
                            f"BOLD file missing sidecar JSON: {name}",
                            subject_id=subj_id,
                            session_id=ses_id,
                            modality=mod_dir_name,
                            file_path=str(nifti_path),
                        )
                    )
                    repairs.append(
                        _repair(
                            "metadata_suggestion",
                            "Create missing BOLD sidecar JSON",
                            f"The BOLD file {name} should have a companion "
                            f"{base_name}.json sidecar with at minimum "
                            "RepetitionTime and TaskName fields.",
                            suggested_path=str(json_path),
                            related_issue_codes=["BOLD_SIDECAR_MISSING"],
                        )
                    )

                # Warn on unknown BIDS suffix
                if bids_suffix and bids_suffix not in KNOWN_NIFTI_SUFFIXES:
                    issues.append(
                        _issue(
                            "warning",
                            "UNKNOWN_NIFTI_SUFFIX",
                            f"Unknown BIDS suffix '{bids_suffix}' for file: {name}",
                            subject_id=subj_id,
                            session_id=ses_id,
                            modality=mod_dir_name,
                            file_path=str(nifti_path),
                            details={"suffix": bids_suffix},
                        )
                    )
        else:
            # Unknown modality folder
            mod_dir = target_dir / mod_dir_name
            issues.append(
                _issue(
                    "warning",
                    "UNKNOWN_MODALITY",
                    f"Unknown modality folder: {mod_dir_name}",
                    subject_id=subj_id,
                    session_id=ses_id,
                    file_path=str(mod_dir),
                )
            )


def bids_summary_check(roots: list[str]) -> dict[str, Any]:
    """Lightweight summary for Data Readiness integration.

    Returns a dict with status, issue_count, repair_count — suitable
    for embedding as a DataReadinessCheck.
    """
    try:
        result = validate_bids(roots)
    except Exception as exc:
        return {
            "name": "bids_validation",
            "status": "unknown",
            "message": f"BIDS validation failed: {exc}",
            "details": {},
        }

    return {
        "name": "bids_validation",
        "status": (
            "pass"
            if result.status == "pass"
            else "warning"
            if result.status == "warning"
            else "fail"
        ),
        "message": (
            f"BIDS validation: {result.status}, "
            f"{len(result.issues)} issue(s), "
            f"{len(result.repair_suggestions)} repair suggestion(s)."
        ),
        "details": {
            "status": result.status,
            "issue_count": len(result.issues),
            "repair_count": len(result.repair_suggestions),
            "subject_count": result.subject_count,
            "nifti_count": result.nifti_file_count,
        },
    }
