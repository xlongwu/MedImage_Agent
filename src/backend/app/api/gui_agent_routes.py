"""GUI Agent API routes — with M9-GUI-GUARD-T002 provider policy gate.

The provider policy gate validates every request that could trigger a
GUI provider call (session creation, step execution, screenshot capture).
Only provider="mock" is allowed; all real/desktop/browser/manual providers
are blocked.

This is Layer 3 of the 14-layer guard pipeline defined in
docs/桌面与前端/界面智能体接口防护设计.md.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.backend.app.api._errors import raise_api_error
from src.backend.app.api.models import (
    GuiAgentSessionRequest,
    GuiAgentStepRequest,
    MockAdapterStepRequest,
)
from src.backend.app.runtime.gui_agent import (
    abort_gui_agent_session,
    capture_gui_agent_screenshot,
    create_gui_agent_session,
    list_gui_agent_sessions,
    step_gui_agent_session,
)
from src.backend.app.runtime.gui_agent_guard import (
    create_gui_audit_record,
    validate_gui_provider_policy,
    validate_gui_session_declaration,
    validate_gui_action_declaration,
    validate_gui_stop_conditions,
)

router = APIRouter()

# ── Status code for blocked requests ──
# 403 Forbidden: the request was understood but the provider is not allowed.
_GUARD_HTTP_STATUS = 403


def _guard_provider(provider_value: str | None) -> None:
    """Run the provider policy gate and raise HTTPException if blocked."""
    result = validate_gui_provider_policy(provider=provider_value)
    if not result.ok:
        raise HTTPException(status_code=_GUARD_HTTP_STATUS, detail=result.to_dict())


def _guard_session(request: GuiAgentSessionRequest) -> None:
    """Run the session declaration validator and raise HTTPException if blocked.

    Maps the existing 'target_app' field to 'target_application' for the
    validator.  All session declaration fields are read directly from the
    Pydantic model (with safe defaults applied for missing fields).
    """
    result = validate_gui_session_declaration(
        provider=request.provider,
        gui_sandbox_mode=request.gui_sandbox_mode,
        target_application=request.target_app,
        target_window=request.target_window,
        allowed_action_tiers=request.allowed_action_tiers,
        file_scope=request.file_scope,
        allow_rawdata_access=request.allow_rawdata_access,
        allow_derivatives_write=request.allow_derivatives_write,
        screenshot_policy=request.screenshot_policy,
        clipboard_policy=request.clipboard_policy,
        network_policy=request.network_policy,
        external_app_policy=request.external_app_policy,
        duration_limit_seconds=request.duration_limit_seconds,
        step_limit=request.step_limit,
        human_present=request.human_present,
        emergency_abort_enabled=request.emergency_abort_enabled,
        audit_log_required=request.audit_log_required,
        redaction_policy=request.redaction_policy,
    )
    if not result.ok:
        raise HTTPException(status_code=_GUARD_HTTP_STATUS, detail=result.to_dict())


@router.get("/api/gui-agent/sessions")
def api_gui_agent_sessions() -> dict[str, Any]:
    return list_gui_agent_sessions()


@router.post("/api/gui-agent/sessions")
def api_gui_agent_create_session(request: GuiAgentSessionRequest) -> dict[str, Any]:
    # ── M9-GUI-GUARD-T002: provider policy gate ──
    _guard_provider(request.provider)
    # ── M9-GUI-GUARD-T003: session declaration validator ──
    _guard_session(request)
    try:
        return create_gui_agent_session(request.model_dump())
    except Exception as exc:
        raise_api_error(exc)


def _guard_action(request: GuiAgentStepRequest) -> None:
    """Run the action declaration validator and raise HTTPException if blocked.

    Maps model fields to the validator's keyword arguments.  Session-level
    policy fields (allowed tiers, screenshot/clipboard/network policy)
    use safe T003-compatible defaults since the session has already been
    validated at creation time.
    """
    result = validate_gui_action_declaration(
        action_type=request.action,
        declared_action_tier=request.action_tier,
        read_only=request.read_only,
        uses_screenshot=request.uses_screenshot,
        uses_clipboard=request.uses_clipboard,
        uses_keyboard=request.uses_keyboard,
        uses_mouse=request.uses_mouse,
        network_access=request.network_access,
        input_paths=request.input_paths,
        output_paths=request.output_paths,
        expected_side_effects=request.expected_side_effects,
        requires_per_action_confirmation=request.requires_per_action_confirmation,
        rollback_plan=request.rollback_plan,
        stop_conditions=request.stop_conditions,
        # Session-level policy: use T003-compatible defaults.
        # The session was validated at creation; these enforce consistency.
        session_allowed_action_tiers=[0],
        screenshot_policy="disabled",
        clipboard_policy="disabled",
        network_policy="disabled",
    )
    if not result.ok:
        raise HTTPException(status_code=_GUARD_HTTP_STATUS, detail=result.to_dict())


@router.post("/api/gui-agent/sessions/{session_id}/step")
def api_gui_agent_step(session_id: str, request: GuiAgentStepRequest) -> dict[str, Any]:
    # ── M9-GUI-GUARD-T004: action declaration validator ──
    _guard_action(request)

    # ── M9-GUI-GUARD-T005: read session for stop-condition + audit checks ──
    from src.backend.app.runtime.gui_agent import _read_session
    import time as _time_module

    session = _read_session(session_id)
    session_provider = session.get("provider", "mock")
    session_age = _time_module.time() - session.get("_created_at_ts", _time_module.time())

    # ── M9-GUI-GUARD-T005: stop-condition checker ──
    from src.backend.app.runtime.gui_agent_guard import classify_gui_action_tier
    computed_tier, _ = classify_gui_action_tier(request.action)
    stop_result = validate_gui_stop_conditions(
        session_id=session_id,
        provider=session_provider,
        human_present=session.get("human_present", True),
        emergency_abort_enabled=session.get("emergency_abort_enabled", True),
        audit_log_required=session.get("audit_log_required", True),
        step_limit=session.get("step_limit", 20),
        current_step_count=session.get("step_count", 0),
        duration_limit_seconds=session.get("duration_limit_seconds", 300),
        session_age_seconds=session_age,
        stop_conditions=request.stop_conditions,
        emergency_abort_requested=session.get("status") == "ABORTED",
    )
    if not stop_result.ok:
        # Create blocked audit record
        audit_rec = create_gui_audit_record(
            session_id=session_id,
            provider=session_provider,
            action_type=request.action,
            guard_result="GUI_GUARD_BLOCKED",
            target_application=session.get("target_app"),
            target_window=session.get("target_window"),
            computed_action_tier=computed_tier,
            declared_action_tier=request.action_tier,
            error_code=stop_result.error_code,
            screenshot_requested=request.uses_screenshot,
            clipboard_requested=request.uses_clipboard,
            keyboard_requested=request.uses_keyboard,
            mouse_requested=request.uses_mouse,
            network_requested=request.network_access,
            input_paths=request.input_paths,
            output_paths=request.output_paths,
            provider_call_allowed=False,
            stop_condition_checked=True,
        )
        detail = stop_result.to_dict()
        detail["audit_id"] = audit_rec.audit_id
        raise HTTPException(status_code=_GUARD_HTTP_STATUS, detail=detail)

    # ── M9-GUI-GUARD-T005: audit pre-create ──
    audit_record = create_gui_audit_record(
        session_id=session_id,
        provider=session_provider,
        action_type=request.action,
        guard_result="GUI_GUARD_OK",
        target_application=session.get("target_app"),
        target_window=session.get("target_window"),
        computed_action_tier=computed_tier,
        declared_action_tier=request.action_tier,
        screenshot_requested=request.uses_screenshot,
        clipboard_requested=request.uses_clipboard,
        keyboard_requested=request.uses_keyboard,
        mouse_requested=request.uses_mouse,
        network_requested=request.network_access,
        input_paths=request.input_paths,
        output_paths=request.output_paths,
        provider_call_allowed=True,
        stop_condition_checked=True,
    )

    # ── M9-GUI-GUARD-T002: runtime-level defense in gui_agent.py
    # handles provider validation at step time via the session's stored provider.
    try:
        result = step_gui_agent_session(session_id, request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        # Runtime guard raises ValueError for blocked providers
        detail = str(exc)
        raise HTTPException(status_code=_GUARD_HTTP_STATUS, detail=detail)
    except Exception as exc:
        raise_api_error(exc)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    # Attach audit record to response
    result["audit"] = audit_record.to_dict()
    return result


@router.get("/api/gui-agent/sessions/{session_id}/screenshot")
def api_gui_agent_screenshot(session_id: str) -> dict[str, Any]:
    # ── M9-GUI-GUARD-T002: runtime-level defense handles provider validation.
    # screenshot route is protected by the runtime guard in gui_agent.py
    # which blocks non-mock providers before capturing.
    try:
        result = capture_gui_agent_screenshot(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=_GUARD_HTTP_STATUS, detail=str(exc))
    except Exception as exc:
        raise_api_error(exc)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/gui-agent/sessions/{session_id}/abort")
def api_gui_agent_abort(session_id: str) -> dict[str, Any]:
    try:
        return abort_gui_agent_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise_api_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Mock Model Adapter Routes — M10-GUI-AGENT-MOCK-T003
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/api/gui-agent/mock-adapter/fixtures")
def api_mock_adapter_fixtures() -> dict[str, Any]:
    """List all mock model output fixtures (safe for UI display).

    Returns fixture metadata only — no raw_text, no chain-of-thought,
    no screenshot bytes, no clipboard contents, no credentials.
    """
    from src.backend.app.runtime.gui_agent_mock_model_fixtures import (
        list_mock_model_fixtures,
    )
    fixtures = list_mock_model_fixtures()
    return {
        "ok": True,
        "fixtures": [
            {
                "fixture_id": f.fixture_id,
                "category": f.category,
                "expected_status": f.expected_status,
                "expected_reason": f.expected_reason,
            }
            for f in fixtures
        ],
    }


@router.post("/api/gui-agent/mock-adapter/step")
def api_mock_adapter_step(request: MockAdapterStepRequest) -> dict[str, Any]:
    """Process a mock model fixture through the adapter and optionally guard.

    - Fetches the fixture by ID.
    - Runs validate_and_normalize_model_output().
    - If rejected: returns MODEL_ACTION_REJECTED; never calls guard/provider.
    - If mapped + dry_run: returns adapter result; never calls guard/provider.
    - If mapped + submit_to_guard: forwards normalized action to the guarded
      step path; guard remains the sole source of authorization.
    """
    from src.backend.app.runtime.gui_agent_mock_model_fixtures import (
        get_mock_model_fixture,
    )
    from src.backend.app.runtime.gui_agent_model_adapter import (
        validate_and_normalize_model_output,
    )
    from src.backend.app.runtime.gui_agent_guard import validate_gui_action_declaration

    # ── 1. Fixture lookup ──
    try:
        fixture = get_mock_model_fixture(request.fixture_id)
    except KeyError:
        return {
            "ok": False,
            "status": "MOCK_MODEL_FIXTURE_NOT_FOUND",
            "fixture_id": request.fixture_id,
            "submitted_to_guard": False,
            "provider_call_allowed": False,
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        }

    # ── 2. Adapter validation ──
    adapter_result = validate_and_normalize_model_output(**fixture.model_output)

    # ── 3. Rejected → return immediately ──
    if not adapter_result.ok:
        return {
            "ok": False,
            "status": "MODEL_ACTION_REJECTED",
            "fixture_id": request.fixture_id,
            "model_output_id": fixture.model_output.get("model_output_id"),
            "adapter_decision": adapter_result.adapter_decision,
            "adapter_rejection_reason": adapter_result.adapter_rejection_reason,
            "submitted_to_guard": False,
            "guard_status": None,
            "audit_id": None,
            "provider_call_allowed": False,
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        }

    # ── 4. Mapped → dry-run or submit ──
    normalized = adapter_result.normalized_action
    normalized_type = normalized["action_type"] if normalized else "unknown"

    if request.dry_run or not request.submit_to_guard:
        return {
            "ok": True,
            "status": "MODEL_ACTION_MAPPED_DRY_RUN",
            "fixture_id": request.fixture_id,
            "model_output_id": fixture.model_output.get("model_output_id"),
            "adapter_decision": adapter_result.adapter_decision,
            "adapter_status": adapter_result.status,
            "normalized_action_type": normalized_type,
            "submitted_to_guard": False,
            "guard_status": None,
            "audit_id": None,
            "provider_call_allowed_by_adapter": False,
            "provider_call_allowed_by_guard": False,
        }

    # ── 5. Submit to guard ──
    if not request.session_id:
        return {
            "ok": False,
            "status": "MOCK_ADAPTER_SESSION_REQUIRED",
            "fixture_id": request.fixture_id,
            "submitted_to_guard": False,
            "provider_call_allowed": False,
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        }

    # Build GuiAgentStepRequest-compatible payload from normalized action
    step_payload = {
        "action": normalized["action_type"],
        "action_tier": normalized["action_tier"],
        "read_only": normalized["read_only"],
        "uses_screenshot": normalized["uses_screenshot"],
        "uses_clipboard": normalized["uses_clipboard"],
        "uses_keyboard": normalized["uses_keyboard"],
        "uses_mouse": normalized["uses_mouse"],
        "network_access": normalized["network_access"],
        "input_paths": normalized["input_paths"],
        "output_paths": normalized["output_paths"],
        "expected_side_effects": normalized["expected_side_effects"],
        "requires_per_action_confirmation": normalized["requires_per_action_confirmation"],
        "rollback_plan": normalized["rollback_plan"],
        "stop_conditions": normalized["stop_conditions"],
    }

    # Submit through the guarded step route
    step_request = GuiAgentStepRequest(**step_payload)
    try:
        guard_response = api_gui_agent_step(request.session_id, step_request)
    except FileNotFoundError:
        return {
            "ok": False,
            "status": "MODEL_ACTION_GUARD_BLOCKED",
            "fixture_id": request.fixture_id,
            "adapter_decision": adapter_result.adapter_decision,
            "adapter_status": adapter_result.status,
            "normalized_action_type": normalized_type,
            "submitted_to_guard": True,
            "guard_status": "SESSION_NOT_FOUND",
            "audit_id": None,
            "provider_call_allowed_by_adapter": False,
            "provider_call_allowed_by_guard": False,
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        }
    except HTTPException as exc:
        return {
            "ok": False,
            "status": "MODEL_ACTION_GUARD_BLOCKED",
            "fixture_id": request.fixture_id,
            "adapter_decision": adapter_result.adapter_decision,
            "adapter_status": adapter_result.status,
            "normalized_action_type": normalized_type,
            "submitted_to_guard": True,
            "guard_status": exc.detail if isinstance(exc.detail, str) else "BLOCKED",
            "audit_id": None,
            "provider_call_allowed_by_adapter": False,
            "provider_call_allowed_by_guard": False,
            "desktop_touched": False,
            "screenshot_captured": False,
            "clipboard_accessed": False,
            "mouse_used": False,
            "keyboard_used": False,
        }

    return {
        "ok": True,
        "status": "MODEL_ACTION_MAPPED",
        "fixture_id": request.fixture_id,
        "model_output_id": fixture.model_output.get("model_output_id"),
        "adapter_decision": adapter_result.adapter_decision,
        "adapter_status": adapter_result.status,
        "normalized_action_type": normalized_type,
        "submitted_to_guard": True,
        "guard_status": "GUI_GUARD_OK",
        "audit_id": guard_response.get("audit", {}).get("audit_id"),
        "provider_call_allowed_by_adapter": False,
        "provider_call_allowed_by_guard": guard_response.get("audit", {}).get(
            "provider_call_allowed", False
        ),
        "desktop_touched": False,
        "screenshot_captured": False,
        "clipboard_accessed": False,
        "mouse_used": False,
        "keyboard_used": False,
    }
