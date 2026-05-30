"""MATLAB command and third-party path safety guard.

Pure functions — no MATLAB/SPM/DPABI calls, no file writes, no side effects.

Designed to be called BEFORE any MATLAB/SPM/DPABI runner, as an additional
layer of defence-in-depth beyond the M5 12-gate execution checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FORBIDDEN_COMMAND_CHARS = frozenset(";&|`$><\n\r")
FORBIDDEN_BASENAMES = frozenset(["matlab", "matlab.exe"])

FORBIDDEN_DIR_NAMES = frozenset([
    "data", "rawdata", "derivatives", "reports", "work",
])


@dataclass(frozen=True)
class MatlabSafetyIssue:
    code: str
    message: str
    severity: str = "error"
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
        }


@dataclass(frozen=True)
class MatlabSafetyResult:
    ok: bool
    errors: list[MatlabSafetyIssue] = field(default_factory=list)
    warnings: list[MatlabSafetyIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


# ── MATLAB command validation ────────────────────────────────────────────────

def validate_matlab_command(command: str) -> MatlabSafetyResult:
    """Validate a `matlab_command` string for safety.

    Only accepts `matlab`, `matlab.exe`, or an absolute path whose basename
    is `matlab` / `matlab.exe`.  Refuses arguments, shell metacharacters,
    path traversal, and dangerous locations.
    """
    errors: list[MatlabSafetyIssue] = []
    warnings: list[MatlabSafetyIssue] = []

    # ── Forbidden characters (check BEFORE strip, to catch \n, \r, etc.) ──
    for ch in command:
        if ch in FORBIDDEN_COMMAND_CHARS:
            errors.append(MatlabSafetyIssue(
                code="MATLAB_COMMAND_FORBIDDEN_CHAR",
                message=f"matlab_command contains forbidden character: {repr(ch)}",
                field="matlab_command",
            ))
            break

    if not command or not command.strip():
        errors.append(MatlabSafetyIssue(
            code="MATLAB_COMMAND_EMPTY",
            message="matlab_command must not be empty.",
            field="matlab_command",
        ))
        # Still return — further checks are irrelevant for empty input
        return MatlabSafetyResult(ok=False, errors=errors, warnings=warnings)

    stripped = command.strip()

    # ── No arguments / no compound commands ──
    # If it looks like a bare name (no slash, no backslash), it must be exactly "matlab" or "matlab.exe"
    if "/" not in stripped and "\\" not in stripped:
        if stripped not in FORBIDDEN_BASENAMES:
            errors.append(MatlabSafetyIssue(
                code="MATLAB_COMMAND_INVALID_BASENAME",
                message=f"matlab_command basename must be 'matlab' or 'matlab.exe', got: {stripped}",
                field="matlab_command",
            ))
        # Also check for arguments: if there's a space, it could be "matlab -r evil"
        if " " in stripped:
            errors.append(MatlabSafetyIssue(
                code="MATLAB_COMMAND_HAS_ARGUMENTS",
                message="matlab_command must not contain arguments or spaces.",
                field="matlab_command",
            ))
    else:
        # It's a path — validate it
        path = Path(stripped)

        # Path traversal
        if ".." in str(path):
            errors.append(MatlabSafetyIssue(
                code="MATLAB_COMMAND_PATH_TRAVERSAL",
                message="matlab_command path must not contain '..'",
                field="matlab_command",
            ))

        # Basename check
        basename = path.name.lower()
        if basename not in FORBIDDEN_BASENAMES:
            errors.append(MatlabSafetyIssue(
                code="MATLAB_COMMAND_INVALID_BASENAME",
                message=f"matlab_command basename must be 'matlab' or 'matlab.exe', got: {basename}",
                field="matlab_command",
            ))

        # Arguments check (path with spaces)
        if " " in stripped:
            errors.append(MatlabSafetyIssue(
                code="MATLAB_COMMAND_HAS_ARGUMENTS",
                message="matlab_command must not contain arguments or spaces.",
                field="matlab_command",
            ))

        # Forbidden location check
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        for forbidden in FORBIDDEN_DIR_NAMES:
            if forbidden in resolved.parts:
                errors.append(MatlabSafetyIssue(
                    code="MATLAB_COMMAND_FORBIDDEN_LOCATION",
                    message=f"matlab_command must not be inside '{forbidden}/' directory.",
                    field="matlab_command",
                ))
                break

    # If the path doesn't exist and it's an absolute path, warn
    if "/" in stripped or "\\" in stripped:
        try:
            if not Path(stripped).exists():
                warnings.append(MatlabSafetyIssue(
                    code="MATLAB_COMMAND_NOT_FOUND",
                    message=f"matlab_command path does not exist: {stripped}",
                    severity="warning",
                    field="matlab_command",
                ))
        except Exception:
            pass

    return MatlabSafetyResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ── Third-party path validation ──────────────────────────────────────────────

def validate_third_party_dir(path: str | Path, *, name: str) -> MatlabSafetyResult:
    """Validate a third-party directory path (spm_dir / dpabi_dir).

    Refuses empty paths, path traversal, forbidden locations, and files.
    Warns if the directory does not exist (may be expected in CI/dev).
    """
    errors: list[MatlabSafetyIssue] = []
    warnings: list[MatlabSafetyIssue] = []

    path_str = str(path).strip() if isinstance(path, str) else str(path)
    if not path_str:
        errors.append(MatlabSafetyIssue(
            code="THIRD_PARTY_DIR_EMPTY",
            message=f"{name} must not be empty.",
            field=name,
        ))
        return MatlabSafetyResult(ok=False, errors=errors, warnings=warnings)

    p = Path(path_str)

    # Path traversal
    if ".." in str(p):
        errors.append(MatlabSafetyIssue(
            code="THIRD_PARTY_DIR_PATH_TRAVERSAL",
            message=f"{name} path must not contain '..'",
            field=name,
        ))

    # Forbidden location
    try:
        resolved = p.resolve()
    except Exception:
        resolved = p
    for forbidden in FORBIDDEN_DIR_NAMES:
        if forbidden in resolved.parts:
            errors.append(MatlabSafetyIssue(
                code="THIRD_PARTY_DIR_FORBIDDEN_LOCATION",
                message=f"{name} must not point inside '{forbidden}/' directory.",
                field=name,
            ))
            break

    # Is it a file?
    if p.exists() and p.is_file():
        errors.append(MatlabSafetyIssue(
            code="THIRD_PARTY_DIR_IS_FILE",
            message=f"{name} points to a file, not a directory.",
            field=name,
        ))

    # Does not exist → warning (not error — CI/dev may not have SPM/DPABI)
    if not p.exists():
        warnings.append(MatlabSafetyIssue(
            code="THIRD_PARTY_DIR_NOT_FOUND",
            message=f"{name} directory does not exist: {p}",
            severity="warning",
            field=name,
        ))

    # Resolved path escape
    try:
        if p.resolve() != p:
            # Path was resolved through symlinks — not inherently dangerous,
            # but worth noting
            pass
    except Exception:
        pass

    return MatlabSafetyResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ── Combined runtime config validation ──────────────────────────────────────

def validate_matlab_runtime_config(
    *,
    matlab_command: str,
    spm_dir: str | Path,
    dpabi_dir: str | Path,
) -> MatlabSafetyResult:
    """Validate the full MATLAB runtime configuration.

    Combines validate_matlab_command + validate_third_party_dir for
    spm_dir and dpabi_dir into a single result.
    """
    cmd_result = validate_matlab_command(matlab_command)
    spm_result = validate_third_party_dir(spm_dir, name="spm_dir")
    dpabi_result = validate_third_party_dir(dpabi_dir, name="dpabi_dir")

    all_errors = cmd_result.errors + spm_result.errors + dpabi_result.errors
    all_warnings = cmd_result.warnings + spm_result.warnings + dpabi_result.warnings

    return MatlabSafetyResult(
        ok=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
    )


# ── SPM-only runtime config validation ──────────────────────────────────────

def validate_spm_runtime_config(
    *,
    matlab_command: str,
    spm_dir: str | Path,
) -> MatlabSafetyResult:
    """Validate MATLAB + SPM runtime config for SPM-only nodes.

    Does NOT validate dpabi_dir.  Use validate_matlab_runtime_config()
    for nodes that also require DPABI.
    """
    cmd_result = validate_matlab_command(matlab_command)
    spm_result = validate_third_party_dir(spm_dir, name="spm_dir")

    all_errors = cmd_result.errors + spm_result.errors
    all_warnings = cmd_result.warnings + spm_result.warnings

    return MatlabSafetyResult(
        ok=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
    )
