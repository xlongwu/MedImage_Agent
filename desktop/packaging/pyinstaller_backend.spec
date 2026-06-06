# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

repo_root = Path(SPECPATH).resolve().parents[1]
entry = repo_root / "src" / "backend" / "app" / "desktop_backend_entry.py"

# ── Collect OpenSSL DLLs from the current Python environment ─────────────
# Conda environments store OpenSSL DLLs in <prefix>/Library/bin while
# standard Python stores them alongside the _ssl.pyd extension module.
_ssl_binaries = []
_prefix = Path(getattr(sys, "base_prefix", sys.prefix))
_library_bin = _prefix / "Library" / "bin"
if _library_bin.is_dir():
    for _dll_name in ("libssl-3-x64.dll", "libcrypto-3-x64.dll"):
        _dll_path = _library_bin / _dll_name
        if _dll_path.is_file():
            _ssl_binaries.append((str(_dll_path), "."))

a = Analysis(
    [str(entry)],
    pathex=[str(repo_root)],
    binaries=_ssl_binaries,
    datas=[],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "src.backend.app.main",
        "ssl",
        "_ssl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pywinauto",
        "torch",
        "safetensors",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="medimage-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=".",
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
