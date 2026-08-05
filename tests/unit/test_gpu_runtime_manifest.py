from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "desktop" / "packaging" / "write_gpu_runtime_manifest.py"


def _load_manifest_writer():
    spec = importlib.util.spec_from_file_location("gpu_runtime_manifest", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gpu_manifest_records_only_portable_gpu_dll_names(tmp_path: Path):
    module = _load_manifest_writer()
    sidecar = tmp_path / "sidecar"
    sidecar.mkdir()
    toc = tmp_path / "Analysis-00.toc"
    toc.write_text(
        "[('cudart64_12.dll', 'C:\\\\private\\\\cuda\\\\cudart64_12.dll', 'BINARY'), "
        "('nvJitLink_120_0.dll', 'C:\\\\private\\\\cuda\\\\nvJitLink_120_0.dll', 'BINARY'), "
        "('licenses/cuda/EULA.txt', 'C:\\\\private\\\\cuda\\\\EULA.txt', 'DATA'), "
        "('regular.dll', 'C:\\\\private\\\\regular.dll', 'BINARY')]",
        encoding="utf-8",
    )

    output = module.write_manifest(sidecar, toc)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["bundled_gpu_dlls"] == ["cudart64_12.dll", "nvJitLink_120_0.dll"]
    assert payload["cuda_eula_included"] is True
    assert "private" not in output.read_text(encoding="utf-8").lower()
