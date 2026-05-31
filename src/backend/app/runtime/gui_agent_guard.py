"""GUI Agent Provider Policy Gate — M9-GUI-GUARD-T002.

The provider policy gate is the first guard layer in the 14-layer GUI Agent
API guard pipeline.  It ensures that:

  - Only provider="mock" is allowed by default.
  - provider="pywinauto" and any real/desktop/browser/manual provider is blocked.
  - approved=true, environment variables, or feature flags alone do NOT bypass
    the provider gate in T002.
  - Blocked responses are structured with explicit safety flags.

This module is defensive: it blocks before any provider is constructed or
any GUI action is executed.  It does NOT call pywinauto, click, type_text,
capture_screenshot, or access clipboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Allowed provider set (T002: mock only) ──────────────────────────────────

_ALLOWED_PROVIDERS: frozenset[str] = frozenset({"mock"})

# Providers that are explicitly blocked (even if future feature flags are set)
_BLOCKED_PROVIDERS: frozenset[str] = frozenset({
    "pywinauto",
    "real",
    "desktop",
    "browser",
    "manual",
})

# ── Error codes ─────────────────────────────────────────────────────────────

_ERROR_CODES = {
    # Provider
    "provider_missing": "GUI_GUARD_PROVIDER_MISSING",
    "provider_unknown": "GUI_GUARD_PROVIDER_UNKNOWN",
    "provider_blocked": "GUI_GUARD_PROVIDER_BLOCKED",
    "real_provider_disabled": "GUI_GUARD_REAL_PROVIDER_DISABLED",
    "ci_real_provider_blocked": "GUI_GUARD_CI_REAL_PROVIDER_BLOCKED",
    # Session
    "session_invalid": "GUI_GUARD_SESSION_INVALID",
    "sandbox_required": "GUI_GUARD_SANDBOX_REQUIRED",
    "target_scope_required": "GUI_GUARD_TARGET_SCOPE_REQUIRED",
    "action_tier_blocked": "GUI_GUARD_ACTION_TIER_BLOCKED",
    "file_scope_blocked": "GUI_GUARD_FILE_SCOPE_BLOCKED",
    "screenshot_blocked": "GUI_GUARD_SCREENSHOT_BLOCKED",
    "clipboard_blocked": "GUI_GUARD_CLIPBOARD_BLOCKED",
    "network_blocked": "GUI_GUARD_NETWORK_BLOCKED",
    "external_app_blocked": "GUI_GUARD_EXTERNAL_APP_BLOCKED",
    "human_required": "GUI_GUARD_HUMAN_REQUIRED",
    "emergency_abort_required": "GUI_GUARD_EMERGENCY_ABORT_REQUIRED",
    "audit_required": "GUI_GUARD_AUDIT_REQUIRED",
    # Action
    "action_invalid": "GUI_GUARD_ACTION_INVALID",
    "action_unknown": "GUI_GUARD_ACTION_UNKNOWN",
    "action_not_allowed": "GUI_GUARD_ACTION_NOT_ALLOWED",
    "action_tier_mismatch": "GUI_GUARD_ACTION_TIER_MISMATCH",
    "read_only_required": "GUI_GUARD_READ_ONLY_REQUIRED",
    "keyboard_blocked": "GUI_GUARD_KEYBOARD_BLOCKED",
    "mouse_blocked": "GUI_GUARD_MOUSE_BLOCKED",
    "side_effect_blocked": "GUI_GUARD_SIDE_EFFECT_BLOCKED",
    "confirmation_unsupported": "GUI_GUARD_CONFIRMATION_UNSUPPORTED",
    # Stop conditions / Audit
    "audit_failed": "GUI_GUARD_AUDIT_FAILED",
    "stop_condition": "GUI_GUARD_STOP_CONDITION",
    "session_missing": "GUI_GUARD_SESSION_MISSING",
    "step_limit_exceeded": "GUI_GUARD_STEP_LIMIT_EXCEEDED",
    "duration_limit_exceeded": "GUI_GUARD_DURATION_LIMIT_EXCEEDED",
    "emergency_aborted": "GUI_GUARD_EMERGENCY_ABORTED",
}


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GuiGuardResult:
    """Result of a GUI Agent guard check.

    When ok=False, provider_call_allowed is always False and
    all desktop/screenshot/clipboard/mouse/keyboard flags are False.
    """

    ok: bool
    status: str
    error_code: str | None = None
    message: str = ""
    provider: str | None = None
    provider_call_allowed: bool = False
    desktop_touched: bool = False
    screenshot_captured: bool = False
    clipboard_accessed: bool = False
    mouse_used: bool = False
    keyboard_used: bool = False
    audit_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "error_code": self.error_code,
            "message": self.message,
            "provider_call_allowed": self.provider_call_allowed,
            "desktop_touched": self.desktop_touched,
            "screenshot_captured": self.screenshot_captured,
            "clipboard_accessed": self.clipboard_accessed,
            "mouse_used": self.mouse_used,
            "keyboard_used": self.keyboard_used,
            "audit_id": self.audit_id,
        }


# ── Private helpers ──────────────────────────────────────────────────────────

def _normalize_provider(raw: str | None) -> str | None:
    """Normalize provider string: strip, lowercase, collapse internal whitespace."""
    if raw is None:
        return None
    value = raw.strip().lower()
    # Collapse multiple spaces into single
    while "  " in value:
        value = value.replace("  ", " ")
    return value or None


def _blocked_result(
    error_code: str,
    message: str,
    provider: str | None = None,
) -> GuiGuardResult:
    """Factory for a blocked GuiGuardResult."""
    return GuiGuardResult(
        ok=False,
        status="GUI_GUARD_BLOCKED",
        error_code=error_code,
        message=message,
        provider=provider,
        provider_call_allowed=False,
        desktop_touched=False,
        screenshot_captured=False,
        clipboard_accessed=False,
        mouse_used=False,
        keyboard_used=False,
    )


def _allowed_result(provider: str) -> GuiGuardResult:
    """Factory for an allowed GuiGuardResult."""
    return GuiGuardResult(
        ok=True,
        status="GUI_GUARD_OK",
        provider=provider,
        provider_call_allowed=True,
    )


# ── Public API ───────────────────────────────────────────────────────────────

def validate_gui_provider_policy(
    *,
    provider: str | None,
    approved: bool | None = None,
    real_provider_feature_enabled: bool = False,
    allow_real_provider: bool = False,
    ci_mode: bool = False,
) -> GuiGuardResult:
    """Validate the GUI provider against the T002 mock-only policy.

    T002 policy: ONLY provider="mock" is allowed.  Everything else is blocked,
    regardless of approved=true, feature flags, or environment variables.

    Args:
        provider: The provider name from the request or session.
        approved: Whether the session has been approved (NOT considered in T002).
        real_provider_feature_enabled: Feature flag (NOT considered in T002).
        allow_real_provider: Explicit allow flag (NOT considered in T002).
        ci_mode: Whether running in CI (always blocks non-mock).

    Returns:
        GuiGuardResult with ok=True only for provider="mock".
    """
    normalized = _normalize_provider(provider)

    # ── 1. Provider missing ──
    if normalized is None:
        return _blocked_result(
            _ERROR_CODES["provider_missing"],
            "GUI provider not specified. Only provider=mock is allowed.",
        )

    # ── 2. Provider explicitly blocked ──
    if normalized in _BLOCKED_PROVIDERS:
        return _blocked_result(
            _ERROR_CODES["real_provider_disabled"],
            f"Real GUI provider '{normalized}' is disabled. Only provider=mock is allowed in T002.",
            provider=normalized,
        )

    # ── 3. Provider not in allowlist ──
    if normalized not in _ALLOWED_PROVIDERS:
        return _blocked_result(
            _ERROR_CODES["provider_unknown"],
            f"Unknown GUI provider '{normalized}'. Only provider=mock is allowed.",
            provider=normalized,
        )

    # ── 4. CI blocks non-mock (defense-in-depth; already covered by steps 1-3) ──
    if ci_mode and normalized != "mock":
        return _blocked_result(
            _ERROR_CODES["ci_real_provider_blocked"],
            "Real GUI provider is not allowed in CI. Only provider=mock is allowed.",
            provider=normalized,
        )

    # ── 5. Provider is "mock" → allowed ──
    # Deliberately ignore approved / feature flags — T002 is unconditionally mock-only.
    _ = approved
    _ = real_provider_feature_enabled
    _ = allow_real_provider

    return _allowed_result(normalized)


# ══════════════════════════════════════════════════════════════════════════════
# Session Declaration Validator — M9-GUI-GUARD-T003
# ══════════════════════════════════════════════════════════════════════════════

# T003 allowed values for session policy fields
_T003_ALLOWED_ACTION_TIERS: frozenset[int] = frozenset({0})
_T003_ALLOWED_SCREENSHOT_POLICIES: frozenset[str] = frozenset({"disabled"})
_T003_ALLOWED_CLIPBOARD_POLICIES: frozenset[str] = frozenset({"disabled"})
_T003_ALLOWED_NETWORK_POLICIES: frozenset[str] = frozenset({"disabled"})
_T003_ALLOWED_EXTERNAL_APP_POLICIES: frozenset[str] = frozenset({"declared_target_only"})
_T003_ALLOWED_REDACTION_POLICIES: frozenset[str] = frozenset({"required_for_persistence"})
_T003_MAX_DURATION_SECONDS: int = 300
_T003_MAX_STEP_LIMIT: int = 20

# File scope forbidden path segments (case-insensitive check)
_FILE_SCOPE_FORBIDDEN_SEGMENTS: frozenset[str] = frozenset({
    "rawdata",
    "data",
    "derivatives",
})


def _is_path_safe_for_file_scope(path: str) -> bool:
    """Check if a single file scope path is safe.

    Blocks:
      - Path traversal (..)
      - Arbitrary absolute paths ("/" or "C:" prefix)
      - Paths containing forbidden segments (rawdata, data, derivatives)
    """
    normalized = path.replace("\\", "/")

    # Block path traversal
    if ".." in normalized:
        return False

    # Block arbitrary absolute paths (must be relative or under allowed root)
    # Allow relative paths like "outputs/work/gui_agent/"
    if normalized.startswith("/"):
        return False
    # Windows absolute path (e.g., "C:/...")
    if len(normalized) >= 2 and normalized[1] == ":":
        return False

    # Block forbidden segments (rawdata, data, derivatives)
    lower = normalized.lower()
    for forbidden in _FILE_SCOPE_FORBIDDEN_SEGMENTS:
        # Match as path segment (preceded by / or start, followed by / or end)
        if f"/{forbidden}/" in f"/{lower}/":
            return False

    return True


def validate_gui_session_declaration(
    *,
    provider: str | None = None,
    gui_sandbox_mode: bool | None = None,
    target_application: str | None = None,
    target_window: str | None = None,
    allowed_action_tiers: list[int] | None = None,
    file_scope: list[str] | None = None,
    allow_rawdata_access: bool | None = None,
    allow_derivatives_write: bool | None = None,
    screenshot_policy: str | None = None,
    clipboard_policy: str | None = None,
    network_policy: str | None = None,
    external_app_policy: str | None = None,
    duration_limit_seconds: int | None = None,
    step_limit: int | None = None,
    human_present: bool | None = None,
    emergency_abort_enabled: bool | None = None,
    audit_log_required: bool | None = None,
    redaction_policy: str | None = None,
) -> GuiGuardResult:
    """Validate a GUI session declaration against T003 policy.

    T003 policy: mock-only, Tier 0 only, screenshot/disabled,
    clipboard/disabled, network/disabled, rawdata forbidden,
    derivatives-write forbidden, human-present required,
    emergency-abort required, audit required.

    Accepts explicit keyword arguments.  When a value is None, a
    safe default is applied (except for required fields like
    target_application, target_window, allowed_action_tiers, file_scope).

    Returns GuiGuardResult with ok=True only if all checks pass.
    """
    # ── Apply safe defaults for optional fields ──
    _sandbox = gui_sandbox_mode if gui_sandbox_mode is not None else True
    _rawdata = allow_rawdata_access if allow_rawdata_access is not None else False
    _deriv_write = allow_derivatives_write if allow_derivatives_write is not None else False
    _screenshot = (screenshot_policy or "disabled").strip().lower()
    _clipboard = (clipboard_policy or "disabled").strip().lower()
    _network = (network_policy or "disabled").strip().lower()
    _ext_app = (external_app_policy or "declared_target_only").strip().lower()
    _duration = duration_limit_seconds if duration_limit_seconds is not None else 300
    _steps = step_limit if step_limit is not None else 20
    _human = human_present if human_present is not None else True
    _abort = emergency_abort_enabled if emergency_abort_enabled is not None else True
    _audit = audit_log_required if audit_log_required is not None else True
    _redaction = (redaction_policy or "required_for_persistence").strip().lower()

    # ── 1. gui_sandbox_mode ──
    if _sandbox is not True:
        return _blocked_result(
            _ERROR_CODES["sandbox_required"],
            "gui_sandbox_mode must be true.",
        )

    # ── 2. provider ──
    # Provider gate is called separately; here we verify it's present.
    norm_provider = _normalize_provider(provider)
    if norm_provider is None:
        return _blocked_result(
            _ERROR_CODES["provider_missing"],
            "GUI provider must be specified.",
        )

    # ── 3. target_application ──
    if not target_application or not target_application.strip():
        return _blocked_result(
            _ERROR_CODES["target_scope_required"],
            "target_application must be specified and non-empty.",
        )

    # ── 4. target_window ──
    if not target_window or not target_window.strip():
        return _blocked_result(
            _ERROR_CODES["target_scope_required"],
            "target_window must be specified and non-empty.",
        )

    # ── 5. allowed_action_tiers ──
    if allowed_action_tiers is None or len(allowed_action_tiers) == 0:
        return _blocked_result(
            _ERROR_CODES["action_tier_blocked"],
            "allowed_action_tiers must be specified and non-empty. Only Tier 0 is allowed in T003.",
        )
    for tier in allowed_action_tiers:
        if not isinstance(tier, int):
            return _blocked_result(
                _ERROR_CODES["action_tier_blocked"],
                f"allowed_action_tiers must contain integers only. Got non-int value: {tier}.",
            )
        if tier not in _T003_ALLOWED_ACTION_TIERS:
            return _blocked_result(
                _ERROR_CODES["action_tier_blocked"],
                f"Action tier {tier} is not allowed in T003. Only Tier 0 is permitted.",
            )

    # ── 6. file_scope ──
    if file_scope is None or len(file_scope) == 0:
        return _blocked_result(
            _ERROR_CODES["file_scope_blocked"],
            "file_scope must be specified and non-empty.",
        )
    for path in file_scope:
        if not isinstance(path, str) or not path.strip():
            return _blocked_result(
                _ERROR_CODES["file_scope_blocked"],
                "file_scope must contain non-empty string paths only.",
            )
        if not _is_path_safe_for_file_scope(path.strip()):
            return _blocked_result(
                _ERROR_CODES["file_scope_blocked"],
                f"file_scope path is not allowed: '{path}'. "
                "Paths must not contain rawdata, data, derivatives, traversal (..), or be absolute.",
            )

    # ── 7. allow_rawdata_access ──
    if _rawdata is True:
        return _blocked_result(
            _ERROR_CODES["file_scope_blocked"],
            "allow_rawdata_access must be false.",
        )

    # ── 8. allow_derivatives_write ──
    if _deriv_write is True:
        return _blocked_result(
            _ERROR_CODES["file_scope_blocked"],
            "allow_derivatives_write must be false.",
        )

    # ── 9. screenshot_policy ──
    if _screenshot not in _T003_ALLOWED_SCREENSHOT_POLICIES:
        return _blocked_result(
            _ERROR_CODES["screenshot_blocked"],
            f"screenshot_policy '{_screenshot}' is not allowed in T003. "
            "Only 'disabled' is permitted.",
        )

    # ── 10. clipboard_policy ──
    if _clipboard not in _T003_ALLOWED_CLIPBOARD_POLICIES:
        return _blocked_result(
            _ERROR_CODES["clipboard_blocked"],
            f"clipboard_policy '{_clipboard}' is not allowed in T003. "
            "Only 'disabled' is permitted.",
        )

    # ── 11. network_policy ──
    if _network not in _T003_ALLOWED_NETWORK_POLICIES:
        return _blocked_result(
            _ERROR_CODES["network_blocked"],
            f"network_policy '{_network}' is not allowed in T003. "
            "Only 'disabled' is permitted.",
        )

    # ── 12. external_app_policy ──
    if _ext_app not in _T003_ALLOWED_EXTERNAL_APP_POLICIES:
        return _blocked_result(
            _ERROR_CODES["external_app_blocked"],
            f"external_app_policy '{_ext_app}' is not allowed in T003. "
            "Only 'declared_target_only' is permitted.",
        )

    # ── 13. duration_limit_seconds ──
    if _duration <= 0:
        return _blocked_result(
            _ERROR_CODES["session_invalid"],
            f"duration_limit_seconds must be positive, got {_duration}.",
        )
    if _duration > _T003_MAX_DURATION_SECONDS:
        return _blocked_result(
            _ERROR_CODES["session_invalid"],
            f"duration_limit_seconds must not exceed {_T003_MAX_DURATION_SECONDS}, got {_duration}.",
        )

    # ── 14. step_limit ──
    if _steps <= 0:
        return _blocked_result(
            _ERROR_CODES["session_invalid"],
            f"step_limit must be positive, got {_steps}.",
        )
    if _steps > _T003_MAX_STEP_LIMIT:
        return _blocked_result(
            _ERROR_CODES["session_invalid"],
            f"step_limit must not exceed {_T003_MAX_STEP_LIMIT}, got {_steps}.",
        )

    # ── 15. human_present ──
    if _human is not True:
        return _blocked_result(
            _ERROR_CODES["human_required"],
            "human_present must be true.",
        )

    # ── 16. emergency_abort_enabled ──
    if _abort is not True:
        return _blocked_result(
            _ERROR_CODES["emergency_abort_required"],
            "emergency_abort_enabled must be true.",
        )

    # ── 17. audit_log_required ──
    if _audit is not True:
        return _blocked_result(
            _ERROR_CODES["audit_required"],
            "audit_log_required must be true.",
        )

    # ── 18. redaction_policy ──
    if _redaction not in _T003_ALLOWED_REDACTION_POLICIES:
        return _blocked_result(
            _ERROR_CODES["session_invalid"],
            f"redaction_policy '{_redaction}' is not allowed in T003. "
            "Only 'required_for_persistence' is permitted.",
        )

    # ── All checks passed ──
    return _allowed_result(norm_provider)


# ══════════════════════════════════════════════════════════════════════════════
# Action Taxonomy + Tier Classifier — M9-GUI-GUARD-T004
# ══════════════════════════════════════════════════════════════════════════════

# ── M9-GUI-T003 Action Taxonomy (29 actions, 4 tiers) ──

_TIER_0_ACTIONS: frozenset[str] = frozenset({
    "record_observation",
    "get_window_title",
    "list_windows",
    "observe_visible_ui_state",
    "screenshot_ephemeral",
    "get_control_text",
    "get_menu_state",
})

_TIER_1_ACTIONS: frozenset[str] = frozenset({
    "focus_window",
    "scroll",
    "switch_tab",
    "wait_for_window",
    "open_non_sensitive_panel",
    "move_focus_within_declared_window",
})

_TIER_2_ACTIONS: frozenset[str] = frozenset({
    "fill_form_field_non_secret",
    "select_file_under_scoped_directory",
    "menu_select_read_only",
    "toggle_non_destructive_option",
    "click_dry_run",
    "type_text_scoped",
})

_TIER_3_ACTIONS: frozenset[str] = frozenset({
    "click_run",
    "click_execute",
    "click_submit",
    "save_file",
    "overwrite_file",
    "delete_file",
    "open_rawdata",
    "launch_external_app",
    "read_clipboard",
    "write_clipboard",
    "upload_file",
    "download_file",
    "network_submission",
    "enter_credentials",
    "accept_permission_dialog",
    "accept_security_dialog",
    "accept_license_dialog",
    "install_software",
    "send_email",
    "send_message",
    "unscoped_file_select",
    "raw_screenshot_persist",
})

# T004: only record_observation is allowed among all actions
_T004_ALLOWED_ACTIONS: frozenset[str] = frozenset({"record_observation"})


def classify_gui_action_tier(action_type: str | None) -> tuple[int | None, str | None]:
    """Classify a GUI action type into its risk tier.

    Returns (tier, error_message).
    - tier is an int 0-3, or None if unknown.
    - error_message is None if the action is known, or a string if unknown.

    T004 note: classification returns the tier, but the action validator
    further restricts to record_observation only.
    """
    if action_type is None:
        return None, "action_type is missing."
    normalized = action_type.strip().lower()
    if not normalized:
        return None, "action_type is empty."

    if normalized in _TIER_0_ACTIONS:
        return 0, None
    if normalized in _TIER_1_ACTIONS:
        return 1, None
    if normalized in _TIER_2_ACTIONS:
        return 2, None
    if normalized in _TIER_3_ACTIONS:
        return 3, None

    return None, f"Unknown action_type: '{action_type}'."


def validate_gui_action_declaration(
    *,
    action_type: str | None = None,
    declared_action_tier: int | None = None,
    read_only: bool | None = None,
    uses_screenshot: bool | None = None,
    uses_clipboard: bool | None = None,
    uses_keyboard: bool | None = None,
    uses_mouse: bool | None = None,
    network_access: bool | None = None,
    input_paths: list[str] | None = None,
    output_paths: list[str] | None = None,
    expected_side_effects: str | None = None,
    requires_per_action_confirmation: bool | None = None,
    approval_id: str | None = None,
    rollback_plan: str | None = None,
    stop_conditions: list[str] | None = None,
    session_allowed_action_tiers: list[int] | None = None,
    screenshot_policy: str | None = None,
    clipboard_policy: str | None = None,
    network_policy: str | None = None,
) -> GuiGuardResult:
    """Validate a GUI action declaration against T004 policy.

    T004 policy:
      - Only action_type="record_observation" is allowed.
      - Tier must be 0.  Declared tier must match computed tier.
      - read_only=true, no screenshot/clipboard/keyboard/mouse/network.
      - No input/output paths, no side effects.
      - No per-action confirmation in T004.
      - Stop conditions must be present and non-empty.

    Returns GuiGuardResult with ok=True only if all checks pass.
    """
    # ── Apply defaults for optional flags ──
    _screenshot = uses_screenshot if uses_screenshot is not None else False
    _clipboard = uses_clipboard if uses_clipboard is not None else False
    _keyboard = uses_keyboard if uses_keyboard is not None else False
    _mouse = uses_mouse if uses_mouse is not None else False
    _network = network_access if network_access is not None else False
    _read_only_val = read_only if read_only is not None else True
    _paths_in = input_paths if input_paths is not None else []
    _paths_out = output_paths if output_paths is not None else []
    _side_effects = (expected_side_effects or "none").strip().lower()
    _confirmation = requires_per_action_confirmation if requires_per_action_confirmation is not None else False
    _rollback = (rollback_plan or "none").strip().lower()
    _session_tiers = session_allowed_action_tiers if session_allowed_action_tiers is not None else [0]
    _screenshot_pol = (screenshot_policy or "disabled").strip().lower()
    _clipboard_pol = (clipboard_policy or "disabled").strip().lower()
    _network_pol = (network_policy or "disabled").strip().lower()

    # ── 1. action_type classification ──
    tier, tier_error = classify_gui_action_tier(action_type)
    if tier is None:
        return _blocked_result(
            _ERROR_CODES["action_unknown"] if action_type and action_type.strip() else _ERROR_CODES["action_invalid"],
            tier_error or "action_type must be specified and recognized.",
        )

    # ── 2. T004: only record_observation allowed ──
    norm_type = action_type.strip().lower() if action_type else ""
    if norm_type not in _T004_ALLOWED_ACTIONS:
        return _blocked_result(
            _ERROR_CODES["action_not_allowed"],
            f"action_type '{action_type}' is not allowed in T004. "
            "Only 'record_observation' is permitted.",
        )

    # ── 3. Tier validation ──
    if tier not in _session_tiers:
        return _blocked_result(
            _ERROR_CODES["action_tier_blocked"],
            f"Action tier {tier} ('{action_type}') is not in session allowed tiers {_session_tiers}.",
        )

    if tier > 0:
        return _blocked_result(
            _ERROR_CODES["action_tier_blocked"],
            f"Action tier {tier} ('{action_type}') is not allowed. Only Tier 0 is permitted in T004.",
        )

    # ── 4. Declared tier mismatch ──
    if declared_action_tier is None:
        return _blocked_result(
            _ERROR_CODES["action_tier_mismatch"],
            "declared_action_tier must be specified.",
        )
    if declared_action_tier != tier:
        return _blocked_result(
            _ERROR_CODES["action_tier_mismatch"],
            f"Declared action tier {declared_action_tier} does not match "
            f"computed tier {tier} for action '{action_type}'.",
        )

    # ── 5. read_only ──
    if _read_only_val is not True:
        return _blocked_result(
            _ERROR_CODES["read_only_required"],
            "read_only must be true in T004.",
        )

    # ── 6. screenshot ──
    if _screenshot is True:
        return _blocked_result(
            _ERROR_CODES["screenshot_blocked"],
            "uses_screenshot must be false in T004.",
        )

    # ── 7. clipboard ──
    if _clipboard is True:
        return _blocked_result(
            _ERROR_CODES["clipboard_blocked"],
            "uses_clipboard must be false in T004.",
        )

    # ── 8. keyboard ──
    if _keyboard is True:
        return _blocked_result(
            _ERROR_CODES["keyboard_blocked"],
            "uses_keyboard must be false in T004.",
        )

    # ── 9. mouse ──
    if _mouse is True:
        return _blocked_result(
            _ERROR_CODES["mouse_blocked"],
            "uses_mouse must be false in T004.",
        )

    # ── 10. network ──
    if _network is True:
        return _blocked_result(
            _ERROR_CODES["network_blocked"],
            "network_access must be false in T004.",
        )

    # ── 11. input_paths ──
    if len(_paths_in) > 0:
        return _blocked_result(
            _ERROR_CODES["file_scope_blocked"],
            "input_paths must be empty in T004.",
        )

    # ── 12. output_paths ──
    if len(_paths_out) > 0:
        return _blocked_result(
            _ERROR_CODES["file_scope_blocked"],
            "output_paths must be empty in T004.",
        )

    # ── 13. side effects ──
    if _side_effects not in ("none", ""):
        return _blocked_result(
            _ERROR_CODES["side_effect_blocked"],
            f"expected_side_effects must be 'none', got '{_side_effects}'.",
        )

    # ── 14. per-action confirmation ──
    if _confirmation is True:
        return _blocked_result(
            _ERROR_CODES["confirmation_unsupported"],
            "requires_per_action_confirmation must be false in T004.",
        )

    # ── 15. rollback_plan ──
    if _rollback not in ("none", ""):
        return _blocked_result(
            _ERROR_CODES["action_invalid"],
            f"rollback_plan must be 'none', got '{_rollback}'.",
        )

    # ── 16. stop_conditions ──
    if stop_conditions is None or len(stop_conditions) == 0:
        return _blocked_result(
            _ERROR_CODES["action_invalid"],
            "stop_conditions must be specified and non-empty.",
        )

    # ── 17. consent gate: screenshot_policy from session ──
    if norm_type == "screenshot_ephemeral" and _screenshot_pol != "ephemeral_only":
        return _blocked_result(
            _ERROR_CODES["screenshot_blocked"],
            "screenshot_ephemeral requires session screenshot_policy to allow it.",
        )

    # ── All checks passed ──
    _ = _clipboard_pol  # reserved for future per-policy checks
    _ = _network_pol
    _ = approval_id
    return _allowed_result("mock")


# ══════════════════════════════════════════════════════════════════════════════
# Audit Log + Stop-Condition Checker — M9-GUI-GUARD-T005
# ══════════════════════════════════════════════════════════════════════════════

import hashlib as _hashlib
from datetime import datetime as _datetime, timezone as _timezone


def _utc_now_iso() -> str:
    return _datetime.now(_timezone.utc).isoformat()


def _short_hash(*parts: str) -> str:
    seed = "|".join(parts).encode("utf-8")
    return "audit_" + _hashlib.sha256(seed).hexdigest()[:14]


@dataclass(frozen=True)
class GuiAuditRecord:
    """Immutable audit record for a single GUI step.

    Captures guard decisions, action metadata, and safety flags.
    Must never contain raw screenshot bytes, raw clipboard contents,
    raw credential values, raw API keys/tokens, or unredacted PHI.
    """

    audit_id: str
    session_id: str
    step_id: str
    timestamp: str
    provider: str
    target_application: str | None
    target_window: str | None
    action_type: str
    computed_action_tier: int | None
    declared_action_tier: int | None
    guard_result: str
    error_code: str | None
    approval_id: str | None = None
    screenshot_requested: bool = False
    clipboard_requested: bool = False
    keyboard_requested: bool = False
    mouse_requested: bool = False
    network_requested: bool = False
    input_paths: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    redaction_required: bool = False
    stop_condition_checked: bool = False
    provider_call_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "session_id": self.session_id,
            "step_id": self.step_id,
            "timestamp": self.timestamp,
            "provider": self.provider,
            "target_application": self.target_application,
            "target_window": self.target_window,
            "action_type": self.action_type,
            "computed_action_tier": self.computed_action_tier,
            "declared_action_tier": self.declared_action_tier,
            "guard_result": self.guard_result,
            "error_code": self.error_code,
            "approval_id": self.approval_id,
            "screenshot_requested": self.screenshot_requested,
            "clipboard_requested": self.clipboard_requested,
            "keyboard_requested": self.keyboard_requested,
            "mouse_requested": self.mouse_requested,
            "network_requested": self.network_requested,
            "input_paths": self.input_paths,
            "output_paths": self.output_paths,
            "redaction_required": self.redaction_required,
            "stop_condition_checked": self.stop_condition_checked,
            "provider_call_allowed": self.provider_call_allowed,
        }


def create_gui_audit_record(
    *,
    session_id: str,
    provider: str,
    action_type: str,
    guard_result: str,
    step_id: str = "",
    target_application: str | None = None,
    target_window: str | None = None,
    computed_action_tier: int | None = None,
    declared_action_tier: int | None = None,
    error_code: str | None = None,
    approval_id: str | None = None,
    screenshot_requested: bool = False,
    clipboard_requested: bool = False,
    keyboard_requested: bool = False,
    mouse_requested: bool = False,
    network_requested: bool = False,
    input_paths: list[str] | None = None,
    output_paths: list[str] | None = None,
    provider_call_allowed: bool = False,
    stop_condition_checked: bool = False,
) -> GuiAuditRecord:
    """Create an audit record for a GUI step.

    The audit record captures the guard decision and action metadata
    BEFORE any provider call.  It must never contain sensitive raw data
    (screenshot bytes, clipboard contents, credentials, tokens, PHI).

    Returns an immutable GuiAuditRecord.
    """
    ts = _utc_now_iso()
    sid = step_id or f"step_{ts}"
    audit_id = _short_hash(session_id, sid, action_type, ts)

    return GuiAuditRecord(
        audit_id=audit_id,
        session_id=session_id,
        step_id=sid,
        timestamp=ts,
        provider=provider,
        target_application=target_application,
        target_window=target_window,
        action_type=action_type,
        computed_action_tier=computed_action_tier,
        declared_action_tier=declared_action_tier,
        guard_result=guard_result,
        error_code=error_code,
        approval_id=approval_id,
        screenshot_requested=screenshot_requested,
        clipboard_requested=clipboard_requested,
        keyboard_requested=keyboard_requested,
        mouse_requested=mouse_requested,
        network_requested=network_requested,
        input_paths=list(input_paths or []),
        output_paths=list(output_paths or []),
        redaction_required=False,
        stop_condition_checked=stop_condition_checked,
        provider_call_allowed=provider_call_allowed,
    )


def validate_gui_stop_conditions(
    *,
    session_id: str | None = None,
    provider: str | None = None,
    human_present: bool | None = None,
    emergency_abort_enabled: bool | None = None,
    audit_log_required: bool | None = None,
    step_limit: int | None = None,
    current_step_count: int | None = None,
    duration_limit_seconds: int | None = None,
    session_age_seconds: float | None = None,
    stop_conditions: list[str] | None = None,
    emergency_abort_requested: bool = False,
) -> GuiGuardResult:
    """Validate session-level stop conditions before a GUI step.

    T005 checks are declaration-level / session-level only.
    Real UI stop detection (unexpected window, credential field,
    permission dialog) is reserved for future implementation phases.

    Returns GuiGuardResult with ok=True only if all checks pass.
    """
    _human = human_present if human_present is not None else True
    _abort_enabled = emergency_abort_enabled if emergency_abort_enabled is not None else True
    _audit = audit_log_required if audit_log_required is not None else True
    _step_limit = step_limit if step_limit is not None else 20
    _step_count = current_step_count if current_step_count is not None else 0
    _duration = duration_limit_seconds if duration_limit_seconds is not None else 300
    _age = session_age_seconds if session_age_seconds is not None else 0.0

    # ── 1. session_id ──
    if not session_id or not session_id.strip():
        return _blocked_result(
            _ERROR_CODES["session_missing"],
            "Session ID is missing or empty.",
        )

    # ── 2. provider ──
    norm_provider = _normalize_provider(provider)
    if norm_provider != "mock":
        return _blocked_result(
            _ERROR_CODES["real_provider_disabled"],
            "Provider must be 'mock'. Real providers are blocked.",
            provider=norm_provider or "unknown",
        )

    # ── 3. human_present ──
    if _human is not True:
        return _blocked_result(
            _ERROR_CODES["human_required"],
            "human_present must be true.",
        )

    # ── 4. emergency_abort_enabled ──
    if _abort_enabled is not True:
        return _blocked_result(
            _ERROR_CODES["emergency_abort_required"],
            "emergency_abort_enabled must be true.",
        )

    # ── 5. audit_log_required ──
    if _audit is not True:
        return _blocked_result(
            _ERROR_CODES["audit_required"],
            "audit_log_required must be true.",
        )

    # ── 6. step_limit ──
    if _step_limit <= 0:
        return _blocked_result(
            _ERROR_CODES["step_limit_exceeded"],
            f"step_limit must be positive, got {_step_limit}.",
        )
    if _step_count >= _step_limit:
        return _blocked_result(
            _ERROR_CODES["step_limit_exceeded"],
            f"Step limit exceeded: {_step_count}/{_step_limit}.",
        )

    # ── 7. duration_limit ──
    if _duration <= 0:
        return _blocked_result(
            _ERROR_CODES["duration_limit_exceeded"],
            f"duration_limit_seconds must be positive, got {_duration}.",
        )
    if _age > _duration:
        return _blocked_result(
            _ERROR_CODES["duration_limit_exceeded"],
            f"Duration limit exceeded: session age {_age:.0f}s > limit {_duration}s.",
        )

    # ── 8. stop_conditions ──
    if stop_conditions is None or len(stop_conditions) == 0:
        return _blocked_result(
            _ERROR_CODES["stop_condition"],
            "stop_conditions must be specified and non-empty.",
        )

    # ── 9. emergency_abort_requested ──
    if emergency_abort_requested is True:
        return _blocked_result(
            _ERROR_CODES["emergency_aborted"],
            "Emergency abort has been requested for this session.",
        )

    # ── All checks passed ──
    return _allowed_result(norm_provider)
