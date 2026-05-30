from __future__ import annotations

from src.backend.app.runtime.gui_agent import (
    abort_gui_agent_session,
    capture_gui_agent_screenshot,
    create_gui_agent_session,
    step_gui_agent_session,
)


def test_gui_agent_mock_session_records_steps():
    session = create_gui_agent_session({
        "target_app": "spm",
        "objective": "open batch editor",
        "approved": True,
    })

    step = step_gui_agent_session(
        session["session_id"],
        {"action": "record_observation", "parameters": {"window": "SPM"}},
    )
    shot = capture_gui_agent_screenshot(session["session_id"])

    assert session["ok"] is True
    assert step["ok"] is True
    assert step["step"]["executed"] is False
    assert shot["artifact"]["type"] == "screenshot_placeholder"
    assert step["replay_script"].endswith("replay_steps.py")


def test_gui_agent_abort_marks_session():
    session = create_gui_agent_session({"approved": True})
    result = abort_gui_agent_session(session["session_id"])

    assert result["ok"] is True
    assert result["status"] == "ABORTED"


def test_gui_agent_real_provider_requires_approval():
    session = create_gui_agent_session({
        "target_app": "spm",
        "provider": "pywinauto",
        "approved": False,
    })

    result = step_gui_agent_session(session["session_id"], {"action": "locate_window"})

    assert session["status"] == "APPROVAL_REQUIRED"
    assert result["ok"] is False
    assert result["status"] == "APPROVAL_REQUIRED"
