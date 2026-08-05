from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ExternalToolRunResult:
    tool_name: str
    backend: str
    command: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    logs: dict[str, str] = field(default_factory=dict)
    returncode: int | None = None
    duration_seconds: float | None = None
    approval: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=utc_now_iso)
    ended_at: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.returncode in {0, None} and not self.errors

    def finish(
        self,
        returncode: int | None = None,
        duration_seconds: float | None = None,
        errors: list[str] | None = None,
    ) -> ExternalToolRunResult:
        if returncode is not None:
            self.returncode = returncode
        if duration_seconds is not None:
            self.duration_seconds = duration_seconds
        if errors:
            self.errors.extend(errors)
        self.ended_at = utc_now_iso()
        return self

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        return data

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target


def from_subprocess_result(
    *,
    tool_name: str,
    backend: str,
    command: list[str],
    returncode: int,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    logs: dict[str, str] | None = None,
    duration_seconds: float | None = None,
    approval: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    result = ExternalToolRunResult(
        tool_name=tool_name,
        backend=backend,
        command=command,
        inputs=inputs or [],
        outputs=outputs or [],
        logs=logs or {},
        returncode=returncode,
        duration_seconds=duration_seconds,
        approval=approval or {},
        safety=safety or {},
        warnings=warnings or [],
        errors=errors or [],
    ).finish(returncode=returncode, duration_seconds=duration_seconds)
    return result.to_dict()


def external_tool_failure(
    *,
    tool_name: str,
    backend: str,
    errors: list[str],
    command: list[str] | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    logs: dict[str, str] | None = None,
    approval: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return ExternalToolRunResult(
        tool_name=tool_name,
        backend=backend,
        command=command or [],
        inputs=inputs or [],
        outputs=outputs or [],
        logs=logs or {},
        approval=approval or {},
        safety=safety or {},
        warnings=warnings or [],
        errors=errors,
    ).finish(returncode=None).to_dict()


def standard_external_safety(**extra: Any) -> dict[str, Any]:
    safety = {
        "rawdata_readonly": True,
        "rawdata_modified": False,
        "files_deleted": False,
        "dpabi_gui_called": False,
        "dparsf_run_called": False,
        "dparsfa_run_called": False,
    }
    safety.update(extra)
    return safety


def missing_output_errors(outputs: list[str]) -> list[str]:
    errors: list[str] = []
    for item in outputs:
        if item and not Path(item).exists():
            errors.append(f"Expected output not found: {item}")
    return errors
