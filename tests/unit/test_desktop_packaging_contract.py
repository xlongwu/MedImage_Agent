from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_desktop_packaging_files_exist():
    required = [
        "desktop/electron/package.json",
        "desktop/electron/main.cjs",
        "desktop/electron/preload.cjs",
        "desktop/electron/build-dist.cjs",
        "desktop/electron/electron-builder.yml",
        "desktop/electron/smoke-check.cjs",
        "desktop/packaging/pyinstaller_backend.spec",
        "desktop/packaging/pyinstaller_desktop_launcher.spec",
        "desktop/packaging/build_backend.ps1",
        "desktop/packaging/build_launcher.ps1",
        "desktop/packaging/build_frontend.ps1",
        "desktop/packaging/build_desktop.ps1",
        "desktop/packaging/build_all_windows.ps1",
        "src/backend/app/desktop_backend_entry.py",
        "src/backend/app/desktop_launcher_entry.py",
        "docs/DESKTOP_APP_PACKAGING.md",
    ]

    for relative in required:
        assert (ROOT / relative).exists(), relative


def test_electron_main_contract():
    main = read("desktop/electron/main.cjs")

    assert "medimage-backend.exe" in main
    assert "findAvailablePort" in main
    assert 'HEALTH_PATH = "/api/health"' in main
    assert "MEDIMAGE_DESKTOP_SMOKE" in main
    assert "MEDIMAGE_DESKTOP_SMOKE_RESULT" in main
    assert "MEDIMAGE_DESKTOP_USER_DATA" in main
    assert "MEDIMAGE_DESKTOP_API_BASE_URL" in main
    assert "loadFile(frontendIndex)" in main
    assert "medimage-backend.bin" in main
    assert "copyFileSync" in main
    assert "spawnSync" in main
    assert '"taskkill"' in main
    assert '"/t"' in main
    assert '"/f"' in main
    assert "backendProcess.kill()" in main
    assert "contextIsolation: true" in main
    assert "nodeIntegration: false" in main
    assert "sandbox: true" in main
    assert "setWindowOpenHandler" in main
    assert "MEDIMAGE_ENABLE_REVIEWED_EXECUTION" not in main
    assert "pywinauto" not in main.lower()
    assert "inference" not in main.lower()
    assert "safetensors" not in main.lower()


def test_preload_exposes_runtime_config_without_raw_ipc():
    preload = read("desktop/electron/preload.cjs")

    assert "MEDIMAGE_API_BASE_URL" in preload
    assert "__MEDIMAGE_DESKTOP_CONFIG__" in preload
    assert "backendBaseUrl" in preload
    assert "getBackendBaseUrl" in preload
    assert 'exposeInMainWorld("ipcRenderer"' not in preload


def test_electron_builder_contract():
    builder = read("desktop/electron/electron-builder.yml")

    assert "../../src/frontend/dist" in builder
    assert "../packaging/dist/backend_payload" in builder
    assert "workspace_seed/examples" in builder
    assert "target: nsis" in builder
    assert "target: portable" in builder
    assert "signAndEditExecutable: false" in builder
    assert "rawdata" not in builder
    assert "data/DemoData" not in builder


def test_desktop_package_contract():
    package_json = json.loads(read("desktop/electron/package.json"))

    assert package_json["main"] == "main.cjs"
    assert package_json["scripts"]["dist"] == "node build-dist.cjs"
    assert package_json["scripts"]["dist:dir"] == "node build-dist.cjs --win dir"
    assert "electron" in package_json["devDependencies"]
    assert "electron-builder" in package_json["devDependencies"]


