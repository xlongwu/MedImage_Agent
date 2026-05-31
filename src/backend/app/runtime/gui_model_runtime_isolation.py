"""Model Runtime Isolation Declaration Validator — M11-GUI-MODEL-CONTRACT-T002.

Pure-function module that validates runtime isolation declarations.
Only fixture_only is allowed in the current phase.  All real runtime
types (local_process, local_worker, etc.) are blocked.

This module:
  - Contains ONLY dataclasses, constants, and pure validation functions.
  - Does NOT start worker processes, call inference, load models,
    or import pywinauto.
  - Does NOT call provider APIs or GUI routes.
  - Does NOT read/write filesystem or network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── Runtime taxonomy ────────────────────────────────────────────────────────

_ALLOWED_RUNTIME_TYPES: frozenset[str] = frozenset({"fixture_only"})

_BLOCKED_REAL_RUNTIME_TYPES: frozenset[str] = frozenset({
    "local_process",
    "local_worker",
    "local_server",
    "remote_server",
    "external_tool",
    "gpu_inference",
})

_ALLOWED_NETWORK_POLICIES: frozenset[str] = frozenset({"disabled"})
_ALLOWED_FILESYSTEM_POLICIES: frozenset[str] = frozenset({"none"})
_ALLOWED_OUTPUT_MODES: frozenset[str] = frozenset({"raw_model_output_envelope"})

# ── Error codes ─────────────────────────────────────────────────────────────

_ERROR_CODES = {
    "runtime_missing": "MODEL_RUNTIME_MISSING",
    "runtime_unknown": "MODEL_RUNTIME_UNKNOWN",
    "runtime_blocked": "MODEL_RUNTIME_BLOCKED",
    "runtime_real_disabled": "MODEL_RUNTIME_REAL_DISABLED",
    "inference_disabled": "MODEL_RUNTIME_INFERENCE_DISABLED",
    "sandbox_required": "MODEL_RUNTIME_SANDBOX_REQUIRED",
    "sandbox_disabled": "MODEL_RUNTIME_SANDBOX_DISABLED",
    "network_blocked": "MODEL_RUNTIME_NETWORK_BLOCKED",
    "filesystem_blocked": "MODEL_RUNTIME_FILESYSTEM_BLOCKED",
    "temp_scope_blocked": "MODEL_RUNTIME_TEMP_SCOPE_BLOCKED",
    "cache_scope_blocked": "MODEL_RUNTIME_CACHE_SCOPE_BLOCKED",
    "timeout_invalid": "MODEL_RUNTIME_TIMEOUT_INVALID",
    "memory_budget_invalid": "MODEL_RUNTIME_MEMORY_BUDGET_INVALID",
    "gpu_disabled": "MODEL_RUNTIME_GPU_DISABLED",
    "concurrency_invalid": "MODEL_RUNTIME_CONCURRENCY_INVALID",
    "queue_invalid": "MODEL_RUNTIME_QUEUE_INVALID",
    "provider_access_blocked": "MODEL_RUNTIME_PROVIDER_ACCESS_BLOCKED",
    "gui_api_access_blocked": "MODEL_RUNTIME_GUI_API_ACCESS_BLOCKED",
    "pywinauto_blocked": "MODEL_RUNTIME_PYWINAUTO_BLOCKED",
    "gui_automation_blocked": "MODEL_RUNTIME_GUI_AUTOMATION_BLOCKED",
    "output_mode_blocked": "MODEL_RUNTIME_OUTPUT_MODE_BLOCKED",
    "provider_permission_blocked": "MODEL_RUNTIME_PROVIDER_PERMISSION_BLOCKED",
    "extra_permission_blocked": "MODEL_RUNTIME_EXTRA_PERMISSION_BLOCKED",
}


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelRuntimeIsolationResult:
    """Result of validating a runtime isolation declaration."""

    ok: bool
    status: str
    error_code: str | None = None
    runtime_type: str | None = None
    inference_allowed: bool = False
    runtime_started: bool = False
    model_loaded: bool = False
    network_accessed: bool = False
    gpu_accessed: bool = False
    provider_call_allowed: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "error_code": self.error_code,
            "runtime_type": self.runtime_type,
            "inference_allowed": self.inference_allowed,
            "runtime_started": self.runtime_started,
            "model_loaded": self.model_loaded,
            "network_accessed": self.network_accessed,
            "gpu_accessed": self.gpu_accessed,
            "provider_call_allowed": self.provider_call_allowed,
            "message": self.message,
        }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _blocked(code: str, message: str, rtype: str | None = None,
             **extra) -> ModelRuntimeIsolationResult:
    return ModelRuntimeIsolationResult(
        ok=False, status="MODEL_RUNTIME_BLOCKED",
        error_code=code, message=message, runtime_type=rtype,
        inference_allowed=False, runtime_started=False,
        model_loaded=False, network_accessed=False,
        gpu_accessed=False, provider_call_allowed=False,
    )


def _allowed(rtype: str) -> ModelRuntimeIsolationResult:
    return ModelRuntimeIsolationResult(
        ok=True, status="MODEL_RUNTIME_ALLOWED", runtime_type=rtype,
        inference_allowed=False, runtime_started=False,
        model_loaded=False, network_accessed=False,
        gpu_accessed=False, provider_call_allowed=False,
    )


# ── Canonical fixture declaration ───────────────────────────────────────────

def allowed_fixture_runtime_declaration() -> dict[str, Any]:
    """Return the canonical fixture_only runtime declaration."""
    return {
        "runtime_type": "fixture_only",
        "runtime_sandbox_required": True,
        "runtime_sandbox_enabled": True,
        "inference_enabled": False,
        "runtime_started": False,
        "network_policy": "disabled",
        "filesystem_policy": "none",
        "temp_dir": None,
        "cache_dir": None,
        "timeout_seconds": 30,
        "hard_timeout_seconds": 60,
        "memory_budget_mb": 4096,
        "gpu_enabled": False,
        "gpu_memory_budget_mb": None,
        "max_concurrent_jobs": 1,
        "queue_limit": 10,
        "provider_access": False,
        "gui_api_access": False,
        "pywinauto_allowed": False,
        "gui_automation_allowed": False,
        "allowed_output_mode": "raw_model_output_envelope",
        "provider_call_allowed": False,
    }


# ── Public API ──────────────────────────────────────────────────────────────

def validate_model_runtime_declaration(
    *,
    runtime_type: str | None = None,
    runtime_sandbox_required: bool | None = None,
    runtime_sandbox_enabled: bool | None = None,
    inference_enabled: bool | None = None,
    runtime_started: bool | None = None,
    network_policy: str | None = None,
    filesystem_policy: str | None = None,
    temp_dir: str | None = None,
    cache_dir: str | None = None,
    timeout_seconds: int | None = None,
    hard_timeout_seconds: int | None = None,
    memory_budget_mb: int | None = None,
    gpu_enabled: bool | None = None,
    gpu_memory_budget_mb: int | None = None,
    max_concurrent_jobs: int | None = None,
    queue_limit: int | None = None,
    provider_access: bool | None = None,
    gui_api_access: bool | None = None,
    pywinauto_allowed: bool | None = None,
    gui_automation_allowed: bool | None = None,
    allowed_output_mode: str | None = None,
    provider_call_allowed: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> ModelRuntimeIsolationResult:
    """Validate a runtime isolation declaration.

    Current phase: ONLY fixture_only is allowed.  All real runtime
    types are blocked regardless of individual field values.
    """
    # ── 1. Runtime type required ──
    if not runtime_type or not runtime_type.strip():
        return _blocked(_ERROR_CODES["runtime_missing"],
                        "runtime_type must be specified.")
    rtype = runtime_type.strip().lower()

    # ── 2. Real runtime types → blocked ──
    if rtype in _BLOCKED_REAL_RUNTIME_TYPES:
        return _blocked(_ERROR_CODES["runtime_real_disabled"],
                        f"Real runtime '{rtype}' is disabled. "
                        "Only fixture_only is allowed.", rtype=rtype)

    # ── 3. Unknown runtime type → blocked ──
    if rtype not in _ALLOWED_RUNTIME_TYPES:
        return _blocked(_ERROR_CODES["runtime_unknown"],
                        f"Unknown runtime type '{rtype}'.", rtype=rtype)

    # ── 4. fixture_only — validate all policy fields ──
    _inf = inference_enabled if inference_enabled is not None else False
    _started = runtime_started if runtime_started is not None else False
    _net = (network_policy or "disabled").strip().lower()
    _fs = (filesystem_policy or "none").strip().lower()
    _temp = temp_dir
    _cache = cache_dir
    _timeout = timeout_seconds if timeout_seconds is not None else 30
    _hard = hard_timeout_seconds if hard_timeout_seconds is not None else 60
    _mem = memory_budget_mb if memory_budget_mb is not None else 4096
    _gpu = gpu_enabled if gpu_enabled is not None else False
    _gpu_mem = gpu_memory_budget_mb
    _conc = max_concurrent_jobs if max_concurrent_jobs is not None else 1
    _queue = queue_limit if queue_limit is not None else 10
    _prov = provider_access if provider_access is not None else False
    _gui_api = gui_api_access if gui_api_access is not None else False
    _pw = pywinauto_allowed if pywinauto_allowed is not None else False
    _auto = gui_automation_allowed if gui_automation_allowed is not None else False
    _out = (allowed_output_mode or "raw_model_output_envelope").strip().lower()
    _prov_call = provider_call_allowed if provider_call_allowed is not None else False
    _sandbox_req = runtime_sandbox_required if runtime_sandbox_required is not None else True
    _sandbox_en = runtime_sandbox_enabled if runtime_sandbox_enabled is not None else True

    if _inf is not False:
        return _blocked(_ERROR_CODES["inference_disabled"],
                        "inference_enabled must be false.", rtype=rtype)
    if _started is not False:
        return _blocked(_ERROR_CODES["runtime_real_disabled"],
                        "runtime_started must be false.", rtype=rtype)
    if _net != "disabled":
        return _blocked(_ERROR_CODES["network_blocked"],
                        f"network_policy must be 'disabled', got '{_net}'.", rtype=rtype)
    if _fs != "none":
        return _blocked(_ERROR_CODES["filesystem_blocked"],
                        f"filesystem_policy must be 'none', got '{_fs}'.", rtype=rtype)
    if _temp is not None:
        return _blocked(_ERROR_CODES["temp_scope_blocked"],
                        "temp_dir must be null.", rtype=rtype)
    if _cache is not None:
        return _blocked(_ERROR_CODES["cache_scope_blocked"],
                        "cache_dir must be null.", rtype=rtype)
    if _timeout <= 0:
        return _blocked(_ERROR_CODES["timeout_invalid"],
                        f"timeout_seconds must be > 0, got {_timeout}.", rtype=rtype)
    if _hard < _timeout:
        return _blocked(_ERROR_CODES["timeout_invalid"],
                        "hard_timeout_seconds must be >= timeout_seconds.", rtype=rtype)
    if _hard > 60:
        return _blocked(_ERROR_CODES["timeout_invalid"],
                        f"hard_timeout_seconds must be <= 60, got {_hard}.", rtype=rtype)
    if _mem <= 0:
        return _blocked(_ERROR_CODES["memory_budget_invalid"],
                        f"memory_budget_mb must be > 0, got {_mem}.", rtype=rtype)
    if _mem > 4096:
        return _blocked(_ERROR_CODES["memory_budget_invalid"],
                        f"memory_budget_mb must be <= 4096, got {_mem}.", rtype=rtype)
    if _gpu is not False:
        return _blocked(_ERROR_CODES["gpu_disabled"],
                        "gpu_enabled must be false.", rtype=rtype)
    if _gpu_mem is not None:
        return _blocked(_ERROR_CODES["gpu_disabled"],
                        "gpu_memory_budget_mb must be null.", rtype=rtype)
    if _conc != 1:
        return _blocked(_ERROR_CODES["concurrency_invalid"],
                        f"max_concurrent_jobs must be 1, got {_conc}.", rtype=rtype)
    if _queue <= 0:
        return _blocked(_ERROR_CODES["queue_invalid"],
                        f"queue_limit must be > 0, got {_queue}.", rtype=rtype)
    if _queue > 10:
        return _blocked(_ERROR_CODES["queue_invalid"],
                        f"queue_limit must be <= 10, got {_queue}.", rtype=rtype)
    if _prov is not False:
        return _blocked(_ERROR_CODES["provider_access_blocked"],
                        "provider_access must be false.", rtype=rtype)
    if _gui_api is not False:
        return _blocked(_ERROR_CODES["gui_api_access_blocked"],
                        "gui_api_access must be false.", rtype=rtype)
    if _pw is not False:
        return _blocked(_ERROR_CODES["pywinauto_blocked"],
                        "pywinauto_allowed must be false.", rtype=rtype)
    if _auto is not False:
        return _blocked(_ERROR_CODES["gui_automation_blocked"],
                        "gui_automation_allowed must be false.", rtype=rtype)
    if _out not in _ALLOWED_OUTPUT_MODES:
        return _blocked(_ERROR_CODES["output_mode_blocked"],
                        "allowed_output_mode must be 'raw_model_output_envelope'.", rtype=rtype)
    if _prov_call is not False:
        return _blocked(_ERROR_CODES["provider_permission_blocked"],
                        "provider_call_allowed must be false.", rtype=rtype)
    if _sandbox_req is not True:
        return _blocked(_ERROR_CODES["sandbox_required"],
                        "runtime_sandbox_required must be true.", rtype=rtype)
    if _sandbox_en is not True:
        return _blocked(_ERROR_CODES["sandbox_disabled"],
                        "runtime_sandbox_enabled must be true.", rtype=rtype)

    # ── 5. Extra permissions blocked ──
    if extra:
        for key in ("enable_real_runtime", "enable_inference",
                    "enable_pywinauto", "enable_gui_automation",
                    "provider_call_allowed"):
            if extra.get(key) is True:
                return _blocked(_ERROR_CODES["extra_permission_blocked"],
                                f"Extra permission '{key}=true' is blocked.", rtype=rtype)

    # ── 6. Allowed ──
    return _allowed(rtype)
