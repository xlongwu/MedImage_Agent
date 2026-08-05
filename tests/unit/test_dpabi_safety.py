from src.backend.app.tools.dpabi_safety import (
    ALLOWED_FUNCTIONS,
    check_dpabi_call,
    list_allowed_functions,
)


def test_dparsf_run_blocked():
    allowed, reason = check_dpabi_call("DPARSF_run")
    assert allowed is False
    assert "blocked" in reason


def test_dparsfa_run_blocked():
    allowed, reason = check_dpabi_call("DPARSFA_run")
    assert allowed is False


def test_dpabi_run_blocked():
    allowed, reason = check_dpabi_call("DPABI_run")
    assert allowed is False


def test_dparsf_pattern_blocked():
    allowed, reason = check_dpabi_call("my_DPARSF_helper")
    assert allowed is False


def test_allowed_functions_pass():
    for func_name in ALLOWED_FUNCTIONS:
        allowed, reason = check_dpabi_call(func_name)
        assert allowed is True, f"{func_name} should be allowed, got: {reason}"


def test_unknown_function_allowed():
    allowed, reason = check_dpabi_call("some_custom_function")
    assert allowed is True
    assert reason is None


def test_list_allowed():
    funcs = list_allowed_functions()
    assert "y_Smooth" in funcs
    assert "y_Filter" in funcs
    assert len(funcs) >= 7
