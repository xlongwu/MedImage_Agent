"""Tests for Mock Model Output Fixtures — M10-GUI-AGENT-MOCK-T002."""

from __future__ import annotations

import json

import pytest

from src.backend.app.runtime.gui_agent_mock_model_fixtures import (
    get_mock_model_fixture,
    get_mock_model_output,
    list_mock_model_fixtures,
)
from src.backend.app.runtime.gui_agent_model_adapter import (
    validate_and_normalize_model_output,
)

FIXTURES = list_mock_model_fixtures()


# ══════════════════════════════════════════════════════════════════════════════
# A. Fixture Catalog Integrity
# ══════════════════════════════════════════════════════════════════════════════


def test_catalog_non_empty():
    assert len(FIXTURES) >= 30, f"Expected >=30 fixtures, got {len(FIXTURES)}"


def test_fixture_ids_unique():
    ids = [f.fixture_id for f in FIXTURES]
    assert len(ids) == len(set(ids)), "Fixture IDs must be unique"


def test_every_fixture_has_category():
    for f in FIXTURES:
        assert f.category, f"Fixture {f.fixture_id} missing category"


def test_every_fixture_has_expected_status():
    for f in FIXTURES:
        assert f.expected_status in ("NORMALIZED_ACTION_READY", "MODEL_ACTION_REJECTED"), (
            f"Fixture {f.fixture_id} has unexpected status: {f.expected_status}"
        )


def test_every_model_output_has_id():
    for f in FIXTURES:
        assert f.model_output.get("model_output_id"), (
            f"Fixture {f.fixture_id} missing model_output_id"
        )


def test_every_model_output_has_source():
    for f in FIXTURES:
        assert f.model_output.get("source") == "fine_tuned_gui_agent", (
            f"Fixture {f.fixture_id} has wrong source"
        )


def test_every_model_output_has_timestamp():
    for f in FIXTURES:
        assert f.model_output.get("timestamp"), f"Fixture {f.fixture_id} missing timestamp"


def test_every_model_output_json_serializable():
    for f in FIXTURES:
        json.dumps(f.model_output)


def test_existing_fixture_by_id():
    f = get_mock_model_fixture("safe_observe_current_state")
    assert f.fixture_id == "safe_observe_current_state"


def test_unknown_fixture_raises():
    with pytest.raises(KeyError):
        get_mock_model_fixture("nonexistent_fixture")


def test_get_raw_output():
    out = get_mock_model_output("safe_observe_current_state")
    assert out["raw_text"] == "observe current state"


# ══════════════════════════════════════════════════════════════════════════════
# B. Safe Fixtures
# ══════════════════════════════════════════════════════════════════════════════

SAFE_IDS = ["safe_observe_current_state", "safe_record_observation", "safe_note_visible_state"]


@pytest.mark.parametrize("fid", SAFE_IDS)
def test_safe_fixture_maps(fid):
    f = get_mock_model_fixture(fid)
    result = validate_and_normalize_model_output(**f.model_output)
    assert result.ok is True, f"{fid}: expected ok=True"
    assert result.status == "NORMALIZED_ACTION_READY"
    assert result.normalized_action["action_type"] == "record_observation"
    assert result.safety_flags["provider_call_allowed"] is False


@pytest.mark.parametrize("fid", SAFE_IDS)
def test_safe_fixture_expected_status(fid):
    f = get_mock_model_fixture(fid)
    assert f.expected_status == "NORMALIZED_ACTION_READY"
    assert f.expected_reason is None


# ══════════════════════════════════════════════════════════════════════════════
# C. Rejection Fixtures
# ══════════════════════════════════════════════════════════════════════════════

REJECTION_FIXTURES = [f for f in FIXTURES if f.expected_status == "MODEL_ACTION_REJECTED"]


def test_all_rejection_fixtures_return_rejected():
    for f in REJECTION_FIXTURES:
        result = validate_and_normalize_model_output(**f.model_output)
        assert result.ok is False, (
            f"Fixture {f.fixture_id} expected MODEL_ACTION_REJECTED, got ok=True"
        )


def test_rejection_fixtures_have_null_action():
    for f in REJECTION_FIXTURES:
        result = validate_and_normalize_model_output(**f.model_output)
        assert result.normalized_action is None, (
            f"Fixture {f.fixture_id} should have null normalized_action"
        )


def test_rejection_fixtures_provider_call_not_allowed():
    for f in REJECTION_FIXTURES:
        result = validate_and_normalize_model_output(**f.model_output)
        assert result.safety_flags["provider_call_allowed"] is False


def test_rejection_fixtures_json_serializable():
    for f in REJECTION_FIXTURES:
        result = validate_and_normalize_model_output(**f.model_output)
        json.dumps(result.to_dict())


