"""Model Audit Metadata Contract — M11-GUI-MODEL-CONTRACT-T005.

Pure-function module that validates and builds safe model audit metadata
records.  Never writes files — only validates that metadata is safe
for a future scoped audit writer.

This module:
  - Contains ONLY dataclasses, constants, and pure validation functions.
  - Does NOT write audit files, read filesystem, or access network.
  - Does NOT call inference, load models, or import pywinauto.
  - Does NOT call provider APIs or GUI routes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Allowed event types ─────────────────────────────────────────────────────

_ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({
    "MODEL_INPUT_MINIMIZED",
    "MODEL_INPUT_REDACTED",
    "MODEL_PROVIDER_POLICY_CHECKED",
    "MODEL_RUNTIME_DECLARED",
    "MODEL_INFERENCE_STARTED",
    "MODEL_INFERENCE_BLOCKED",
    "MODEL_INFERENCE_COMPLETED",
    "MODEL_OUTPUT_RECEIVED",
    "MODEL_OUTPUT_REJECTED",
    "MODEL_OUTPUT_NORMALIZED",
    "ADAPTER_DECISION_RECORDED",
    "GUARD_SUBMISSION_ATTEMPTED",
    "GUARD_SUBMISSION_BLOCKED",
    "GUARD_SUBMISSION_ALLOWED",
    "MOCK_PROVIDER_CALLED",
})

# ── Allowed audit roots ─────────────────────────────────────────────────────

_ALLOWED_AUDIT_ROOTS: frozenset[str] = frozenset({
    "reports/gui/model_audit",
    "outputs/work/gui_agent/model_audit",
})

# ── Forbidden field keys (must not appear in audit metadata) ────────────────

_FORBIDDEN_FIELD_KEYS: frozenset[str] = frozenset({
    "raw_prompt", "full_prompt", "raw_model_output", "raw_output",
    "raw_text", "raw_json",
    "screenshot_bytes", "raw_screenshot", "screenshot_ocr_text",
    "clipboard_contents", "raw_clipboard",
    "raw_terminal_output", "raw_browser_dom", "raw_ui_text", "raw_file_contents",
    "chain_of_thought", "hidden_reasoning", "reasoning_trace",
    "credential", "credentials", "api_key", "token", "password",
    "private_key", "secret",
    "phi", "subject_id",
    "rawdata_path", "derivatives_path",
    "environment_variable", "shell_history", "provider_secret",
})

# ── Path unsafe patterns ────────────────────────────────────────────────────

_FORBIDDEN_PATH_SEGMENTS: frozenset[str] = frozenset({
    "rawdata", "data", "derivatives",
})

# ── Error codes ─────────────────────────────────────────────────────────────

_ERROR_CODES = {
    "audit_schema_invalid": "MODEL_AUDIT_SCHEMA_INVALID",
    "audit_event_unknown": "MODEL_AUDIT_EVENT_UNKNOWN",
    "audit_path_blocked": "MODEL_AUDIT_PATH_BLOCKED",
    "audit_write_failed": "MODEL_AUDIT_WRITE_FAILED",
    "audit_required": "MODEL_AUDIT_REQUIRED",
    "audit_redaction_required": "MODEL_AUDIT_REDACTION_REQUIRED",
    "audit_forbidden_field": "MODEL_AUDIT_FORBIDDEN_FIELD",
    "audit_retention_invalid": "MODEL_AUDIT_RETENTION_INVALID",
    "audit_run_id_invalid": "MODEL_AUDIT_RUN_ID_INVALID",
    "audit_output_id_invalid": "MODEL_AUDIT_OUTPUT_ID_INVALID",
    "extra_permission_blocked": "MODEL_AUDIT_EXTRA_PERMISSION_BLOCKED",
    "safety_flag_invalid": "MODEL_AUDIT_SAFETY_FLAG_INVALID",
    "provider_permission_blocked": "MODEL_AUDIT_PROVIDER_PERMISSION_BLOCKED",
    "guard_permission_invalid": "MODEL_AUDIT_GUARD_PERMISSION_INVALID",
}


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelAuditContractResult:
    """Result of validating and building a safe model audit record."""

    ok: bool
    status: str
    error_code: str | None = None
    audit_id: str | None = None
    audit_record: dict[str, Any] | None = None
    audit_path: str | None = None
    audit_write_allowed: bool = False
    audit_written: bool = False
    forbidden_field_detected: bool = False
    forbidden_fields: list[str] = field(default_factory=list)
    provider_call_allowed: bool = False
    submitted_to_guard: bool = False
    inference_allowed: bool = False
    model_called: bool = False
    desktop_touched: bool = False
    screenshot_captured: bool = False
    clipboard_accessed: bool = False
    mouse_used: bool = False
    keyboard_used: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "status": self.status, "error_code": self.error_code,
            "audit_id": self.audit_id, "audit_record": self.audit_record,
            "audit_path": self.audit_path,
            "audit_write_allowed": self.audit_write_allowed,
            "audit_written": self.audit_written,
            "forbidden_field_detected": self.forbidden_field_detected,
            "forbidden_fields": self.forbidden_fields,
            "provider_call_allowed": self.provider_call_allowed,
            "submitted_to_guard": self.submitted_to_guard,
            "inference_allowed": self.inference_allowed,
            "model_called": self.model_called,
            "desktop_touched": self.desktop_touched,
            "screenshot_captured": self.screenshot_captured,
            "clipboard_accessed": self.clipboard_accessed,
            "mouse_used": self.mouse_used,
            "keyboard_used": self.keyboard_used,
            "message": self.message,
        }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _blocked(code: str, message: str, audit_id: str | None = None,
             forbidden_fields: list[str] | None = None,
             **overrides) -> ModelAuditContractResult:
    return ModelAuditContractResult(
        ok=False, status="MODEL_AUDIT_BLOCKED",
        error_code=code, message=message,
        audit_id=audit_id, audit_record=None, audit_path=None,
        audit_write_allowed=False, audit_written=False,
        forbidden_field_detected=bool(forbidden_fields),
        forbidden_fields=forbidden_fields or [],
        provider_call_allowed=False, submitted_to_guard=False,
        inference_allowed=False, model_called=False,
        desktop_touched=False, screenshot_captured=False,
        clipboard_accessed=False, mouse_used=False, keyboard_used=False,
        **overrides,
    )


def _allowed(audit_id: str, record: dict, path: str,
             submitted: bool = False) -> ModelAuditContractResult:
    return ModelAuditContractResult(
        ok=True, status="MODEL_AUDIT_ALLOWED",
        audit_id=audit_id, audit_record=record, audit_path=path,
        audit_write_allowed=True, audit_written=False,
        forbidden_field_detected=False, forbidden_fields=[],
        provider_call_allowed=False,
        submitted_to_guard=submitted,
        inference_allowed=False, model_called=False,
        desktop_touched=False, screenshot_captured=False,
        clipboard_accessed=False, mouse_used=False, keyboard_used=False,
    )


def _is_id_safe(s: str) -> bool:
    return bool(s) and all(c.isalnum() or c in "_-." for c in s)


def _is_path_safe(path: str) -> bool:
    """Pure string check: is this path safe as an audit root?"""
    if not path or not path.strip():
        return False
    normalized = path.strip().replace("\\", "/")
    if ".." in normalized:
        return False
    if normalized.startswith("/") or (len(normalized) >= 2 and normalized[1] == ":"):
        return False
    if normalized.startswith("~"):
        return False
    lower = normalized.lower()
    for seg in _FORBIDDEN_PATH_SEGMENTS:
        if f"/{seg}/" in f"/{lower}/" or lower.startswith(f"{seg}/"):
            return False
    return True


def _scan_forbidden(obj: Any, prefix: str = "") -> list[str]:
    """Recursively scan a dict/list for forbidden field keys."""
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_lower = k.lower().replace(" ", "_")
            if key_lower in _FORBIDDEN_FIELD_KEYS or k.lower() in _FORBIDDEN_FIELD_KEYS:
                found.append(f"{prefix}{k}" if prefix else k)
            if isinstance(v, (dict, list)):
                found.extend(_scan_forbidden(v, f"{prefix}{k}." if prefix else f"{k}."))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                found.extend(_scan_forbidden(item, f"{prefix}[{i}]." if prefix else f""))
    return found


# ── Canonical safe declaration ──────────────────────────────────────────────

def allowed_model_audit_metadata_declaration() -> dict[str, Any]:
    return {
        "audit_id": "model_audit_safe_001",
        "run_id": "run_safe_001",
        "session_id": "gui_safe_001",
        "event_type": "MODEL_OUTPUT_NORMALIZED",
        "model_input_id": "input_safe_001",
        "model_output_id": "output_safe_001",
        "provider_metadata": {
            "provider_type": "fixture_only",
            "provider_status": "MODEL_PROVIDER_ALLOWED",
            "inference_allowed": False,
            "model_loaded": False,
            "network_accessed": False,
        },
        "adapter_metadata": {
            "adapter_decision": "mapped",
            "adapter_status": "NORMALIZED_ACTION_READY",
            "normalized_action_type": "record_observation",
            "provider_call_allowed_by_adapter": False,
        },
        "guard_metadata": {
            "submitted_to_guard": True,
            "guard_status": "GUI_GUARD_OK",
            "provider_call_allowed_by_guard": True,
            "gui_audit_id": "audit_abc",
        },
        "safety_flags": {
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        },
    }


# ── Public API ──────────────────────────────────────────────────────────────

def validate_and_build_model_audit_record(
    *,
    audit_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    event_type: str | None = None,
    model_input_id: str | None = None,
    model_output_id: str | None = None,
    provider_metadata: dict[str, Any] | None = None,
    redaction_metadata: dict[str, Any] | None = None,
    runtime_metadata: dict[str, Any] | None = None,
    output_metadata: dict[str, Any] | None = None,
    adapter_metadata: dict[str, Any] | None = None,
    guard_metadata: dict[str, Any] | None = None,
    safety_flags: dict[str, Any] | None = None,
    audit_root: str | None = "reports/gui/model_audit",
    retention_days: int | None = 7,
    audit_required: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> ModelAuditContractResult:
    """Validate and build a safe model audit metadata record."""

    # ── 0. Required fields ──
    if not audit_id or not isinstance(audit_id, str):
        return _blocked(_ERROR_CODES["audit_schema_invalid"],
                        "audit_id required.")
    aid = audit_id.strip()
    if not _is_id_safe(aid):
        return _blocked(_ERROR_CODES["audit_output_id_invalid"],
                        f"audit_id '{aid}' has invalid chars.", audit_id=aid)
    if not run_id or not _is_id_safe(run_id):
        return _blocked(_ERROR_CODES["audit_run_id_invalid"],
                        "run_id missing or invalid.", audit_id=aid)
    if not session_id or not _is_id_safe(session_id):
        return _blocked(_ERROR_CODES["audit_run_id_invalid"],
                        "session_id missing or invalid.", audit_id=aid)
    if not event_type or event_type not in _ALLOWED_EVENT_TYPES:
        return _blocked(_ERROR_CODES["audit_event_unknown"],
                        f"event_type '{event_type}' not allowed.", audit_id=aid)

    mid = model_input_id
    moid = model_output_id
    if moid and not _is_id_safe(moid):
        return _blocked(_ERROR_CODES["audit_output_id_invalid"],
                        f"model_output_id '{moid}' invalid chars.", audit_id=aid)

    # ── 1. Audit path scope ──
    root = (audit_root or "reports/gui/model_audit").strip()
    if root not in _ALLOWED_AUDIT_ROOTS:
        if not _is_path_safe(root):
            return _blocked(_ERROR_CODES["audit_path_blocked"],
                            f"Unsafe audit root: '{root}'.", audit_id=aid)
        return _blocked(_ERROR_CODES["audit_path_blocked"],
                        f"Audit root '{root}' not allowlisted.", audit_id=aid)
    if not _is_path_safe(root):
        return _blocked(_ERROR_CODES["audit_path_blocked"],
                        f"Unsafe audit root: '{root}'.", audit_id=aid)
    audit_path = f"{root}/{run_id}/model_audit_{aid}.json"

    # ── 2. Retention policy ──
    ret = retention_days if retention_days is not None else 7
    if ret < 1 or ret > 30:
        return _blocked(_ERROR_CODES["audit_retention_invalid"],
                        f"retention_days must be 1-30, got {ret}.", audit_id=aid)

    # ── 3. Build record ──
    record: dict[str, Any] = {
        "audit_schema_version": "m11_model_audit_v1",
        "audit_id": aid,
        "event_type": event_type,
        "run_id": run_id,
        "session_id": session_id,
    }
    if mid:
        record["model_input_id"] = mid
    if moid:
        record["model_output_id"] = moid
    if provider_metadata:
        record["provider"] = provider_metadata
    if redaction_metadata:
        record["redaction"] = redaction_metadata
    if runtime_metadata:
        record["runtime"] = runtime_metadata
    if output_metadata:
        record["output"] = output_metadata
    if adapter_metadata:
        record["adapter"] = adapter_metadata
    if guard_metadata:
        record["guard"] = guard_metadata
    if safety_flags:
        record["safety_flags"] = safety_flags

    # ── 4. Scan for forbidden fields ──
    forbidden = _scan_forbidden(record)
    if extra:
        forbidden.extend(_scan_forbidden(extra))
    if forbidden:
        return _blocked(_ERROR_CODES["audit_forbidden_field"],
                        f"Forbidden fields: {forbidden}", audit_id=aid,
                        forbidden_fields=forbidden)

    # ── 5. Metadata semantics validation ──
    prov = provider_metadata or {}
    if prov.get("inference_allowed") is True:
        return _blocked(_ERROR_CODES["provider_permission_blocked"],
                        "inference_allowed must be false.", audit_id=aid)
    if prov.get("model_loaded") is True:
        return _blocked(_ERROR_CODES["provider_permission_blocked"],
                        "model_loaded must be false.", audit_id=aid)
    if prov.get("network_accessed") is True:
        return _blocked(_ERROR_CODES["provider_permission_blocked"],
                        "network_accessed must be false.", audit_id=aid)

    adp = adapter_metadata or {}
    if adp.get("provider_call_allowed_by_adapter") is True:
        return _blocked(_ERROR_CODES["provider_permission_blocked"],
                        "adapter provider_call_allowed_by_adapter must be false.", audit_id=aid)

    grd = guard_metadata or {}
    if grd.get("provider_call_allowed_by_guard") is True:
        if grd.get("guard_status") != "GUI_GUARD_OK":
            return _blocked(_ERROR_CODES["guard_permission_invalid"],
                            "guard should not grant provider permission for blocked status.", audit_id=aid)

    sf = safety_flags or {}
    _flag_map = {"desktop_touched": "desktop_touched",
                 "screenshot_captured": "screenshot_captured",
                 "clipboard_accessed": "clipboard_accessed",
                 "mouse_used": "mouse_used",
                 "keyboard_used": "keyboard_used"}
    for key, attr in _flag_map.items():
        if sf.get(key) is True:
            return _blocked(_ERROR_CODES["safety_flag_invalid"],
                            f"{key} must be false.", audit_id=aid)

    # ── 6. Extra permissions blocked ──
    if extra:
        for key in _FORBIDDEN_FIELD_KEYS:
            if extra.get(key) is not None:
                return _blocked(_ERROR_CODES["audit_forbidden_field"],
                                f"Extra '{key}' is forbidden.", audit_id=aid,
                                forbidden_fields=[key])
        for key in ("audit_written", "audit_write_failed", "provider_call_allowed",
                    "inference_allowed", "model_called", "network_accessed"):
            if extra.get(key) is True:
                return _blocked(_ERROR_CODES["extra_permission_blocked"],
                                f"Extra permission '{key}=true' blocked.", audit_id=aid)
        if extra.get("audit_root") and not _is_path_safe(str(extra["audit_root"])):
            return _blocked(_ERROR_CODES["audit_path_blocked"],
                            "User-provided audit_root unsafe.", audit_id=aid)
        if extra.get("user_filename"):
            return _blocked(_ERROR_CODES["audit_path_blocked"],
                            "user_filename must not be provided.", audit_id=aid)

    # ── 7. Determine submitted_to_guard ──
    submitted = grd.get("submitted_to_guard", False) if grd else False

    # ── 8. Allowed ──
    return _allowed(aid, record, audit_path, submitted=submitted)
