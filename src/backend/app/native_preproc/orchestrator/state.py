"""Run context helpers for native preprocessing."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


@dataclass(frozen=True)
class NativePreprocRunContext:
    root_dir: Path
    run_id: str = "native_preproc_run"
    subject_id: str = ""
    session_id: str = ""

    @classmethod
    def from_output_dir(
        cls,
        output_dir: str | Path,
        *,
        run_id: str = "native_preproc_run",
        subject_id: str = "",
        session_id: str = "",
    ) -> "NativePreprocRunContext":
        context = cls(Path(output_dir), run_id=run_id, subject_id=subject_id, session_id=session_id)
        context.ensure_directories()
        return context

    @property
    def artifacts_dir(self) -> Path:
        return self.root_dir / "artifacts"

    @property
    def manifests_dir(self) -> Path:
        return self.root_dir / "manifests"

    @property
    def provenance_dir(self) -> Path:
        return self.root_dir / "provenance"

    @property
    def qc_dir(self) -> Path:
        return self.root_dir / "qc"

    def stage_artifact_dir(self, stage_id: str) -> Path:
        return self.artifacts_dir / stage_id

    def manifest_path(self, stage_id: str) -> Path:
        return self.manifests_dir / f"{stage_id}_manifest.json"

    def provenance_path(self, stage_id: str) -> Path:
        return self.provenance_dir / f"{stage_id}_provenance.json"

    def qc_path(self, stage_id: str) -> Path:
        return self.qc_dir / f"{stage_id}_qc.json"

    def qc_markdown_path(self, stage_id: str) -> Path:
        return self.qc_dir / f"{stage_id}_qc.md"

    def ensure_directories(self) -> None:
        for path in (self.root_dir, self.artifacts_dir, self.manifests_dir, self.provenance_dir, self.qc_dir):
            path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def package_versions(*names: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return versions
