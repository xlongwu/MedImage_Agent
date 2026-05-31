"""Model Input Redaction Contract — M11-GUI-MODEL-CONTRACT-T004.

Pure-function module that validates and builds safe model prompt envelopes.
Only safe, minimized summaries are allowed.  All raw screenshots, clipboard,
credentials, paths, injection text, and unsafe actions are blocked.

This module:
  - Contains ONLY dataclasses, constants, and pure validation functions.
  - Does NOT call inference, load models, or import pywinauto.
  - Does NOT call provider APIs or GUI routes.
  - Does NOT read/write filesystem or network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Length limits ───────────────────────────────────────────────────────────

_MAX_USER_INTENT_CHARS = 256
_MAX_TASK_CONTEXT_CHARS = 512
_MAX_VISIBLE_STATE_CHARS = 512
_MAX_TOTAL_PROMPT_CHARS = 2048

# ── Sensitive pattern flags ─────────────────────────────────────────────────

_RAWDATA_PATTERNS = ("rawdata/", "data/raw/")
_DERIVATIVES_PATTERNS = ("derivatives/",)

_CREDENTIAL_PATTERNS = (
    "api_key", "apikey", "sk-", "token=", "password", "passwd",
    "private key", "begin rsa private key", "-----begin",
)

_SUBJECT_ID_PATTERNS = ("sub-", "sub_", "subject-", "subject_")

_POLICY_OVERRIDE_PATTERNS = (
    "provider=pywinauto", "use pywinauto",
    "approved=true", "approved = true",
    "disable guard", "disable safety",
    "ignore safety", "ignore previous instructions",
    "ignore rules", "bypass policy", "bypass guard",
    "override policy", "override guard",
)

_UNSAFE_ACTION_PATTERNS = (
    "click run", "click execute", "click submit",
    "execute pipeline", "run pipeline",
    "submit form",
)

_COORDINATE_PATTERNS = (
    "click at", "x=", "y=", "coordinates",
)

_CHAIN_OF_THOUGHT_PATTERNS = (
    "chain_of_thought", "chain of thought", "reasoning",
)

# ── Error codes ─────────────────────────────────────────────────────────────

_ERROR_CODES = {
    "input_schema_invalid": "MODEL_INPUT_SCHEMA_INVALID",
    "input_too_long": "MODEL_INPUT_TOO_LONG",
    "redaction_required": "MODEL_INPUT_REDACTION_REQUIRED",
    "redaction_failed": "MODEL_INPUT_REDACTION_FAILED",
    "contains_screenshot": "MODEL_INPUT_CONTAINS_SCREENSHOT",
    "contains_screenshot_ocr": "MODEL_INPUT_CONTAINS_SCREENSHOT_OCR",
    "contains_clipboard": "MODEL_INPUT_CONTAINS_CLIPBOARD",
    "contains_raw_ui_text": "MODEL_INPUT_CONTAINS_RAW_UI_TEXT",
    "contains_terminal": "MODEL_INPUT_CONTAINS_TERMINAL_OUTPUT",
    "contains_browser_dom": "MODEL_INPUT_CONTAINS_BROWSER_DOM",
    "contains_file_contents": "MODEL_INPUT_CONTAINS_FILE_CONTENTS",
    "contains_credential": "MODEL_INPUT_CONTAINS_CREDENTIAL",
    "contains_phi": "MODEL_INPUT_CONTAINS_PHI",
    "contains_subject_id": "MODEL_INPUT_CONTAINS_SUBJECT_ID",
    "contains_rawdata_path": "MODEL_INPUT_CONTAINS_RAWDATA_PATH",
    "contains_derivatives_path": "MODEL_INPUT_CONTAINS_DERIVATIVES_PATH",
    "contains_provider_override": "MODEL_INPUT_CONTAINS_PROVIDER_OVERRIDE",
    "contains_policy_override": "MODEL_INPUT_CONTAINS_POLICY_OVERRIDE",
    "contains_unsafe_action": "MODEL_INPUT_CONTAINS_UNSAFE_ACTION",
    "contains_coordinates": "MODEL_INPUT_CONTAINS_COORDINATES",
    "contains_chain_of_thought": "MODEL_INPUT_CONTAINS_CHAIN_OF_THOUGHT",
    "extra_permission_blocked": "MODEL_INPUT_EXTRA_PERMISSION_BLOCKED",
    "audit_required": "MODEL_INPUT_AUDIT_REQUIRED",
}


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelInputRedactionResult:
    """Result of validating and building a safe model input envelope."""

    ok: bool
    status: str
    error_code: str | None = None
    model_input_id: str | None = None
    prompt_envelope: dict[str, Any] | None = None
    redaction_applied: bool = False
    blocked_input_detected: bool = False
    blocked_input_categories: list[str] = field(default_factory=list)
    input_char_count_before: int = 0
    input_char_count_after: int = 0
    inference_allowed: bool = False
    model_called: bool = False
    provider_call_allowed: bool = False
    network_accessed: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "error_code": self.error_code,
            "model_input_id": self.model_input_id,
            "prompt_envelope": self.prompt_envelope,
            "redaction_applied": self.redaction_applied,
            "blocked_input_detected": self.blocked_input_detected,
            "blocked_input_categories": self.blocked_input_categories,
            "input_char_count_before": self.input_char_count_before,
            "input_char_count_after": self.input_char_count_after,
            "inference_allowed": self.inference_allowed,
            "model_called": self.model_called,
            "provider_call_allowed": self.provider_call_allowed,
            "network_accessed": self.network_accessed,
            "message": self.message,
        }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _blocked(code: str, message: str, mid: str | None = None,
             categories: list[str] | None = None,
             before: int = 0, after: int = 0) -> ModelInputRedactionResult:
    return ModelInputRedactionResult(
        ok=False, status="MODEL_INPUT_BLOCKED",
        error_code=code, message=message, model_input_id=mid,
        prompt_envelope=None,
        redaction_applied=False,
        blocked_input_detected=True,
        blocked_input_categories=categories or [],
        input_char_count_before=before,
        input_char_count_after=after,
        inference_allowed=False, model_called=False,
        provider_call_allowed=False, network_accessed=False,
    )


def _allowed(mid: str, envelope: dict, before: int, after: int) -> ModelInputRedactionResult:
    return ModelInputRedactionResult(
        ok=True, status="MODEL_INPUT_ALLOWED",
        model_input_id=mid, prompt_envelope=envelope,
        redaction_applied=True, blocked_input_detected=False,
        blocked_input_categories=[],
        input_char_count_before=before, input_char_count_after=after,
        inference_allowed=False, model_called=False,
        provider_call_allowed=False, network_accessed=False,
    )


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in patterns)


# ── Canonical safe input ────────────────────────────────────────────────────

def allowed_minimal_prompt_input_declaration() -> dict[str, Any]:
    return {
        "model_input_id": "input_safe_001",
        "user_intent_summary": "User requests safe observation.",
        "task_context_summary": "Mock-only GUI Agent context.",
        "visible_state_summary": "Sanitized visible state summary.",
        "policy_summary": {
            "allowed_action_policy": "record_observation_only",
            "blocked_capabilities": [
                "screenshot", "clipboard", "mouse", "keyboard",
                "network", "file_paths", "rawdata", "derivatives",
                "tier_1_2_3",
            ],
        },
        "session_safety_summary": {
            "provider_mode": "fixture_only",
            "real_provider_allowed": False,
            "pywinauto_allowed": False,
            "provider_call_allowed": False,
        },
    }


# ── Public API ──────────────────────────────────────────────────────────────

def validate_and_build_model_prompt_envelope(
    *,
    model_input_id: str | None = None,
    user_intent_summary: str | None = None,
    task_context_summary: str | None = None,
    visible_state_summary: str | None = None,
    policy_summary: dict[str, Any] | None = None,
    session_safety_summary: dict[str, Any] | None = None,
    raw_screenshot_present: bool | None = None,
    screenshot_ocr_text: str | None = None,
    clipboard_contents: str | None = None,
    raw_ui_text: str | None = None,
    raw_terminal_output: str | None = None,
    raw_browser_dom: str | None = None,
    raw_file_contents: str | None = None,
    redaction_required: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> ModelInputRedactionResult:
    """Validate and build a safe model prompt envelope.

    Only safe, minimized summaries are allowed.  All raw screenshots,
    clipboard, credentials, paths, injection text, and unsafe actions
    are blocked.
    """
    # ── 0. ID required ──
    if not model_input_id or not model_input_id.strip():
        return _blocked(_ERROR_CODES["input_schema_invalid"],
                        "model_input_id must be specified.")

    mid = model_input_id.strip()
    _redact = redaction_required if redaction_required is not None else True

    # ── 1. Raw inputs → blocked immediately ──
    if raw_screenshot_present is True:
        return _blocked(_ERROR_CODES["contains_screenshot"],
                        "Raw screenshots are blocked.", mid=mid,
                        categories=["screenshot"])
    if screenshot_ocr_text and screenshot_ocr_text.strip():
        return _blocked(_ERROR_CODES["contains_screenshot_ocr"],
                        "Screenshot OCR text is blocked.", mid=mid,
                        categories=["screenshot_ocr"])
    if clipboard_contents and clipboard_contents.strip():
        return _blocked(_ERROR_CODES["contains_clipboard"],
                        "Clipboard contents are blocked.", mid=mid,
                        categories=["clipboard"])
    if raw_ui_text and raw_ui_text.strip():
        return _blocked(_ERROR_CODES["contains_raw_ui_text"],
                        "Raw UI text is blocked.", mid=mid,
                        categories=["raw_ui_text"])
    if raw_terminal_output and raw_terminal_output.strip():
        return _blocked(_ERROR_CODES["contains_terminal"],
                        "Raw terminal output is blocked.", mid=mid,
                        categories=["terminal"])
    if raw_browser_dom and raw_browser_dom.strip():
        return _blocked(_ERROR_CODES["contains_browser_dom"],
                        "Raw browser DOM is blocked.", mid=mid,
                        categories=["browser"])
    if raw_file_contents and raw_file_contents.strip():
        return _blocked(_ERROR_CODES["contains_file_contents"],
                        "Raw file contents are blocked.", mid=mid,
                        categories=["file_contents"])

    # ── 2. Input strings ──
    usr = (user_intent_summary or "").strip()
    task = (task_context_summary or "").strip()
    vis = (visible_state_summary or "").strip()
    pol_text = str(policy_summary or {})
    ses_text = str(session_safety_summary or {})
    combined = f"{usr}\n{task}\n{vis}\n{pol_text}\n{ses_text}"
    total_before = len(combined)

    # ── 3. Length checks ──
    if len(usr) > _MAX_USER_INTENT_CHARS:
        return _blocked(_ERROR_CODES["input_too_long"],
                        f"user_intent_summary exceeds {_MAX_USER_INTENT_CHARS} chars.",
                        mid=mid, before=total_before, categories=["too_long"])
    if len(task) > _MAX_TASK_CONTEXT_CHARS:
        return _blocked(_ERROR_CODES["input_too_long"],
                        f"task_context_summary exceeds {_MAX_TASK_CONTEXT_CHARS} chars.",
                        mid=mid, before=total_before, categories=["too_long"])
    if len(vis) > _MAX_VISIBLE_STATE_CHARS:
        return _blocked(_ERROR_CODES["input_too_long"],
                        f"visible_state_summary exceeds {_MAX_VISIBLE_STATE_CHARS} chars.",
                        mid=mid, before=total_before, categories=["too_long"])
    if len(combined) > _MAX_TOTAL_PROMPT_CHARS:
        return _blocked(_ERROR_CODES["input_too_long"],
                        f"Total prompt exceeds {_MAX_TOTAL_PROMPT_CHARS} chars.",
                        mid=mid, before=total_before, categories=["too_long"])

    # ── 4. Sensitive pattern scanning ──
    text = combined.lower()
    categories: list[str] = []

    if _contains_any(text, _RAWDATA_PATTERNS):
        categories.append("rawdata_path")
    if _contains_any(text, _DERIVATIVES_PATTERNS):
        categories.append("derivatives_path")
    if _contains_any(text, _CREDENTIAL_PATTERNS):
        categories.append("credential")
    if _contains_any(text, _SUBJECT_ID_PATTERNS):
        categories.append("subject_id")
    if _contains_any(text, _POLICY_OVERRIDE_PATTERNS):
        categories.append("policy_override")
    if _contains_any(text, _UNSAFE_ACTION_PATTERNS):
        categories.append("unsafe_action")
    if _contains_any(text, _COORDINATE_PATTERNS):
        categories.append("coordinates")
    if _contains_any(text, _CHAIN_OF_THOUGHT_PATTERNS):
        categories.append("chain_of_thought")

    if categories:
        # Map first category to error code
        code_map = {
            "rawdata_path": "contains_rawdata_path",
            "derivatives_path": "contains_derivatives_path",
            "credential": "contains_credential",
            "subject_id": "contains_subject_id",
            "policy_override": "contains_policy_override",
            "unsafe_action": "contains_unsafe_action",
            "coordinates": "contains_coordinates",
            "chain_of_thought": "contains_chain_of_thought",
        }
        first = categories[0]
        return _blocked(_ERROR_CODES.get(code_map.get(first, ""), _ERROR_CODES["input_schema_invalid"]),
                        f"Blocked input category: {first}", mid=mid,
                        categories=categories, before=total_before)

    # ── 5. Redaction required check ──
    if not _redact:
        return _blocked(_ERROR_CODES["redaction_required"],
                        "redaction_required must be true.", mid=mid,
                        before=total_before)

    # ── 6. Extra permissions blocked ──
    if extra:
        for key in ("raw_prompt", "raw_model_context", "chain_of_thought",
                    "credentials", "api_key", "token",
                    "provider_call_allowed", "inference_allowed",
                    "model_called", "network_accessed"):
            if extra.get(key) is True or (isinstance(extra.get(key), str) and extra[key]):
                return _blocked(_ERROR_CODES["extra_permission_blocked"],
                                f"Extra permission '{key}' is blocked.", mid=mid,
                                before=total_before)

    # ── 7. Build safe prompt envelope ──
    envelope = {
        "prompt_envelope_version": "m11_input_v1",
        "model_input_id": mid,
        "source": "gui_model_input_minimizer",
        "user_intent_summary": usr,
        "task_context_summary": task,
        "visible_state_summary": vis,
        "policy_summary": policy_summary or {},
        "session_safety_summary": session_safety_summary or {},
        "provider_call_allowed": False,
        "redaction_applied": True,
    }
    # Truncate for safety in envelope
    envelope_text = str(envelope)
    after = min(len(envelope_text), _MAX_TOTAL_PROMPT_CHARS)

    return _allowed(mid, envelope, total_before, after)
