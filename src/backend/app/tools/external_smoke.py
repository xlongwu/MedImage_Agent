from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.backend.app.runtime.external_tool_result import (
    ExternalToolRunResult,
    external_tool_failure,
    standard_external_safety,
)
from src.backend.app.tools.dpabi_wrapper import run_dpabi_single_function, run_dpabi_smoke_test
from src.backend.app.tools.spm_runner import run_spm_smoke_test


REPORT_DIR = Path("outputs/reports/external_smoke")
VALID_TARGETS = {"spm", "dpabi", "all"}
VALID_MODES = {"preflight", "manual_package", "approved_smoke"}
VALID_DPABI_FUNCTIONS = {
    "y_Smooth",
    "y_Filter",
    "y_RegressOutImgCovariates",
    "y_alff_falff",
    "y_Reho",
    "y_ROItseries",
    "y_FC",
}


def get_external_smoke_status() -> dict[str, Any]:
    result_path = REPORT_DIR / "external_smoke_result.json"
    if not result_path.exists():
        return {
            "ok": False,
            "result": None,
            "report_text": "",
            "checklist_text": "",
            "commands_text": "",
            "artifacts": {},
            "errors": ["No external smoke package has been generated yet."],
            "next_actions": ["Run manual_package or preflight before reviewing external smoke artifacts."],
        }

    result = _read_json(result_path)
    artifacts = dict(result.get("artifacts", {}) if result else {})
    artifacts.setdefault("result_json", str(result_path))
    return {
        "ok": bool(result and result.get("ok", False)),
        "result": result,
        "report_text": _read_text(REPORT_DIR / "external_smoke_report.md"),
        "checklist_text": _read_text(REPORT_DIR / "checklist.md"),
        "commands_text": _read_text(REPORT_DIR / "commands.md"),
        "artifacts": artifacts,
        "errors": [] if result else [f"Failed to parse external smoke result: {result_path}"],
        "next_actions": (result or {}).get("next_actions", ["Regenerate the external smoke package."]),
    }


def run_external_smoke(
    *,
    target: str = "all",
    mode: str = "manual_package",
    config_path: str = "examples/project_config.yaml",
    approve: bool = False,
    approved_by: str = "local-user",
    dpabi_function: str = "y_Smooth",
) -> dict[str, Any]:
    if target not in VALID_TARGETS:
        return _error_result(target, mode, [f"Invalid target: {target}. Use spm, dpabi, or all."])
    if mode not in VALID_MODES:
        return _error_result(target, mode, [f"Invalid mode: {mode}. Use preflight, manual_package, or approved_smoke."])
    if dpabi_function not in VALID_DPABI_FUNCTIONS:
        return _error_result(target, mode, [f"Invalid DPABI function for smoke: {dpabi_function}."])

    config = _load_config(Path(config_path))
    targets = ["spm", "dpabi"] if target == "all" else [target]
    checks: list[dict[str, Any]] = []
    external_tool_results: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for item in targets:
        if item == "spm":
            spm_checks = _spm_preflight_checks(config)
            checks.extend(spm_checks)
            external_tool_results.append(_preflight_external_result("spm.preflight", "matlab-spm", spm_checks))
        if item == "dpabi":
            dpabi_checks = _dpabi_preflight_checks(config)
            checks.extend(dpabi_checks)
            external_tool_results.append(_preflight_external_result("dpabi.preflight", "matlab-dpabi", dpabi_checks))

    if mode == "approved_smoke":
        if not approve:
            errors.append("approved_smoke requires --approve. No MATLAB process was launched.")
        else:
            for item in targets:
                if item == "spm":
                    result = _run_spm_smoke_if_safe(config, approve=approve)
                    external_tool_results.append(result.get("external_tool_result", result))
                    errors.extend(result.get("errors", []))
                    warnings.extend(result.get("warnings", []))
                if item == "dpabi":
                    for result in _run_dpabi_smoke_if_safe(config, approve=approve, approved_by=approved_by, dpabi_function=dpabi_function):
                        external_tool_results.append(result.get("external_tool_result", result))
                        errors.extend(result.get("errors", []))
                        warnings.extend(result.get("warnings", []))

    artifacts = _write_manual_package(
        target=target,
        mode=mode,
        config=config,
        config_path=config_path,
        approve=approve,
        approved_by=approved_by,
        dpabi_function=dpabi_function,
        checks=checks,
        external_tool_results=external_tool_results,
        errors=errors,
        warnings=warnings,
    )

    next_actions = _next_actions(mode=mode, checks=checks, errors=errors, target=target)
    result = {
        "ok": not errors and all(item.get("ok", False) for item in checks if item.get("required", False)),
        "target": target,
        "mode": mode,
        "checks": checks,
        "external_tool_results": external_tool_results,
        "artifacts": artifacts,
        "warnings": warnings,
        "errors": errors,
        "next_actions": next_actions,
    }
    result_path = REPORT_DIR / "external_smoke_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["artifacts"]["result_json"] = str(result_path)
    return result