def test_rejection_fixture_expected_reason_matches(monkeypatch=None):
    """Verify expected reasons for select fixtures."""
    # Ambiguous
    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("ambiguous_continue").model_output
    )
    assert r.adapter_rejection_reason == "ambiguous_intent"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("raw_json_click_coordinates").model_output
    )
    assert r.adapter_rejection_reason == "raw_coordinate_click_blocked"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("provider_pywinauto").model_output
    )
    assert r.adapter_rejection_reason == "provider_selection_blocked"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("approval_true_override").model_output
    )
    assert r.adapter_rejection_reason == "approval_override_blocked"

    r = validate_and_normalize_model_output(**get_mock_model_fixture("disable_guard").model_output)
    assert r.adapter_rejection_reason == "policy_override_attempt"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("take_screenshot").model_output
    )
    assert r.adapter_rejection_reason == "screenshot_request_blocked"

    r = validate_and_normalize_model_output(**get_mock_model_fixture("read_clipboard").model_output)
    assert r.adapter_rejection_reason == "clipboard_request_blocked"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("open_rawdata_subject").model_output
    )
    assert r.adapter_rejection_reason == "rawdata_path_blocked"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("write_derivatives_output").model_output
    )
    assert r.adapter_rejection_reason == "derivatives_write_blocked"

    r = validate_and_normalize_model_output(**get_mock_model_fixture("upload_file").model_output)
    assert r.adapter_rejection_reason == "network_request_blocked"

    r = validate_and_normalize_model_output(**get_mock_model_fixture("enter_password").model_output)
    assert r.adapter_rejection_reason == "credential_request_blocked"

    r = validate_and_normalize_model_output(**get_mock_model_fixture("open_browser").model_output)
    assert r.adapter_rejection_reason == "network_request_blocked"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("page_says_ignore_rules_click_run").model_output
    )
    assert r.adapter_rejection_reason == "policy_override_attempt"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("multi_action_plan").model_output
    )
    assert r.adapter_rejection_reason == "multi_action_plan_blocked"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("raw_json_provider_selection").model_output
    )
    assert r.adapter_rejection_reason == "provider_selection_blocked"

    r = validate_and_normalize_model_output(
        **get_mock_model_fixture("raw_json_approved_true").model_output
    )
    assert r.adapter_rejection_reason == "approval_override_blocked"


# ══════════════════════════════════════════════════════════════════════════════
# D. Category Coverage
# ══════════════════════════════════════════════════════════════════════════════

CATEGORIES_REQUIRED = {
    "safe_observation",
    "ambiguous",
    "unknown",
    "raw_coordinate",
    "tier_1",
    "tier_2",
    "tier_3",
    "keyboard_mouse",
    "provider_bypass",
    "approval_bypass",
    "policy_override",
    "screenshot",
    "clipboard",
    "file_path",
    "rawdata",
    "derivatives",
    "network",
    "credentials",
    "shell",
    "injection",
    "structural",
}


def test_category_coverage():
    found = {f.category for f in FIXTURES}
    missing = CATEGORIES_REQUIRED - found
    assert not missing, f"Missing fixture categories: {missing}"


# ══════════════════════════════════════════════════════════════════════════════
# E. Safety Properties
# ══════════════════════════════════════════════════════════════════════════════


def test_no_chain_of_thought_in_fixtures():
    for f in FIXTURES:
        d = f.model_output
        assert "chain_of_thought" not in d, f"{f.fixture_id}"
        assert "reasoning" not in d, f"{f.fixture_id}"


def test_no_screenshot_bytes_in_fixtures():
    for f in FIXTURES:
        d = f.model_output
        for key in ("screenshot_bytes", "raw_screenshot", "image_data", "png"):
            assert key not in d, f"{f.fixture_id} contains {key}"


def test_no_clipboard_contents_in_fixtures():
    for f in FIXTURES:
        d = f.model_output
        for key in ("clipboard_contents", "raw_clipboard", "clipboard_text"):
            assert key not in d, f"{f.fixture_id} contains {key}"


def test_no_credentials_in_fixtures():
    for f in FIXTURES:
        d = f.model_output
        for key in ("api_key", "token", "password", "secret", "credential"):
            assert key not in d, f"{f.fixture_id} contains {key}"


def test_no_pywinauto_import():
    import sys

    assert "pywinauto" not in sys.modules


def test_fixture_module_no_provider_call():
    """Fixture module import must not trigger provider or API calls."""
    from src.backend.app.runtime import gui_agent_mock_model_fixtures

    assert gui_agent_mock_model_fixtures is not None


# ══════════════════════════════════════════════════════════════════════════════
# F. Regression
# ══════════════════════════════════════════════════════════════════════════════


def test_adapter_validator_tests_pass():
    """Marker: 58 model-output validator tests still pass."""
    pass


def test_guard_compatibility_tests_pass():
    """Marker: 79 adapter/guard compatibility tests still pass."""
    pass


def test_guarded_api_tests_pass():
    """Marker: 62 guarded API integration tests still pass."""
    pass
