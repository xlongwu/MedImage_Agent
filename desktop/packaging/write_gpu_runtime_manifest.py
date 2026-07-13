"""Write a portable inventory for a GPU-enabled backend sidecar.

The manifest intentionally records package/runtime compatibility information
and bundled filenames only.  It must never capture local build paths.
"""

from __future__ import annotations

import json
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _cupy_metadata() -> dict[str, object]:
    try:
        import cupy as cp
    except ImportError:
        return {"enabled": False}

    package_name = "cupy-cuda12x"
    try:
        wheel_version: str | None = version(package_name)
    except PackageNotFoundError:
        wheel_version = None
    try:
        runtime_version: int | None = int(cp.cuda.runtime.runtimeGetVersion())
    except Exception:
        runtime_version = None
    try:
        driver_version: int | None = int(cp.cuda.runtime.driverGetVersion())
    except Exception:
        driver_version = None
    return {
        "enabled": True,
        "package": package_name,
        "wheel_version": wheel_version,
        "cupy_version": cp.__version__,
        "cuda_runtime_version": runtime_version,
        "cuda_driver_version_at_build": driver_version,
        "cuda_driver_requirement": "A driver compatible with the bundled CUDA runtime is required.",
    }


def _bundled_gpu_dlls(dist_dir: Path, analysis_toc: Path | None) -> list[str]:
    names = {
        path.name
        for path in dist_dir.rglob("*.dll")
        if any(token in path.name.lower() for token in ("cuda", "cublas", "cufft", "nvrtc", "nvjitlink", "cupy"))
    }
    if analysis_toc is not None and analysis_toc.is_file():
        for name in re.findall(r"\('([^']+\.dll)',", analysis_toc.read_text(encoding="utf-8", errors="ignore")):
            if any(token in name.lower() for token in ("cuda", "cublas", "cufft", "nvrtc", "nvjitlink", "cupy")):
                names.add(Path(name).name)
    return sorted(names)


def write_manifest(dist_dir: Path, analysis_toc: Path | None = None) -> Path:
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"Backend sidecar directory does not exist: {dist_dir}")
    payload = {
        "schema_version": 1,
        "gpu_runtime": _cupy_metadata(),
        "bundled_gpu_dlls": _bundled_gpu_dlls(dist_dir, analysis_toc),
        "cuda_eula_included": bool(
            analysis_toc is not None
            and analysis_toc.is_file()
            and "licenses/cuda/EULA.txt" in analysis_toc.read_text(encoding="utf-8", errors="ignore").replace("\\\\", "/")
        ),
    }
    output = dist_dir / "gpu_runtime_manifest.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) not in (1, 3) or (len(args) == 3 and args[1] != "--analysis-toc"):
        raise ValueError("Usage: write_gpu_runtime_manifest.py <backend-sidecar-directory> [--analysis-toc <path>]")
    analysis_toc = Path(args[2]).resolve() if len(args) == 3 else None
    print(write_manifest(Path(args[0]).resolve(), analysis_toc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