def _load_config(config_path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _runtime(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("runtime", {})


def _third_party(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("third_party", {})


def _data(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("data", {})


def _path_check(name: str, path: str, *, required: bool = True) -> dict[str, Any]:
    p = Path(path)
    return {
        "name": name,
        "ok": p.exists(),
        "path": str(p),
        "resolved": str(p.resolve()) if p.exists() else "",
        "required": required,
    }


def _command_check(name: str, command: str, *, required: bool = True) -> dict[str, Any]:
    resolved = shutil.which(command)
    path_exists = Path(command).exists()
    return {
        "name": name,
        "ok": bool(resolved or path_exists),
        "command": command,
        "resolved": resolved or (str(Path(command).resolve()) if path_exists else ""),
        "required": required,
    }


def _spm_preflight_checks(config: dict[str, Any]) -> list[dict[str, Any]]:
    runtime = _runtime(config)
    third_party = _third_party(config)
    return [
        _command_check("matlab_command", runtime.get("matlab_command", "matlab")),
        _path_check("spm_dir", third_party.get("spm_dir", "./third_party/spm12")),
        {
            "name": "spm_smoke_scope",
            "ok": True,
            "required": False,
            "detail": "Approved smoke will run SPM environment script only; no rawdata writes.",
        },
    ]


def _dpabi_preflight_checks(config: dict[str, Any]) -> list[dict[str, Any]]:
    runtime = _runtime(config)
    third_party = _third_party(config)
    data = _data(config)
    return [
        _command_check("matlab_command", runtime.get("matlab_command", "matlab")),
        _path_check("dpabi_dir", third_party.get("dpabi_dir", "./third_party/DPABI_V8.2_240510")),
        _path_check("synthetic_bold", _default_input_bold(config), required=False),
        {
            "name": "dpabi_safety_policy",
            "ok": True,
            "required": True,
            "rawdata_dir": data.get("rawdata_dir", "./examples/synthetic_bids/rawdata"),
            "forbidden": ["DPARSF_run", "DPARSFA_run", "DPABI GUI batch execution"],
        },
    ]


def _preflight_external_result(tool_name: str, backend: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [f"{item['name']} not available: {item.get('path') or item.get('command')}" for item in checks if item.get("required", False) and not item.get("ok", False)]
    return ExternalToolRunResult(
        tool_name=tool_name,
        backend=backend,
        approval={"approved": False, "required_for_execution": True},
        safety=standard_external_safety(),
        warnings=["Preflight/manual package mode does not launch MATLAB."],
        errors=errors,
    ).finish(returncode=None).to_dict()


def _run_spm_smoke_if_safe(config: dict[str, Any], *, approve: bool) -> dict[str, Any]:
    checks = _spm_preflight_checks(config)
    blocking = [item for item in checks if item.get("required", False) and not item.get("ok", False)]
    runtime = _runtime(config)
    third_party = _third_party(config)
    if blocking:
        return {
            "ok": False,
            "external_tool_result": external_tool_failure(
                tool_name="spm.smoke_test",
                backend="matlab-spm",
                errors=[f"SPM smoke blocked by failed preflight: {item['name']}" for item in blocking],
                approval={"approved": approve, "required": True},
                safety=standard_external_safety(),
            ),
            "errors": [f"SPM smoke blocked by failed preflight: {item['name']}" for item in blocking],
            "warnings": [],
        }
    return run_spm_smoke_test(
        matlab_command=runtime.get("matlab_command", "matlab"),
        spm_dir=third_party.get("spm_dir", "./third_party/spm12"),
        work_dir=runtime.get("work_dir", "./work"),
        log_dir=runtime.get("log_dir", "./logs"),
        matlab_script_dir="./matlab",
    )


def _run_dpabi_smoke_if_safe(
    config: dict[str, Any],
    *,
    approve: bool,
    approved_by: str,
    dpabi_function: str,
) -> list[dict[str, Any]]:
    checks = _dpabi_preflight_checks(config)
    blocking = [item for item in checks if item.get("required", False) and not item.get("ok", False)]
    runtime = _runtime(config)
    third_party = _third_party(config)
    if blocking:
        errors = [f"DPABI smoke blocked by failed preflight: {item['name']}" for item in blocking]
        return [{
            "ok": False,
            "external_tool_result": external_tool_failure(
                tool_name="dpabi.smoke_test",
                backend="matlab-dpabi",
                errors=errors,
                approval={"approved": approve, "approved_by": approved_by, "required": True},
                safety=standard_external_safety(),
            ),
            "errors": errors,
            "warnings": [],
        }]

    env_smoke = run_dpabi_smoke_test(
        dpabi_dir=third_party.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
        matlab_command=runtime.get("matlab_command", "matlab"),
        work_dir=runtime.get("work_dir", "./work"),
        log_dir=runtime.get("log_dir", "./logs"),
        approved=approve,
    )
    single_function = run_dpabi_single_function(
        function_name=dpabi_function,
        input_bold=_default_input_bold(config),
        subject_id="sub-001",
        derivatives_dir=runtime.get("derivatives_dir", "./derivatives"),
        work_dir=runtime.get("work_dir", "./work"),
        log_dir=runtime.get("log_dir", "./logs"),
        dpabi_dir=third_party.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
        matlab_command=runtime.get("matlab_command", "matlab"),
        mode="synthetic_execute",
        approved=approve,
        params={},
    )
    return [env_smoke, single_function]


def _default_input_bold(config: dict[str, Any]) -> str:
    rawdata = _data(config).get("rawdata_dir", "./examples/synthetic_bids/rawdata")
    return str(Path(rawdata) / "sub-001" / "func" / "sub-001_task-rest_bold.nii")


def _write_manual_package(
    *,
    target: str,
    mode: str,
    config: dict[str, Any],
    config_path: str,
    approve: bool,
    approved_by: str,
    dpabi_function: str,
    checks: list[dict[str, Any]],
    external_tool_results: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> dict[str, str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    runtime = _runtime(config)
    third_party = _third_party(config)

    approval_template = {
        "approved": False,
        "approved_by": "",
        "approved_at": "",
        "target": target,
        "allowed_mode": "approved_smoke",
        "rawdata_readonly": True,
        "forbidden": ["DPARSF_run", "DPARSFA_run", "DPABI GUI batch execution"],
    }
    approval_path = REPORT_DIR / "approval_template.json"
    approval_path.write_text(json.dumps(approval_template, ensure_ascii=False, indent=2), encoding="utf-8")

    spm_script = REPORT_DIR / "spm_env_smoke.m"
    spm_script.write_text(
        "\n".join([
            "% SPM environment smoke script snapshot.",
            f"addpath('{third_party.get('spm_dir', './third_party/spm12')}');",
            "spm('defaults', 'fmri');",
            "spm_jobman('initcfg');",
            "disp(['SPM version: ' spm('version')]);",
            "",
        ]),
        encoding="utf-8",
    )

    dpabi_script = REPORT_DIR / f"dpabi_{dpabi_function}_smoke.m"
    dpabi_script.write_text(
        "\n".join([
            "% DPABI environment and single-function smoke script snapshot.",
            f"addpath(genpath('{third_party.get('dpabi_dir', './third_party/DPABI_V8.2_240510')}'));",
            f"disp(['{dpabi_function} path: ' which('{dpabi_function}')]);",
            "% Execute only through run_external_smoke_cli --mode approved_smoke --approve.",
            "",
        ]),
        encoding="utf-8",
    )

    commands_path = REPORT_DIR / "commands.md"
    commands_path.write_text(
        "\n".join([
            "# External Smoke Commands",
            "",
            "```bash",
            f"python -m src.backend.app.tools.run_external_smoke_cli --target {target} --mode preflight --config {config_path}",
            f"python -m src.backend.app.tools.run_external_smoke_cli --target {target} --mode manual_package --config {config_path}",
            f"python -m src.backend.app.tools.run_external_smoke_cli --target {target} --mode approved_smoke --config {config_path} --approve --approved-by {approved_by} --dpabi-function {dpabi_function}",
            "```",
            "",
        ]),
        encoding="utf-8",
    )

    checklist_path = REPORT_DIR / "checklist.md"
    checklist_path.write_text(_render_checklist(checks), encoding="utf-8")
    report_path = REPORT_DIR / "external_smoke_report.md"
    report_path.write_text(
        _render_report(
            target=target,
            mode=mode,
            approve=approve,
            checks=checks,
            external_tool_results=external_tool_results,
            warnings=warnings,
            errors=errors,
            matlab_command=runtime.get("matlab_command", "matlab"),
        ),
        encoding="utf-8",
    )

    return {
        "report_dir": str(REPORT_DIR),
        "checklist": str(checklist_path),
        "commands": str(commands_path),
        "approval_template": str(approval_path),
        "spm_script_snapshot": str(spm_script),
        "dpabi_script_snapshot": str(dpabi_script),
        "report_md": str(report_path),
    }


def _render_checklist(checks: list[dict[str, Any]]) -> str:
    lines = ["# External Smoke Checklist", ""]
    for item in checks:
        mark = "x" if item.get("ok") else " "
        detail = item.get("path") or item.get("command") or item.get("detail") or ""
        lines.append(f"- [{mark}] {item['name']}: {detail}")
    lines += [
        "",
        "## Safety",
        "",
        "- Rawdata remains read-only.",
        "- DPARSF_run, DPARSFA_run, and DPABI GUI batch execution remain forbidden.",
        "- approved_smoke requires explicit --approve.",
        "",
    ]
    return "\n".join(lines)


def _render_report(
    *,
    target: str,
    mode: str,
    approve: bool,
    checks: list[dict[str, Any]],
    external_tool_results: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
    matlab_command: str,
) -> str:
    lines = [
        "# External Smoke Diagnostic Report",
        "",
        f"- Target: {target}",
        f"- Mode: {mode}",
        f"- Approved: {approve}",
        f"- MATLAB command: `{matlab_command}`",
        "",
        "## Checks",
        "",
    ]
    for item in checks:
        status = "PASS" if item.get("ok") else "FAIL"
        detail = item.get("path") or item.get("command") or item.get("detail") or ""
        lines.append(f"- {status}: {item['name']} {detail}")
    lines += ["", "## External Tool Results", ""]
    for item in external_tool_results:
        lines.append(f"- {item.get('tool_name')}: ok={item.get('ok')} returncode={item.get('returncode')}")
        logs = item.get("logs") or {}
        if logs:
            lines.append(f"  Logs: {json.dumps(logs, ensure_ascii=False)}")
    lines += ["", "## Errors", ""]
    lines.extend([f"- {item}" for item in errors] or ["- None"])
    lines += ["", "## Warnings", ""]
    lines.extend([f"- {item}" for item in warnings] or ["- None"])
    lines += ["", "## Diagnosis", ""]
    lines.extend([f"- {item}" for item in _next_actions(mode=mode, checks=checks, errors=errors, target=target)])
    lines.append("")
    return "\n".join(lines)


def _next_actions(*, mode: str, checks: list[dict[str, Any]], errors: list[str], target: str) -> list[str]:
    actions: list[str] = []
    failed = [item for item in checks if item.get("required", False) and not item.get("ok", False)]
    for item in failed:
        if item["name"] == "matlab_command":
            actions.append("Configure runtime.matlab_command or ensure MATLAB is on PATH.")
        elif item["name"] == "spm_dir":
            actions.append("Install/configure SPM12 and update third_party.spm_dir.")
        elif item["name"] == "dpabi_dir":
            actions.append("Install/configure DPABI and update third_party.dpabi_dir.")
    if mode != "approved_smoke" and not failed:
        actions.append("Review the generated manual package, then run approved_smoke with --approve in a hardware MATLAB environment.")
    if errors:
        actions.append("Open the stdout/stderr logs listed in external_tool_results before retrying.")
    if target in {"dpabi", "all"}:
        actions.append("Keep DPABI validation limited to allowlisted single functions; do not use DPARSF_run or DPARSFA_run.")
    return actions or ["No action required."]


def _error_result(target: str, mode: str, errors: list[str]) -> dict[str, Any]:
    return {
        "ok": False,
        "target": target,
        "mode": mode,
        "checks": [],
        "external_tool_results": [],
        "artifacts": {},
        "warnings": [],
        "errors": errors,
        "next_actions": ["Fix CLI arguments and rerun."],
    }
