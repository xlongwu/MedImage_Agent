"""GUI Agent Model Output Adapter — M10-GUI-AGENT-T003.

Pure-function module that validates and normalizes raw fine-tuned GUI Agent
model outputs into the Normalized GUI Action Schema.  Only safe observation
intent → record_observation is allowed in v1.

This module:
  - Contains ONLY dataclasses, constants, and pure validation functions.
  - Does NOT call provider APIs, GUI automation, model inference, or pywinauto.
  - Does NOT modify the existing guard pipeline.
  - Does NOT grant provider_call_allowed=true (that's the guard's job).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Reuse the canonical action taxonomy from the guard module
from src.backend.app.runtime.gui_agent_guard import classify_gui_action_tier

# ── Constants ──────────────────────────────────────────────────────────────

VALID_SOURCE = "fine_tuned_gui_agent"

# Tier labels for rejection policy text
_TIER_LABELS: dict[int | None, str] = {
    0: "Tier 0 (read-only observation)",
    1: "Tier 1 (low-risk navigation)",
    2: "Tier 2 (medium-risk interaction)",
    3: "Tier 3 (high-risk / blocked)",
    None: "Unknown tier",
}

# v1: only safe observation → record_observation
_V1_ALLOWED_ACTION = "record_observation"

# Intent classification keywords
_SAFE_OBSERVATION_KEYWORDS: frozenset[str] = frozenset({
    "observe", "observation", "record", "note", "inspect",
    "safe observation", "read only", "read-only", "readonly",
})

_AMBIGUOUS_KEYWORDS: frozenset[str] = frozenset({
    "continue", "proceed", "next step", "fix it", "handle it",
    "finish", "do the right thing", "do the next thing",
    "click the right thing", "click appropriate",
})

_RAW_COORDINATE_TERMS: frozenset[str] = frozenset({
    "click at", "move mouse", "drag from", "double click",
    "right click", "coordinates", "pixel",
})

_KEYBOARD_MOUSE_TERMS: frozenset[str] = frozenset({
    "press enter", "press key", "type ", "scroll down",
    "scroll up", "scroll ", "focus window", "switch tab",
    "switch window", "mouse over", "hover",
})

_PROVIDER_SELECTION_TERMS: frozenset[str] = frozenset({
    "pywinauto", "use pywinauto", "provider=",
    "call provider", "provider:",
})

_APPROVAL_OVERRIDE_TERMS: frozenset[str] = frozenset({
    "approved=true", "approved = true", "set approved",
    "enable approved",
})

_POLICY_OVERRIDE_TERMS: frozenset[str] = frozenset({
    "ignore previous rules", "ignore safety", "ignore policy",
    "disable guard", "disable safety", "bypass guard",
    "bypass policy", "override policy", "ignore instructions",
    "ignore rules",
})

_SCREENSHOT_TERMS: frozenset[str] = frozenset({
    "screenshot", "capture screen", "take screen", "screen capture",
})

_CLIPBOARD_TERMS: frozenset[str] = frozenset({
    "clipboard", "copy paste", "copy and paste", "read clipboard",
    "write clipboard",
})

_FILE_PATH_TERMS: frozenset[str] = frozenset({
    "open file", "select file", "save file", "delete file",
    "overwrite", "rawdata", "derivatives",
})

_NETWORK_TERMS: frozenset[str] = frozenset({
    "upload", "download", "browser", "open url", "http",
    "open browser",
})

_CREDENTIAL_TERMS: frozenset[str] = frozenset({
    "password", "api key", "token", "credential", "login",
    "enter password", "secret",
})

_SHELL_TERMS: frozenset[str] = frozenset({
    "run command", "shell", "exec", "system(", "subprocess",
    "os.system",
})

_EXTERNAL_APP_TERMS: frozenset[str] = frozenset({
    "launch app", "open application", "start program",
    "open matlab", "open spm",
})


# ── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelOutputValidationResult:
    """Result of validating and normalizing a raw model output.

    When ok=True, normalized_action is present and adapter_decision="mapped".
    When ok=False, rejection is present with a structured reason.
    """

    ok: bool
    status: str
    source: str
    model_output_id: str | None = None
    intent_type: str | None = None
    adapter_decision: str = "rejected"
    adapter_rejection_reason: str | None = None
    confidence: float | None = None
    rationale_summary: str | None = None
    normalized_action: dict[str, Any] | None = None
    rejection: dict[str, Any] | None = None
    safety_flags: dict[str, bool] = field(default_factory=lambda: {
        "provider_call_allowed": False,
        "desktop_touched": False,
        "screenshot_captured": False,
        "clipboard_accessed": False,
        "mouse_used": False,
        "keyboard_used": False,
    })

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "source": self.source,
            "model_output_id": self.model_output_id,
            "intent_type": self.intent_type,
            "adapter_decision": self.adapter_decision,
            "adapter_rejection_reason": self.adapter_rejection_reason,
            "confidence": self.confidence,
            "rationale_summary": self.rationale_summary,
            "normalized_action": self.normalized_action,
            "rejection": self.rejection,
            "safety_flags": self.safety_flags,
        }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _reject(
    model_output_id: str | None,
    reason: str,
    intent_type: str | None = None,
    blocked_terms: list[str] | None = None,
    computed_tier: int | None = None,
    confidence: float | None = None,
    rationale_summary: str | None = None,
) -> ModelOutputValidationResult:
    """Factory for a rejection result."""
    return ModelOutputValidationResult(
        ok=False,
        status="MODEL_ACTION_REJECTED",
        source=VALID_SOURCE,
        model_output_id=model_output_id,
        intent_type=intent_type,
        adapter_decision="rejected",
        adapter_rejection_reason=reason,
        confidence=confidence,
        rationale_summary=rationale_summary,
        normalized_action=None,
        rejection={
            "reason": reason,
            "blocked_terms": blocked_terms or [],
            "computed_tier": computed_tier,
            "policy": _tier_policy_text(computed_tier, reason),
        },
        safety_flags={
            "provider_call_allowed": False,
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        },
    )


def _mapped(
    model_output_id: str | None,
    normalized_action: dict[str, Any],
    confidence: float | None = None,
    rationale_summary: str | None = None,
) -> ModelOutputValidationResult:
    """Factory for a successful mapping result."""
    return ModelOutputValidationResult(
        ok=True,
        status="NORMALIZED_ACTION_READY",
        source=VALID_SOURCE,
        model_output_id=model_output_id,
        intent_type="safe_observation",
        adapter_decision="mapped",
        adapter_rejection_reason=None,
        confidence=confidence,
        rationale_summary=rationale_summary,
        normalized_action=normalized_action,
        rejection=None,
        safety_flags={
            "provider_call_allowed": False,  # Guard sets this later
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        },
    )


def _tier_policy_text(tier: int | None, reason: str) -> str:
    label = _TIER_LABELS.get(tier, "Unknown tier")
    if tier == 0:
        return f"{label}: only record_observation is allowed in v1."
    if tier in (1, 2):
        return f"{label}: blocked in current guard. Requires future contract."
    if tier == 3:
        return f"{label}: blocked by default."
    return f"Rejected: {reason}."


def _normalize_record_observation() -> dict[str, Any]:
    """Return the canonical v1-safe normalized action."""
    return {
        "action_type": "record_observation",
        "action_tier": 0,
        "read_only": True,
        "uses_screenshot": False,
        "uses_clipboard": False,
        "uses_keyboard": False,
        "uses_mouse": False,
        "network_access": False,
        "input_paths": [],
        "output_paths": [],
        "expected_side_effects": "none",
        "requires_per_action_confirmation": False,
        "approval_id": None,
        "rollback_plan": "none",
        "stop_conditions": ["unexpected_window", "credential_field"],
    }


def _contains_any(text: str | None, terms: frozenset[str]) -> bool:
    """Check if text contains any of the given terms (case-insensitive)."""
    if not text:
        return False
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _extract_blocked(raw_text: str | None, terms: frozenset[str]) -> list[str]:
    """Extract which specific terms were found in the text."""
    if not raw_text:
        return []
    lower = raw_text.lower()
    return [t for t in terms if t.lower() in lower]


# ── Intent classification ───────────────────────────────────────────────────

def classify_model_intent(
    raw_text: str | None,
    raw_json: dict[str, Any] | None = None,
) -> tuple[str | None, str | None]:
    """Classify the model's intent from raw output.

    Returns (intent_type, rejection_reason).
    - intent_type is one of: safe_observation, ambiguous, navigation,
      interaction, destructive_action, injection_or_policy_override, or None.
    - rejection_reason is the error code if the intent should be rejected.
    """
    if not raw_text or not raw_text.strip():
        return None, "unknown_intent"

    text = raw_text.strip().lower()

    # ── Check for JSON-level overrides first ──
    if raw_json:
        if isinstance(raw_json, dict):
            if raw_json.get("provider"):
                return None, "provider_selection_blocked"
            if raw_json.get("approved") is True:
                return None, "approval_override_blocked"
            # Multi-action plan
            if isinstance(raw_json.get("actions"), list) and len(raw_json["actions"]) > 1:
                return None, "multi_action_plan_blocked"
            # Raw coordinates
            action = raw_json.get("action", "")
            if isinstance(action, str):
                if action in ("click", "move", "drag", "type", "scroll", "focus"):
                    return None, _json_action_to_rejection(action, raw_json)

    # ── Policy override / injection detection ──
    if _contains_any(raw_text, _POLICY_OVERRIDE_TERMS):
        return "injection_or_policy_override", "policy_override_attempt"

    # ── Provider / approval bypass ──
    if _contains_any(raw_text, _PROVIDER_SELECTION_TERMS):
        return None, "provider_selection_blocked"
    if _contains_any(raw_text, _APPROVAL_OVERRIDE_TERMS):
        return None, "approval_override_blocked"

    # ── Shell command ──
    if _contains_any(raw_text, _SHELL_TERMS):
        return None, "shell_command_blocked"

    # ── Destructive / credentials ──
    if _contains_any(raw_text, _CREDENTIAL_TERMS):
        return "destructive_action", "credential_request_blocked"

    # ── Screenshot / clipboard / file / network / external app ──
    if _contains_any(raw_text, _SCREENSHOT_TERMS):
        return None, "screenshot_request_blocked"
    if _contains_any(raw_text, _CLIPBOARD_TERMS):
        return None, "clipboard_request_blocked"
    if _contains_any(raw_text, _NETWORK_TERMS):
        return None, "network_request_blocked"
    if _contains_any(raw_text, _EXTERNAL_APP_TERMS):
        return None, "external_app_blocked"
    if _contains_any(raw_text, _FILE_PATH_TERMS):
        # Distinguish file operations
        if _contains_any(raw_text, frozenset({"rawdata", "derivatives"})):
            if "rawdata" in text:
                return None, "rawdata_path_blocked"
            return None, "derivatives_write_blocked"
        if _contains_any(raw_text, frozenset({"save", "delete", "overwrite"})):
            return "destructive_action", "tier_3_action_blocked"
        return None, "file_path_blocked"

    # ── Keyboard / mouse ──
    if _contains_any(raw_text, _KEYBOARD_MOUSE_TERMS):
        return "navigation", "tier_1_action_blocked"

    # ── Raw coordinates ──
    if _contains_any(raw_text, _RAW_COORDINATE_TERMS):
        return None, "raw_coordinate_click_blocked"

    # ── Ambiguous ──
    if _contains_any(raw_text, _AMBIGUOUS_KEYWORDS):
        return None, "ambiguous_intent"

    # ── Safe observation ──
    if _contains_any(raw_text, _SAFE_OBSERVATION_KEYWORDS):
        return "safe_observation", None

    # ── Unknown ──
    return None, "unknown_intent"


def _json_action_to_rejection(action: str, raw_json: dict[str, Any]) -> str:
    """Map a JSON action string to a rejection reason."""
    lower = action.lower()
    if lower in ("click", "move", "drag"):
        if "x" in raw_json or "y" in raw_json:
            return "raw_coordinate_click_blocked"
        return "tier_2_action_blocked"
    if lower in ("type",):
        return "keyboard_mouse_blocked"
    if lower in ("scroll", "focus", "switch"):
        return "tier_1_action_blocked"
    if lower in ("run", "execute", "submit"):
        return "tier_3_action_blocked"
    return "unknown_action_blocked"


# ── Main entry point ────────────────────────────────────────────────────────

def validate_and_normalize_model_output(
    *,
    model_output_id: str | None = None,
    source: str | None = None,
    raw_text: str | None = None,
    raw_json: dict[str, Any] | None = None,
    observed_context_summary: str | None = None,
    timestamp: str | None = None,
    confidence: float | None = None,
    rationale_summary: str | None = None,
) -> ModelOutputValidationResult:
    """Validate a raw model output and normalize it if safe.

    v1 policy: only safe observation intent → record_observation.
    All other intents are rejected with structured reasons.

    Args:
        model_output_id: Unique model invocation identifier.
        source: Must be "fine_tuned_gui_agent".
        raw_text: Untrusted free-text model output.
        raw_json: Untrusted structured model output.
        observed_context_summary: Sanitized UI context (no secrets/PHI).
        timestamp: ISO-8601 UTC timestamp.
        confidence: Model confidence 0.0-1.0 (does NOT override policy).
        rationale_summary: Brief sanitized rationale.

    Returns:
        ModelOutputValidationResult with ok=True only for safe observation
        mapped to record_observation.
    """
    # ── 1. Source validation ──
    if source != VALID_SOURCE:
        return _reject(
            model_output_id, "unknown_intent",
            confidence=confidence, rationale_summary=rationale_summary,
        )

    # ── 2. Output ID required ──
    if not model_output_id or not model_output_id.strip():
        return _reject(
            None, "unknown_intent",
            confidence=confidence, rationale_summary=rationale_summary,
        )

    # ── 3. Intent classification ──
    intent_type, rejection_reason = classify_model_intent(raw_text, raw_json)

    if rejection_reason:
        return _reject(
            model_output_id,
            rejection_reason,
            intent_type=intent_type,
            blocked_terms=_extract_blocked(raw_text, _get_terms_for_reason(rejection_reason)),
            confidence=confidence,
            rationale_summary=rationale_summary,
        )

    if intent_type != "safe_observation":
        return _reject(
            model_output_id, "unknown_intent",
            confidence=confidence, rationale_summary=rationale_summary,
        )

    # ── 4. Validate the proposed action via json if present ──
    if raw_json:
        proposed = _extract_proposed_action(raw_json)
        if proposed:
            tier, tier_err = classify_gui_action_tier(proposed)
            if tier_err:
                return _reject(
                    model_output_id, "unknown_action_blocked",
                    blocked_terms=[proposed],
                    confidence=confidence, rationale_summary=rationale_summary,
                )
            if proposed != _V1_ALLOWED_ACTION:
                return _reject(
                    model_output_id,
                    f"tier_{tier}_action_blocked" if tier else "unknown_action_blocked",
                    intent_type=intent_type,
                    blocked_terms=[proposed],
                    computed_tier=tier,
                    confidence=confidence,
                    rationale_summary=rationale_summary,
                )

    # ── 5. Map to record_observation ──
    normalized = _normalize_record_observation()
    return _mapped(model_output_id, normalized, confidence=confidence,
                   rationale_summary=rationale_summary)


def _extract_proposed_action(raw_json: dict[str, Any]) -> str | None:
    """Extract a proposed action_type from raw JSON output."""
    if not isinstance(raw_json, dict):
        return None
    action = raw_json.get("action")
    if isinstance(action, str) and action.strip():
        return action.strip().lower()
    action_type = raw_json.get("action_type")
    if isinstance(action_type, str) and action_type.strip():
        return action_type.strip().lower()
    return None


def _get_terms_for_reason(reason: str) -> frozenset[str]:
    """Map a rejection reason to the relevant keyword set for blocked-term extraction."""
    mapping: dict[str, frozenset[str]] = {
        "provider_selection_blocked": _PROVIDER_SELECTION_TERMS,
        "approval_override_blocked": _APPROVAL_OVERRIDE_TERMS,
        "policy_override_attempt": _POLICY_OVERRIDE_TERMS,
        "screenshot_request_blocked": _SCREENSHOT_TERMS,
        "clipboard_request_blocked": _CLIPBOARD_TERMS,
        "network_request_blocked": _NETWORK_TERMS,
        "file_path_blocked": _FILE_PATH_TERMS,
        "rawdata_path_blocked": _FILE_PATH_TERMS,
        "derivatives_write_blocked": _FILE_PATH_TERMS,
        "credential_request_blocked": _CREDENTIAL_TERMS,
        "shell_command_blocked": _SHELL_TERMS,
        "external_app_blocked": _EXTERNAL_APP_TERMS,
        "keyboard_mouse_blocked": _KEYBOARD_MOUSE_TERMS,
        "raw_coordinate_click_blocked": _RAW_COORDINATE_TERMS,
        "tier_1_action_blocked": _KEYBOARD_MOUSE_TERMS,
        "tier_3_action_blocked": frozenset({"click", "run", "submit", "save", "delete"}),
        "ambiguous_intent": _AMBIGUOUS_KEYWORDS,
    }
    return mapping.get(reason, frozenset())
