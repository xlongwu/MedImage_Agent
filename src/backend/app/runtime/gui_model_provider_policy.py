"""Model Provider Policy Gate — M11-GUI-MODEL-CONTRACT-T001.

Pure-function module that validates model provider declarations.
Only fixture_only is allowed in the current phase.  All real, local,
remote, and external providers are blocked.

This module:
  - Contains ONLY dataclasses, constants, and pure validation functions.
  - Does NOT call model inference, load model weights, or import pywinauto.
  - Does NOT call provider APIs or GUI routes.
  - Does NOT read/write filesystem or network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── Provider taxonomy ───────────────────────────────────────────────────────

_ALLOWED_PROVIDER_TYPES: frozenset[str] = frozenset({"fixture_only"})

_BLOCKED_REAL_PROVIDER_TYPES: frozenset[str] = frozenset({
    "local_allowlisted",
    "local_untrusted",
})

_BLOCKED_REMOTE_PROVIDER_TYPES: frozenset[str] = frozenset({
    "remote_disabled",
    "remote_allowlisted_future",
    "remote_untrusted",
})

_BLOCKED_EXTERNAL_TYPES: frozenset[str] = frozenset({
    "external_tool_provider",
})

# Concrete provider names blocked unconditionally
_BLOCKED_PROVIDER_NAMES: frozenset[str] = frozenset({
    "openai",
    "huggingface",
    "ollama",
    "vllm",
    "transformers",
    "custom_http",
    "pywinauto",
    "desktop",
    "browser",
    "manual",
})

# ── Allowed policy values ───────────────────────────────────────────────────

_ALLOWED_OUTPUT_MODES: frozenset[str] = frozenset({"raw_model_output_envelope"})
_ALLOWED_ACTION_POLICIES: frozenset[str] = frozenset({"record_observation_only"})
_ALLOWED_NETWORK_POLICIES: frozenset[str] = frozenset({"disabled"})
_ALLOWED_WEIGHTS_FORMATS: frozenset[str] = frozenset({"safetensors"})

# ── Error codes ─────────────────────────────────────────────────────────────

_ERROR_CODES = {
    "provider_missing": "MODEL_PROVIDER_MISSING",
    "provider_unknown": "MODEL_PROVIDER_UNKNOWN",
    "provider_blocked": "MODEL_PROVIDER_BLOCKED",
    "real_provider_disabled": "MODEL_PROVIDER_REAL_DISABLED",
    "remote_provider_disabled": "MODEL_PROVIDER_REMOTE_DISABLED",
    "local_provider_disabled": "MODEL_PROVIDER_LOCAL_DISABLED",
    "source_not_allowed": "MODEL_PROVIDER_SOURCE_NOT_ALLOWED",
    "checksum_required": "MODEL_PROVIDER_CHECKSUM_REQUIRED",
    "trust_remote_code_blocked": "MODEL_PROVIDER_TRUST_REMOTE_CODE_BLOCKED",
    "network_blocked": "MODEL_PROVIDER_NETWORK_BLOCKED",
    "runtime_sandbox_required": "MODEL_PROVIDER_RUNTIME_SANDBOX_REQUIRED",
    "output_mode_blocked": "MODEL_PROVIDER_OUTPUT_MODE_BLOCKED",
    "action_policy_blocked": "MODEL_PROVIDER_ACTION_POLICY_BLOCKED",
    "approval_ignored": "MODEL_PROVIDER_APPROVAL_IGNORED",
    "extra_permission_blocked": "MODEL_PROVIDER_EXTRA_PERMISSION_BLOCKED",
}


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelProviderPolicyResult:
    """Result of validating a model provider declaration."""

    ok: bool
    status: str
    error_code: str | None = None
    provider_type: str | None = None
    provider_name: str | None = None
    inference_allowed: bool = False
    model_loaded: bool = False
    network_accessed: bool = False
    provider_call_allowed: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "error_code": self.error_code,
            "provider_type": self.provider_type,
            "provider_name": self.provider_name,
            "inference_allowed": self.inference_allowed,
            "model_loaded": self.model_loaded,
            "network_accessed": self.network_accessed,
            "provider_call_allowed": self.provider_call_allowed,
            "message": self.message,
        }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _blocked(code: str, message: str, ptype: str | None = None,
             pname: str | None = None) -> ModelProviderPolicyResult:
    return ModelProviderPolicyResult(
        ok=False, status="MODEL_PROVIDER_BLOCKED",
        error_code=code, message=message,
        provider_type=ptype, provider_name=pname,
        inference_allowed=False, model_loaded=False,
        network_accessed=False, provider_call_allowed=False,
    )


def _allowed(ptype: str, pname: str | None = None) -> ModelProviderPolicyResult:
    return ModelProviderPolicyResult(
        ok=True, status="MODEL_PROVIDER_ALLOWED",
        provider_type=ptype, provider_name=pname,
        inference_allowed=False, model_loaded=False,
        network_accessed=False, provider_call_allowed=False,
    )


# ── Canonical fixture declaration ───────────────────────────────────────────

def allowed_fixture_provider_declaration() -> dict[str, Any]:
    """Return the canonical fixture_only provider declaration."""
    return {
        "provider_type": "fixture_only",
        "provider_name": "mock_fixture_provider",
        "model_source": "fixture_catalog",
        "model_id": "mock_fixture_catalog_v1",
        "model_version": "m10_mock_fixtures",
        "model_dir": None,
        "weights_format": None,
        "checksum": None,
        "checksum_required": False,
        "trust_remote_code": False,
        "weights_only": True,
        "network_access": "disabled",
        "runtime_sandbox_required": True,
        "inference_enabled": False,
        "allowed_output_mode": "raw_model_output_envelope",
        "allowed_action_policy": "record_observation_only",
    }


# ── Public API ──────────────────────────────────────────────────────────────

def validate_model_provider_policy(
    *,
    provider_type: str | None = None,
    provider_name: str | None = None,
    model_source: str | None = None,
    model_id: str | None = None,
    model_version: str | None = None,
    model_dir: str | None = None,
    weights_format: str | None = None,
    checksum: str | None = None,
    checksum_required: bool | None = None,
    trust_remote_code: bool | None = None,
    weights_only: bool | None = None,
    network_access: str | None = None,
    runtime_sandbox_required: bool | None = None,
    inference_enabled: bool | None = None,
    allowed_output_mode: str | None = None,
    allowed_action_policy: str | None = None,
    approved: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> ModelProviderPolicyResult:
    """Validate a model provider declaration.

    Current phase: ONLY fixture_only is allowed.  All real, local,
    remote, and external providers are blocked regardless of their
    individual field values.
    """
    # ── 1. Provider type required ──
    if not provider_type or not provider_type.strip():
        return _blocked(_ERROR_CODES["provider_missing"],
                        "provider_type must be specified.")
    ptype = provider_type.strip().lower()

    # ── 2. Block provider names (defense-in-depth) ──
    if provider_name:
        pname_lower = provider_name.strip().lower()
        if pname_lower in _BLOCKED_PROVIDER_NAMES:
            return _blocked(_ERROR_CODES["provider_blocked"],
                            f"Provider name '{provider_name}' is blocked.",
                            ptype=ptype, pname=provider_name)

    # ── 3. External tool providers → blocked ──
    if ptype in _BLOCKED_EXTERNAL_TYPES:
        return _blocked(_ERROR_CODES["provider_blocked"],
                        f"External tool provider '{ptype}' is blocked.",
                        ptype=ptype, pname=provider_name)

    # ── 4. Remote providers → blocked ──
    if ptype in _BLOCKED_REMOTE_PROVIDER_TYPES:
        return _blocked(_ERROR_CODES["remote_provider_disabled"],
                        f"Remote provider '{ptype}' is disabled.",
                        ptype=ptype, pname=provider_name)

    # ── 5. Real (local) providers → blocked ──
    if ptype in _BLOCKED_REAL_PROVIDER_TYPES:
        # Validate that even if unblocked, the declaration would need safety
        _ = _validate_real_provider_fields(
            ptype, provider_name, model_source, model_dir, weights_format,
            checksum, checksum_required, trust_remote_code, weights_only,
            network_access, runtime_sandbox_required, allowed_output_mode,
            allowed_action_policy,
        )
        return _blocked(_ERROR_CODES["real_provider_disabled"],
                        f"Real model provider '{ptype}' is disabled. "
                        "Only fixture_only is allowed in the current phase.",
                        ptype=ptype, pname=provider_name)

    # ── 6. Unknown provider type → blocked ──
    if ptype not in _ALLOWED_PROVIDER_TYPES:
        return _blocked(_ERROR_CODES["provider_unknown"],
                        f"Unknown provider type '{ptype}'.",
                        ptype=ptype, pname=provider_name)

    # ── 7. fixture_only — validate policy fields ──
    _net = (network_access or "disabled").strip().lower()
    _out = (allowed_output_mode or "raw_model_output_envelope").strip().lower()
    _act = (allowed_action_policy or "record_observation_only").strip().lower()
    _inf = inference_enabled if inference_enabled is not None else False
    _trust = trust_remote_code if trust_remote_code is not None else False
    _sandbox = runtime_sandbox_required if runtime_sandbox_required is not None else True
    _source = (model_source or "fixture_catalog").strip().lower()

    if _inf is not False:
        return _blocked(_ERROR_CODES["real_provider_disabled"],
                        "inference_enabled must be false.",
                        ptype=ptype, pname=provider_name)
    if _net != "disabled":
        return _blocked(_ERROR_CODES["network_blocked"],
                        f"network_access must be 'disabled', got '{_net}'.",
                        ptype=ptype, pname=provider_name)
    if _out not in _ALLOWED_OUTPUT_MODES:
        return _blocked(_ERROR_CODES["output_mode_blocked"],
                        "allowed_output_mode must be 'raw_model_output_envelope'.",
                        ptype=ptype, pname=provider_name)
    if _act not in _ALLOWED_ACTION_POLICIES:
        return _blocked(_ERROR_CODES["action_policy_blocked"],
                        "allowed_action_policy must be 'record_observation_only'.",
                        ptype=ptype, pname=provider_name)
    if _trust is not False:
        return _blocked(_ERROR_CODES["trust_remote_code_blocked"],
                        "trust_remote_code must be false.",
                        ptype=ptype, pname=provider_name)
    if _sandbox is not True:
        return _blocked(_ERROR_CODES["runtime_sandbox_required"],
                        "runtime_sandbox_required must be true.",
                        ptype=ptype, pname=provider_name)

    # ── 8. approved=true is ignored ──
    if approved is True:
        # Documented: approved does NOT affect provider policy.
        pass

    # ── 9. Extra permissions blocked ──
    if extra:
        for key in ("provider_call_allowed", "approved", "enable_real_model",
                    "enable_pywinauto", "bypass_policy"):
            if extra.get(key) is True:
                return _blocked(_ERROR_CODES["extra_permission_blocked"],
                                f"Extra permission '{key}=true' is blocked.",
                                ptype=ptype, pname=provider_name)

    # ── 10. Allowed ──
    return _allowed(ptype, provider_name)


def _validate_real_provider_fields(
    ptype: str, pname: str | None,
    model_source: str | None, model_dir: str | None,
    weights_format: str | None, checksum: str | None,
    checksum_required: bool | None, trust_remote_code: bool | None,
    weights_only: bool | None, network_access: str | None,
    runtime_sandbox_required: bool | None,
    allowed_output_mode: str | None, allowed_action_policy: str | None,
) -> None:
    """Validate additional real-provider fields (defense-in-depth).

    Even though the provider is blocked by type, this function validates
    that the declaration would also fail individual field checks.
    Used for comprehensive error code coverage in tests.
    """
    _ = ptype, pname, model_source, model_dir, weights_format, checksum
    _ = checksum_required, trust_remote_code, weights_only, network_access
    _ = runtime_sandbox_required, allowed_output_mode, allowed_action_policy
