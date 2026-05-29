"""ProjectSettings dataclass and YAML loader.

Design principles:
- Critical fields (work_dir, log_dir, spm_dir, dpabi_dir): raise ValueError if missing.
- Optional fields: safe defaults, never silently fail on missing.
- Error messages are clear and actionable.
- No side effects — loading never writes files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RuntimeSettings:
    """Pipeline runtime configuration."""

    work_dir: str
    log_dir: str
    derivatives_dir: str = "./derivatives"
    report_dir: str = "./reports"
    matlab_command: str = "matlab"


@dataclass
class ThirdPartySettings:
    """Third-party tool paths."""

    spm_dir: str
    dpabi_dir: str


@dataclass
class SafetySettings:
    """Safety boundary configuration."""

    rawdata_readonly: bool = True
    allow_overwrite_derivatives: bool = False
    require_confirmation: bool = True
    # also accepts `require_confirmation_for_matlab_run` from YAML


@dataclass
class ProjectSettings:
    """Top-level project settings loaded from a YAML config file.

    Usage:
        settings = ProjectSettings.from_yaml("examples/project_config.yaml")
        print(settings.runtime.work_dir)
    """

    runtime: RuntimeSettings
    third_party: ThirdPartySettings
    safety: SafetySettings
    source_path: str = ""

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ProjectSettings":
        """Load ProjectSettings from a YAML project config file.

        Args:
            path: Relative or absolute path to the YAML file.

        Returns:
            ProjectSettings instance with validated fields.

        Raises:
            FileNotFoundError: The file does not exist.
            ValueError: Invalid YAML syntax, non-dict content, or missing critical fields.
        """
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "Missing dependency: PyYAML. Install with: pip install pyyaml"
            ) from exc

        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Project config file not found: {path}")

        raw_text = p.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in project config: {path}\n{exc}") from exc

        if not isinstance(data, dict):
            got = type(data).__name__
            raise ValueError(
                f"Project config must be a mapping/dictionary, got {got}: {path}"
            )

        runtime = cls._build_runtime(data.get("runtime", {}) or {}, path)
        third_party = cls._build_third_party(data.get("third_party", {}) or {}, path)
        safety = cls._build_safety(data.get("safety", {}) or {})

        return cls(
            runtime=runtime,
            third_party=third_party,
            safety=safety,
            source_path=str(p),
        )

    # ── private builders ──

    @staticmethod
    def _build_runtime(raw: dict[str, Any], path: str | Path) -> RuntimeSettings:
        work_dir = raw.get("work_dir")
        log_dir = raw.get("log_dir")

        if not work_dir:
            raise ValueError(
                f"Missing required field 'runtime.work_dir' in {path}"
            )
        if not log_dir:
            raise ValueError(
                f"Missing required field 'runtime.log_dir' in {path}"
            )

        return RuntimeSettings(
            work_dir=str(work_dir),
            log_dir=str(log_dir),
            derivatives_dir=str(raw.get("derivatives_dir", "./derivatives")),
            report_dir=str(raw.get("report_dir", "./reports")),
            matlab_command=str(raw.get("matlab_command", "matlab")),
        )

    @staticmethod
    def _build_third_party(
        raw: dict[str, Any], path: str | Path
    ) -> ThirdPartySettings:
        spm_dir = raw.get("spm_dir")
        dpabi_dir = raw.get("dpabi_dir")

        if not spm_dir:
            raise ValueError(
                f"Missing required field 'third_party.spm_dir' in {path}"
            )
        if not dpabi_dir:
            raise ValueError(
                f"Missing required field 'third_party.dpabi_dir' in {path}"
            )

        return ThirdPartySettings(
            spm_dir=str(spm_dir),
            dpabi_dir=str(dpabi_dir),
        )

    @staticmethod
    def _build_safety(raw: dict[str, Any]) -> SafetySettings:
        # Support both `require_confirmation` and `require_confirmation_for_matlab_run`
        require = raw.get("require_confirmation")
        if require is None:
            require = raw.get("require_confirmation_for_matlab_run", True)

        return SafetySettings(
            rawdata_readonly=bool(raw.get("rawdata_readonly", True)),
            allow_overwrite_derivatives=bool(
                raw.get("allow_overwrite_derivatives", False)
            ),
            require_confirmation=bool(require),
        )
