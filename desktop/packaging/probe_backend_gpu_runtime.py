"""Launch the frozen backend and verify packaged scientific capabilities."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get_json(url: str, *, timeout: float) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {body}") from exc


def _stop_backend_process_tree(proc: subprocess.Popen[bytes]) -> None:
    """Stop the PyInstaller bootloader and its extracted backend child."""
    if os.name == "nt" and proc.poll() is None:
        subprocess.run(
            ["taskkill", "/pid", str(proc.pid), "/t", "/f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=30)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend_exe", type=Path)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("result_path", type=Path)
    parser.add_argument("--expect-cupy", action="store_true")
    args = parser.parse_args()

    backend = args.backend_exe.resolve()
    workspace = args.workspace.resolve()
    result_path = args.result_path.resolve()
    if not backend.is_file():
        raise FileNotFoundError(backend)
    workspace.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "MEDIMAGE_DESKTOP": "1",
            "MEDIMAGE_DESKTOP_WORKSPACE": str(workspace),
            "CUPY_CACHE_DIR": str(workspace / "cupy-cache"),
        }
    )
    stdout_path = workspace / "backend.stdout.log"
    stderr_path = workspace / "backend.stderr.log"
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(
            [str(backend), "--host", "127.0.0.1", "--port", str(port)],
            cwd=workspace,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        base = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"Frozen backend exited before health check: {proc.returncode}"
                    )
                try:
                    _get_json(f"{base}/api/health", timeout=2)
                    break
                except (OSError, urllib.error.URLError, TimeoutError):
                    time.sleep(1)
            else:
                raise TimeoutError(
                    "Frozen backend did not become healthy within 180 seconds"
                )

            gpu = _get_json(f"{base}/api/gpu/detect", timeout=120)
            dicom = _get_json(
                f"{base}/api/desktop/capabilities/dicom-conversion",
                timeout=30,
            )
            dicom_capability = dict(dicom.get("capability") or {})
            evidence = {
                "ok": True,
                "backend_exe": backend.name,
                "expect_cupy": bool(args.expect_cupy),
                "cupy_available": bool(gpu.get("cupy_available")),
                "gpu_available": bool(gpu.get("gpu_available")),
                "capability_error_code": gpu.get("capability_error_code"),
                "warnings": list(gpu.get("warnings") or []),
                "dicom_converter_available": bool(
                    dicom_capability.get("converter_available")
                ),
                "dicom_execution_supported": bool(
                    dicom_capability.get("execution_supported")
                ),
                "dicom_converter_name": dicom_capability.get("converter_name"),
                "dicom_converter_version": dicom_capability.get("converter_version"),
                "dicom_error": dicom_capability.get("error"),
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
            }
            if not (
                evidence["dicom_converter_available"]
                and evidence["dicom_execution_supported"]
            ):
                evidence["ok"] = False
                result_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
                raise RuntimeError(
                    "Frozen backend DICOM converter is unavailable: "
                    + str(evidence["dicom_error"])
                )
            if args.expect_cupy and not evidence["cupy_available"]:
                evidence["ok"] = False
                result_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
                raise RuntimeError(
                    "Frozen backend could not import CuPy: "
                    + " | ".join(evidence["warnings"])
                )
            result_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(json.dumps(evidence, indent=2))
        finally:
            _stop_backend_process_tree(proc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