def test_pyinstaller_spec_excludes_blocked_gui_and_model_modules():
    spec = read("desktop/packaging/pyinstaller_backend.spec")
    launcher_spec = read("desktop/packaging/pyinstaller_desktop_launcher.spec")

    assert "desktop_backend_entry.py" in spec
    assert "medimage-backend" in spec
    assert "upx=False" in spec
    assert 'runtime_tmpdir="."' in spec
    assert '"pywinauto"' in spec
    assert '"torch"' in spec
    assert '"safetensors"' in spec
    assert "desktop_launcher_entry.py" in launcher_spec
    assert "MedImage Agent" in launcher_spec
    assert "upx=False" in launcher_spec
    assert 'runtime_tmpdir="."' in launcher_spec
    assert '"src" / "frontend" / "dist"' in launcher_spec
    assert '"pywinauto"' in launcher_spec
    assert '"torch"' in launcher_spec
    assert '"safetensors"' in launcher_spec


def test_desktop_launcher_contract():
    launcher = read("src/backend/app/desktop_launcher_entry.py")

    assert "127.0.0.1" in launcher
    assert "find_available_port" in launcher
    assert "StaticFiles" in launcher
    assert "MEDIMAGE_DESKTOP_WORKSPACE" in launcher
    assert "MEDIMAGE_GUI_AGENT_PROVIDER" in launcher
    assert '"mock"' in launcher
    assert "server.should_exit = True" in launcher
    assert "pywinauto" not in launcher.lower()
    assert "inference" not in launcher.lower()
    assert "safetensors" not in launcher.lower()


def test_frontend_runtime_config_contract():
    client = read("src/frontend/src/lib/api/client.ts")
    vite = read("src/frontend/vite.config.ts")

    assert "__MEDIMAGE_DESKTOP_CONFIG__" in client
    assert "MEDIMAGE_API_BASE_URL" in client
    assert 'base: "./"' in vite


def test_desktop_dist_wrapper_uses_workspace_caches():
    wrapper = read("desktop/electron/build-dist.cjs")
    build_desktop = read("desktop/packaging/build_desktop.ps1")
    build_all = read("desktop/packaging/build_all_windows.ps1")

    assert "ELECTRON_CACHE" in wrapper
    assert ".electron-cache" in wrapper
    assert "ELECTRON_BUILDER_CACHE" in wrapper
    assert ".electron-builder-cache" in wrapper
    assert "TEMP: tempRoot" in wrapper
    assert "TMP: tempRoot" in wrapper
    assert ".tmp" in wrapper
    assert "NPM_CONFIG_CACHE" in wrapper
    assert ".npm-cache" in wrapper
    assert "frontendBuilder" in wrapper
    assert "MEDIMAGE_ELECTRON_RUNTIME_ZIP" in wrapper
    assert "MEDIMAGE_ELECTRON_NSIS_ARCHIVE" in wrapper
    assert "MEDIMAGE_ELECTRON_NSIS_RESOURCES_ARCHIVE" in wrapper
    assert "ELECTRON_BUILDER_NSIS_DIR" in wrapper
    assert "ELECTRON_BUILDER_BINARIES_DOWNLOAD_OVERRIDE_URL" in wrapper
    assert "manual-runtime" in wrapper
    assert "manual-nsis" in wrapper
    assert "manual-binaries" in wrapper
    assert "--config.electronDist" in wrapper
    assert "ElectronRuntimeZip" in build_desktop
    assert "ElectronRuntimeZip" in build_all
    assert "NsisArchive" in build_desktop
    assert "NsisArchive" in build_all
    assert "NsisResourcesArchive" in build_desktop
    assert "NsisResourcesArchive" in build_all
    assert "DirOnly" in build_desktop
    assert "DirOnly" in build_all
    assert "LASTEXITCODE" in build_desktop
    assert "Copy-Item" in build_desktop
    assert "backend_payload" in build_desktop


def test_desktop_docs_record_safety_boundaries():
    docs = read("docs/DESKTOP_APP_PACKAGING.md")

    required = [
        "does not enable real GUI automation",
        "does not enable PyWinAuto",
        "does not connect a real model",
        "does not call inference",
        "does not load model weights",
        "does not change the reviewed execution allowlist",
        "does not add GUI/manual reviewed execution nodes",
        "record_observation",
    ]
    for phrase in required:
        assert phrase in docs
