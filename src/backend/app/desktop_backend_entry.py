from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Sequence

import uvicorn


DEFAULT_DESKTOP_HOST = "127.0.0.1"
DEFAULT_DESKTOP_PORT = 8765
APP_IMPORT_STRING = "src.backend.app.main:app"


@dataclass(frozen=True)
class DesktopBackendConfig:
    host: str
    port: int
    log_level: str


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
