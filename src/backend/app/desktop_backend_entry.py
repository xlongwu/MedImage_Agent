from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import uvicorn

DEFAULT_DESKTOP_HOST = "127.0.0.1"
DEFAULT_DESKTOP_PORT = 8765
APP_IMPORT_STRING = "src.backend.app.main:app"


@dataclass(frozen=True)
class DesktopBackendConfig:
    host: str
    port: int
    log_level: str


def ensure_packaged_windows_runtime_dirs() -> tuple[Path, ...]:
    """Create frozen-runtime probe directories inside the desktop workspace.

    CuPy's Windows loader probes ``sys.prefix/bin`` during its lazy import.
    For a PyInstaller one-file sidecar, ``sys.prefix`` is the launch working
    directory and the directory is absent in a fresh desktop workspace.  The
    probe raises ``WinError 2`` before CuPy can load bundled DLLs unless the
    empty directory exists.

    The helper is a no-op outside a frozen Windows process and refuses to
    create anything outside the explicitly selected desktop workspace.
    """
    if os.name != "nt" or not bool(getattr(sys, "frozen", False)):
        return ()
    workspace = Path(
        os.environ.get("MEDIMAGE_DESKTOP_WORKSPACE") or Path.cwd()
    ).expanduser().resolve()
    prefix_bin = (Path(sys.prefix).expanduser().resolve() / "bin").resolve()
    try:
        prefix_bin.relative_to(workspace)
    except ValueError as exc:
        raise RuntimeError(
            f"Frozen runtime bin directory escapes desktop workspace: {prefix_bin}"
        ) from exc
    prefix_bin.mkdir(parents=True, exist_ok=True)
    return (prefix_bin,)


def validate_host(host: str) -> str:
    normalized = host.strip()
    if normalized != DEFAULT_DESKTOP_HOST:
        raise ValueError("Desktop backend host must be 127.0.0.1.")
    return normalized


def _env_port() -> int:
    raw = (
        os.environ.get("MEDIMAGE_DESKTOP_BACKEND_PORT")
        or os.environ.get("MEDIMAGE_BACKEND_PORT")
        or str(DEFAULT_DESKTOP_PORT)
    )
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid desktop backend port: {raw}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"Desktop backend port out of range: {port}")
    return port


def parse_args(argv: Sequence[str] | None = None) -> DesktopBackendConfig:
    parser = argparse.ArgumentParser(description="Start the MedImage Agent desktop backend.")
    parser.add_argument(
        "--host",
        default=os.environ.get("MEDIMAGE_DESKTOP_BACKEND_HOST", DEFAULT_DESKTOP_HOST),
        help="Backend bind host. Desktop mode only permits 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_env_port(),
        help="Backend bind port. Defaults to MEDIMAGE_DESKTOP_BACKEND_PORT or 8765.",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("MEDIMAGE_DESKTOP_BACKEND_LOG_LEVEL", "info"),
        choices=("critical", "error", "warning", "info", "debug", "trace"),
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        raise ValueError(f"Desktop backend port out of range: {args.port}")
    return DesktopBackendConfig(
        host=validate_host(args.host),
        port=args.port,
        log_level=args.log_level,
    )


def run_backend(config: DesktopBackendConfig) -> None:
    ensure_packaged_windows_runtime_dirs()
    os.environ.setdefault("MEDIMAGE_DESKTOP", "1")
    os.environ["MEDIMAGE_DESKTOP_BACKEND_HOST"] = config.host
    os.environ["MEDIMAGE_DESKTOP_BACKEND_PORT"] = str(config.port)
    uvicorn.run(
        APP_IMPORT_STRING,
        host=config.host,
        port=config.port,
        reload=False,
        factory=False,
        log_level=config.log_level,
    )


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_args(argv)
    run_backend(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
