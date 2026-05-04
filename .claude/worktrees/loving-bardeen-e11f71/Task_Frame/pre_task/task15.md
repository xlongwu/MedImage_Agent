你是我的工程搭建助手。前十四步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。
Step 8：完成最小长期记忆、后台复盘和错误知识库闭环。
Step 9：完成最小 FastAPI 后端服务闭环。
Step 10：完成最小 React 前端闭环。
Step 11：完成 Run Monitor + State / Log Viewer 闭环。
Step 12：完成 Error Diagnosis + Retry Plan 闭环。
Step 13：完成 Checkpoint / Cache / Approved Retry 闭环。
Step 14：完成最小本地 subject-level 并行调度 + 资源限制闭环。

现在开始第十五步。

第十五步目标：实现“最小 GPU 加速原型 + CPU fallback + Benchmark 闭环”。

本步骤要实现一个医学影像 GPU 加速原型，但不要碰 SPM/DPABI 内核。  
我们先选择一个适合 GPU 的计算模块：ALFF / fALFF。

在 synthetic BIDS-like 数据上：

- 读取 subject 的 smoothed BOLD NIfTI
- 用 NumPy 实现 CPU ALFF / fALFF
- 如果安装了 CuPy 且 GPU 可用，则用 CuPy 实现 GPU ALFF / fALFF
- 如果 CuPy 不可用，自动 fallback 到 CPU
- 保存 ALFF / fALFF NIfTI 输出
- 记录 backend：cpu-numpy 或 gpu-cupy
- 记录 runtime_seconds
- 记录 gpu_available
- 如果同时运行 CPU 与 GPU benchmark，比较结果差异
- 生成 gpu_benchmark_summary.json
- 生成 gpu_benchmark_report.md
- 将 gpu_alff_subject 作为 subject-level pipeline node 接入现有 pipeline
- 前端增加 GPU Benchmark / Acceleration 区域

不要实现：
- GPU registration
- GPU normalization
- GPU smoothing
- CUDA kernel 手写
- PyTorch 版本
- 真实医学影像数据处理
- DPABI pipeline
- 改 SPM/DPABI 源码
- Slurm GPU
- 多 GPU
- GPU 调度器
- 数据库
- WebSocket
- 真实 LLM
- 临床结论

本步骤只做 synthetic 数据上的 ALFF / fALFF GPU 原型和 benchmark。

---

## 1. 创建 specs/gpu_runtime_spec.md

创建文件：

```text
specs/gpu_runtime_spec.md

内容：

# GPU Runtime Specification

This document defines the MVP GPU acceleration prototype for MedImage Agent.

## Goals

The GPU runtime demonstrates safe acceleration for matrix-heavy neuroimaging operations.

The MVP focuses on:

- ALFF
- fALFF
- CPU NumPy backend
- optional GPU CuPy backend
- CPU fallback
- benchmark reporting
- numerical comparison

## Why ALFF / fALFF

ALFF and fALFF are suitable first GPU targets because they are based on voxel-wise time-series FFT, which is matrix-heavy and does not require modifying SPM or DPABI internals.

## Scope

Supported:

- synthetic 4D BOLD NIfTI input
- subject-level ALFF / fALFF computation
- NumPy CPU backend
- optional CuPy GPU backend
- automatic CPU fallback
- NIfTI output
- runtime metrics
- benchmark summary
- benchmark report

Unsupported:

- GPU registration
- GPU normalization
- GPU segmentation
- GPU SPM internals
- multi-GPU
- Slurm GPU scheduling
- CUDA kernels
- DPABI replacement claim
- clinical interpretation

## Outputs

For each subject:

```text
derivatives/gpu_alff/{subject_id}/func/{subject_id}_alff.nii
derivatives/gpu_alff/{subject_id}/func/{subject_id}_falff.nii
derivatives/gpu_alff/{subject_id}/func/gpu_alff_result.json

Dataset-level benchmark:

reports/gpu_benchmark/gpu_benchmark_summary.json
reports/gpu_benchmark/gpu_benchmark_report.md
Metrics

Each subject result should include:

backend
gpu_available
cupy_available
runtime_seconds
input_shape
tr
freq_band
alff_output
falff_output
warnings
errors
Benchmark Comparison

If both CPU and GPU outputs are available, compare:

max_abs_diff_alff
mean_abs_diff_alff
max_abs_diff_falff
mean_abs_diff_falff
Safety Rules
Do not modify rawdata.
Do not delete files.
Do not modify SPM or DPABI.
Do not claim clinical meaning.
CPU fallback is required.
GPU result must be treated as experimental until validated.

---

## 2. 修改 examples/project_config_dataset.yaml

在现有配置中新增 gpu 配置。不要删除已有字段。

```yaml id="gpu_project_config"
gpu:
  enabled: true
  prefer_gpu: true
  require_gpu: false
  fallback_to_cpu: true
  benchmark_compare_cpu_gpu: true

说明：

enabled=true 表示允许 GPU 节点。
prefer_gpu=true 表示优先尝试 CuPy。
require_gpu=false 表示 GPU 不可用时不能失败，应 fallback CPU。
fallback_to_cpu=true 表示必须支持 CPU fallback。
benchmark_compare_cpu_gpu=true 表示如果 GPU 可用，同时跑 CPU 对照并比较结果。
3. 创建 backend/app/tools/gpu_utils.py

创建文件：

backend/app/tools/gpu_utils.py

目标：检测 CuPy / GPU 是否可用。

提供函数：

detect_gpu() -> dict

返回结构：

{
  "ok": true,
  "cupy_available": true,
  "gpu_available": true,
  "device_count": 1,
  "device_name": "NVIDIA ...",
  "errors": [],
  "warnings": []
}

如果 CuPy 没安装：

{
  "ok": true,
  "cupy_available": false,
  "gpu_available": false,
  "device_count": 0,
  "device_name": null,
  "errors": [],
  "warnings": ["CuPy is not installed. GPU backend unavailable."]
}

参考实现：

from __future__ import annotations

from typing import Any


def detect_gpu() -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        import cupy as cp
    except ImportError:
        return {
            "ok": True,
            "cupy_available": False,
            "gpu_available": False,
            "device_count": 0,
            "device_name": None,
            "warnings": ["CuPy is not installed. GPU backend unavailable."],
            "errors": [],
        }

    try:
        device_count = cp.cuda.runtime.getDeviceCount()
        if device_count <= 0:
            return {
                "ok": True,
                "cupy_available": True,
                "gpu_available": False,
                "device_count": 0,
                "device_name": None,
                "warnings": ["CuPy is installed but no CUDA device was detected."],
                "errors": [],
            }

        device = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(0)
        device_name = props.get("name", b"unknown")
        if isinstance(device_name, bytes):
            device_name = device_name.decode("utf-8", errors="replace")

        with device:
            _ = cp.asarray([1.0, 2.0, 3.0]).sum().item()

        return {
            "ok": True,
            "cupy_available": True,
            "gpu_available": True,
            "device_count": int(device_count),
            "device_name": str(device_name),
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        return {
            "ok": True,
            "cupy_available": True,
            "gpu_available": False,
            "device_count": 0,
            "device_name": None,
            "warnings": [f"CuPy is installed but GPU check failed: {exc}"],
            "errors": [],
        }
4. 创建 backend/app/tools/alff_compute.py

创建文件：

backend/app/tools/alff_compute.py

目标：实现 CPU/GPU ALFF 和 fALFF 计算。

提供函数：

compute_alff_numpy(data, tr: float, freq_band: tuple[float, float]) -> tuple
compute_alff_cupy(data, tr: float, freq_band: tuple[float, float]) -> tuple
compute_alff_backend(data, tr: float, freq_band: tuple[float, float], prefer_gpu: bool, require_gpu: bool) -> dict

要求：

输入 data 是 4D array：X, Y, Z, T。
沿最后一个维度做 FFT。
频率轴用 np.fft.rfftfreq(n_timepoints, d=tr)。
ALFF：
对目标频段内振幅求平均。
fALFF：
目标频段振幅和 / 全频段振幅和。
如果时间点太少，仍然运行，但 warnings 记录。
如果 CuPy 不可用，fallback NumPy。
返回：
alff
falff
backend
runtime_seconds
warnings
errors
注意除零：fALFF denominator 为 0 时设为 0。
不要引入 scipy。

参考实现：

from __future__ import annotations

import time
from typing import Any

import numpy as np


def _safe_falff(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    out = np.zeros_like(numerator, dtype="float32")
    mask = denominator > 0
    out[mask] = numerator[mask] / denominator[mask]
    return out.astype("float32")


def compute_alff_numpy(
    data: np.ndarray,
    tr: float,
    freq_band: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    warnings: list[str] = []

    if data.ndim != 4:
        raise ValueError(f"Expected 4D BOLD data, got shape={data.shape}")

    n_timepoints = data.shape[-1]
    if n_timepoints < 8:
        warnings.append(f"Very few timepoints for ALFF: {n_timepoints}")

    data = data.astype("float32")
    data = data - np.mean(data, axis=-1, keepdims=True)

    freqs = np.fft.rfftfreq(n_timepoints, d=tr)
    spectrum = np.fft.rfft(data, axis=-1)
    amplitude = np.abs(spectrum).astype("float32")

    low, high = freq_band
    band_mask = (freqs >= low) & (freqs <= high)

    if not np.any(band_mask):
        warnings.append(
            f"No FFT bins found in frequency band {freq_band}; ALFF will be zeros."
        )
        alff = np.zeros(data.shape[:3], dtype="float32")
        falff = np.zeros(data.shape[:3], dtype="float32")
        return alff, falff, warnings

    band_amp = amplitude[..., band_mask]
    alff = np.mean(band_amp, axis=-1).astype("float32")

    total_amp = np.sum(amplitude[..., 1:], axis=-1).astype("float32")
    band_sum = np.sum(band_amp, axis=-1).astype("float32")
    falff = _safe_falff(band_sum, total_amp)

    return alff, falff, warnings


def compute_alff_cupy(
    data: np.ndarray,
    tr: float,
    freq_band: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    warnings: list[str] = []

    try:
        import cupy as cp
    except ImportError as exc:
        raise RuntimeError("CuPy is not installed.") from exc

    if data.ndim != 4:
        raise ValueError(f"Expected 4D BOLD data, got shape={data.shape}")

    n_timepoints = data.shape[-1]
    if n_timepoints < 8:
        warnings.append(f"Very few timepoints for ALFF: {n_timepoints}")

    x = cp.asarray(data.astype("float32"))
    x = x - cp.mean(x, axis=-1, keepdims=True)

    freqs = cp.asarray(np.fft.rfftfreq(n_timepoints, d=tr))
    spectrum = cp.fft.rfft(x, axis=-1)
    amplitude = cp.abs(spectrum).astype(cp.float32)

    low, high = freq_band
    band_mask = (freqs >= low) & (freqs <= high)

    if not bool(cp.any(band_mask).get()):
        warnings.append(
            f"No FFT bins found in frequency band {freq_band}; ALFF will be zeros."
        )
        alff = cp.zeros(x.shape[:3], dtype=cp.float32)
        falff = cp.zeros(x.shape[:3], dtype=cp.float32)
        return cp.asnumpy(alff), cp.asnumpy(falff), warnings

    band_amp = amplitude[..., band_mask]
    alff = cp.mean(band_amp, axis=-1).astype(cp.float32)

    total_amp = cp.sum(amplitude[..., 1:], axis=-1).astype(cp.float32)
    band_sum = cp.sum(band_amp, axis=-1).astype(cp.float32)

    falff = cp.zeros_like(band_sum, dtype=cp.float32)
    mask = total_amp > 0
    falff[mask] = band_sum[mask] / total_amp[mask]

    cp.cuda.Stream.null.synchronize()

    return cp.asnumpy(alff), cp.asnumpy(falff), warnings


def compute_alff_backend(
    data: np.ndarray,
    tr: float,
    freq_band: tuple[float, float],
    prefer_gpu: bool = True,
    require_gpu: bool = False,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if prefer_gpu:
        try:
            start = time.perf_counter()
            alff, falff, backend_warnings = compute_alff_cupy(data, tr, freq_band)
            runtime_seconds = time.perf_counter() - start
            warnings.extend(backend_warnings)
            return {
                "ok": True,
                "backend": "gpu-cupy",
                "alff": alff.astype("float32"),
                "falff": falff.astype("float32"),
                "runtime_seconds": runtime_seconds,
                "warnings": warnings,
                "errors": errors,
            }
        except Exception as exc:
            if require_gpu:
                return {
                    "ok": False,
                    "backend": "gpu-cupy",
                    "alff": None,
                    "falff": None,
                    "runtime_seconds": None,
                    "warnings": warnings,
                    "errors": [f"GPU ALFF failed and require_gpu=true: {exc}"],
                }
            warnings.append(f"GPU backend unavailable, falling back to CPU: {exc}")

    start = time.perf_counter()
    alff, falff, backend_warnings = compute_alff_numpy(data, tr, freq_band)
    runtime_seconds = time.perf_counter() - start
    warnings.extend(backend_warnings)

    return {
        "ok": True,
        "backend": "cpu-numpy",
        "alff": alff.astype("float32"),
        "falff": falff.astype("float32"),
        "runtime_seconds": runtime_seconds,
        "warnings": warnings,
        "errors": errors,
    }
5. 创建 backend/app/tools/gpu_alff_runner.py

创建文件：

backend/app/tools/gpu_alff_runner.py

目标：对单个 subject 的 smoothed BOLD 执行 ALFF / fALFF。

提供函数：

run_alff_subject(
    subject_id: str,
    input_nii: str,
    derivatives_dir: str,
    tr: float = 2.0,
    freq_band: list[float] | None = None,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    benchmark_compare_cpu_gpu: bool = True,
) -> dict

要求：

使用 nibabel 读取 smoothed BOLD。
调用 compute_alff_backend。
输出：
derivatives/gpu_alff/{subject_id}/func/{subject_id}_alff.nii
derivatives/gpu_alff/{subject_id}/func/{subject_id}_falff.nii
derivatives/gpu_alff/{subject_id}/func/gpu_alff_result.json
如果 benchmark_compare_cpu_gpu=true 且 GPU 可用：
同时跑 CPU 和 GPU
比较差异
记录 max_abs_diff_alff、mean_abs_diff_alff、max_abs_diff_falff、mean_abs_diff_falff
如果 GPU 不可用：
fallback CPU
warnings 记录
返回结构化 dict。
不修改 rawdata。
不删除文件。

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from backend.app.tools.alff_compute import compute_alff_backend, compute_alff_numpy
from backend.app.tools.gpu_utils import detect_gpu


def _compare_arrays(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    diff = np.abs(a.astype("float32") - b.astype("float32"))
    return {
        "max_abs_diff": float(np.max(diff)),
        "mean_abs_diff": float(np.mean(diff)),
    }


def run_alff_subject(
    subject_id: str,
    input_nii: str,
    derivatives_dir: str,
    tr: float = 2.0,
    freq_band: list[float] | None = None,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    benchmark_compare_cpu_gpu: bool = True,
) -> dict[str, Any]:
    try:
        import nibabel as nib
    except ImportError:
        return {
            "ok": False,
            "node_id": "gpu_alff_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "metrics": {},
            "warnings": [],
            "errors": ["Missing dependency: nibabel. Install with: pip install nibabel"],
        }

    freq_band = freq_band or [0.01, 0.08]
    band_tuple = (float(freq_band[0]), float(freq_band[1]))

    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    if not input_path.exists():
        return {
            "ok": False,
            "node_id": "gpu_alff_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "metrics": {},
            "warnings": [],
            "errors": [f"Input smoothed BOLD not found: {input_path}"],
        }

    out_dir = Path(derivatives_dir) / "gpu_alff" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    alff_path = out_dir / f"{subject_id}_alff.nii"
    falff_path = out_dir / f"{subject_id}_falff.nii"
    result_json = out_dir / "gpu_alff_result.json"

    try:
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")

        if data.ndim != 4:
            raise ValueError(f"Expected 4D BOLD input, got shape={data.shape}")

        gpu_info = detect_gpu()
        warnings.extend(gpu_info.get("warnings", []))

        result = compute_alff_backend(
            data=data,
            tr=tr,
            freq_band=band_tuple,
            prefer_gpu=prefer_gpu,
            require_gpu=require_gpu,
        )

        warnings.extend(result.get("warnings", []))
        errors.extend(result.get("errors", []))

        if not result.get("ok"):
            payload = {
                "ok": False,
                "node_id": "gpu_alff_subject",
                "backend": result.get("backend"),
                "subject_id": subject_id,
                "outputs": [],
                "metrics": {},
                "warnings": warnings,
                "errors": errors,
            }
            result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return payload

        alff = result["alff"]
        falff = result["falff"]

        nib.save(nib.Nifti1Image(alff.astype("float32"), img.affine, img.header), str(alff_path))
        nib.save(nib.Nifti1Image(falff.astype("float32"), img.affine, img.header), str(falff_path))

        comparison: dict[str, Any] = {}

        if benchmark_compare_cpu_gpu and result.get("backend") == "gpu-cupy":
            cpu_alff, cpu_falff, cpu_warnings = compute_alff_numpy(data, tr, band_tuple)
            warnings.extend([f"CPU benchmark: {item}" for item in cpu_warnings])

            alff_diff = _compare_arrays(cpu_alff, alff)
            falff_diff = _compare_arrays(cpu_falff, falff)

            comparison = {
                "max_abs_diff_alff": alff_diff["max_abs_diff"],
                "mean_abs_diff_alff": alff_diff["mean_abs_diff"],
                "max_abs_diff_falff": falff_diff["max_abs_diff"],
                "mean_abs_diff_falff": falff_diff["mean_abs_diff"],
            }

        metrics = {
            "backend": result.get("backend"),
            "gpu_available": gpu_info.get("gpu_available"),
            "cupy_available": gpu_info.get("cupy_available"),
            "device_name": gpu_info.get("device_name"),
            "runtime_seconds": result.get("runtime_seconds"),
            "input_shape": list(data.shape),
            "tr": tr,
            "freq_band": list(band_tuple),
            **comparison,
        }

        payload = {
            "ok": True,
            "node_id": "gpu_alff_subject",
            "backend": result.get("backend"),
            "subject_id": subject_id,
            "input": str(input_path),
            "outputs": [str(alff_path), str(falff_path), str(result_json)],
            "metrics": metrics,
            "warnings": warnings,
            "errors": errors,
        }

        result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    except Exception as exc:
        payload = {
            "ok": False,
            "node_id": "gpu_alff_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Failed to run ALFF subject: {exc}"],
        }
        result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
6. 创建 backend/app/tools/gpu_benchmark_report.py

创建文件：

backend/app/tools/gpu_benchmark_report.py

目标：聚合所有 subject 的 gpu_alff_result.json，生成报告。

提供函数：

write_gpu_benchmark_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict

输出：

reports/gpu_benchmark/gpu_benchmark_summary.json
reports/gpu_benchmark/gpu_benchmark_report.md

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_gpu_benchmark_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    gpu_root = Path(derivatives_dir) / "gpu_alff"
    out_dir = Path(report_dir) / "gpu_benchmark"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "gpu_benchmark_summary.json"
    report_path = out_dir / "gpu_benchmark_report.md"

    subject_results = []
    warnings: list[str] = []
    errors: list[str] = []

    if not gpu_root.exists():
        warnings.append(f"No gpu_alff directory found: {gpu_root}")
    else:
        for result_path in sorted(gpu_root.glob("*/func/gpu_alff_result.json")):
            payload = _read_json(result_path)
            if payload:
                subject_results.append(payload)
            else:
                warnings.append(f"Invalid gpu_alff_result.json: {result_path}")

    subjects_total = len(subject_results)
    subjects_success = sum(1 for item in subject_results if item.get("ok"))
    gpu_backend_count = sum(1 for item in subject_results if item.get("backend") == "gpu-cupy")
    cpu_backend_count = sum(1 for item in subject_results if item.get("backend") == "cpu-numpy")

    runtimes = [
        item.get("metrics", {}).get("runtime_seconds")
        for item in subject_results
        if item.get("metrics", {}).get("runtime_seconds") is not None
    ]

    mean_runtime = sum(runtimes) / len(runtimes) if runtimes else None

    summary = {
        "subjects_total": subjects_total,
        "subjects_success": subjects_success,
        "gpu_backend_count": gpu_backend_count,
        "cpu_backend_count": cpu_backend_count,
        "mean_runtime_seconds": mean_runtime,
        "warnings": warnings,
        "errors": errors,
        "note": "GPU ALFF is experimental and for engineering benchmark only.",
        "subjects": [
            {
                "subject_id": item.get("subject_id"),
                "ok": item.get("ok"),
                "backend": item.get("backend"),
                "runtime_seconds": item.get("metrics", {}).get("runtime_seconds"),
                "gpu_available": item.get("metrics", {}).get("gpu_available"),
                "device_name": item.get("metrics", {}).get("device_name"),
                "max_abs_diff_alff": item.get("metrics", {}).get("max_abs_diff_alff"),
                "max_abs_diff_falff": item.get("metrics", {}).get("max_abs_diff_falff"),
            }
            for item in subject_results
        ],
    }

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# GPU Benchmark Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- Subjects success: {subjects_success}")
    lines.append(f"- GPU backend count: {gpu_backend_count}")
    lines.append(f"- CPU backend count: {cpu_backend_count}")
    lines.append(f"- Mean runtime seconds: {mean_runtime}")
    lines.append("")
    lines.append("## Subject Results")
    lines.append("")
    if subject_results:
        lines.append("| Subject | OK | Backend | Runtime seconds | GPU available | Device | Max diff ALFF | Max diff fALFF |")
        lines.append("|---|---:|---|---:|---:|---|---:|---:|")
        for item in summary["subjects"]:
            lines.append(
                f"| {item.get('subject_id')} | {item.get('ok')} | {item.get('backend')} | "
                f"{item.get('runtime_seconds')} | {item.get('gpu_available')} | {item.get('device_name')} | "
                f"{item.get('max_abs_diff_alff')} | {item.get('max_abs_diff_falff')} |"
            )
    else:
        lines.append("No subject GPU benchmark results found.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report is for engineering benchmark only. It is not a clinical or scientific validation.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "gpu_benchmark_report",
        "backend": "python",
        "outputs": [str(summary_path), str(report_path)],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_success": subjects_success,
            "gpu_backend_count": gpu_backend_count,
            "cpu_backend_count": cpu_backend_count,
            "mean_runtime_seconds": mean_runtime,
        },
        "warnings": warnings,
        "errors": errors,
    }
7. 修改 backend/app/runtime/node_registry.py

新增两个节点：

gpu_alff_subject
gpu_benchmark_report

要求：

不破坏已有节点。
gpu_alff_subject 是 subject-level node。
gpu_benchmark_report 是 project-level node。
gpu_alff_subject 从 previous_subject_results 中读取 spm_smooth_subject 输出。
如果没有 smoothed output，返回 ok=false。
从 project_config.gpu 读取 prefer_gpu、require_gpu、benchmark_compare_cpu_gpu。
从 node.params 读取 tr 和 freq_band。

新增导入：

from backend.app.tools.gpu_alff_runner import run_alff_subject
from backend.app.tools.gpu_benchmark_report import write_gpu_benchmark_report

新增 runner：

def run_gpu_alff_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    if not context.subject_id:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "outputs": [],
            "errors": ["Missing subject_id in context."],
        }

    previous = context.previous_subject_results or {}
    smooth_result = previous.get("spm_smooth_subject", {})
    outputs = smooth_result.get("outputs", [])

    if not outputs:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "subject_id": context.subject_id,
            "outputs": [],
            "errors": ["No smoothed BOLD output found from spm_smooth_subject."],
        }

    gpu_config = context.project_config.get("gpu", {}) or {}

    result = run_alff_subject(
        subject_id=context.subject_id,
        input_nii=outputs[0],
        derivatives_dir=context.derivatives_dir,
        tr=float(node.params.get("tr", 2.0)),
        freq_band=node.params.get("freq_band", [0.01, 0.08]),
        prefer_gpu=bool(gpu_config.get("prefer_gpu", True)),
        require_gpu=bool(gpu_config.get("require_gpu", False)),
        benchmark_compare_cpu_gpu=bool(gpu_config.get("benchmark_compare_cpu_gpu", True)),
    )
    result["node_id"] = node.id
    return result


def run_gpu_benchmark_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    return write_gpu_benchmark_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )

更新 NODE_REGISTRY：

"gpu_alff_subject": run_gpu_alff_subject_node,
"gpu_benchmark_report": run_gpu_benchmark_report_node,
8. 新增 examples/pipeline_gpu_alff.yaml

创建文件：

examples/pipeline_gpu_alff.yaml

内容：

pipeline_id: gpu_alff_pipeline
version: "0.1.0"
modality: synthetic-rsfmri
description: "Synthetic subject-level SPM smoothing followed by experimental CPU/GPU ALFF and fALFF."

execution:
  stop_on_failure: true
  run_id: "run_gpu_alff_001"
  scheduler:
    mode: "local_parallel"
    max_workers: 2
    matlab_max_workers: 1

nodes:
  - id: create_synthetic_bids
    name: Create Synthetic BIDS Dataset
    agent: data-inspector
    backend: python
    depends_on: []
    inputs: []
    outputs:
      - "./examples/synthetic_bids/rawdata/dataset_description.json"
      - "./examples/synthetic_bids/rawdata/participants.tsv"
    params:
      output_dir: "./examples/synthetic_bids/rawdata"
      subjects:
        - sub-001
        - sub-002
        - sub-003
        - sub-004
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: data_inspection
    name: Data Inspection
    agent: data-inspector
    backend: python
    depends_on:
      - create_synthetic_bids
    inputs:
      - "./examples/synthetic_bids/rawdata"
    outputs:
      - "./work/dataset_index/dataset_index.json"
      - "./work/dataset_index/data_completeness_report.json"
      - "./work/dataset_index/subject_table.csv"
    params:
      rawdata_dir: "./examples/synthetic_bids/rawdata"
      output_dir: "./work/dataset_index"
      read_nifti_metadata: true
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: spm_smooth_subject
    name: SPM Smooth Subject BOLD
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - data_inspection
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs: []
    params:
      dataset_index: "./work/dataset_index/dataset_index.json"
      fwhm: [4, 4, 4]
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: gpu_alff_subject
    name: Experimental CPU/GPU ALFF and fALFF
    agent: gpu-optimizer
    backend: python-cupy
    depends_on:
      - spm_smooth_subject
    inputs: []
    outputs: []
    params:
      tr: 2.0
      freq_band: [0.01, 0.08]
    parallel_level: subject
    gpu_supported: true
    cache: false

  - id: subject_qc
    name: Subject QC
    agent: qc-agent
    backend: python
    depends_on:
      - spm_smooth_subject
    inputs: []
    outputs: []
    params:
      qc_output_dir: "./derivatives/qc"
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: gpu_benchmark_report
    name: GPU Benchmark Report
    agent: gpu-optimizer
    backend: python
    depends_on:
      - gpu_alff_subject
    inputs: []
    outputs:
      - "./reports/gpu_benchmark/gpu_benchmark_summary.json"
      - "./reports/gpu_benchmark/gpu_benchmark_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dataset_evaluation
    name: Dataset Evaluation
    agent: dataset-evaluator
    backend: python
    depends_on:
      - subject_qc
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs:
      - "./reports/dataset_evaluation/dataset_summary.json"
      - "./reports/dataset_evaluation/subject_qc_table.csv"
      - "./reports/dataset_evaluation/exclusion_recommendations.csv"
      - "./reports/dataset_evaluation/dataset_evaluation_report.md"
      - "./reports/dataset_evaluation/dataset_evaluation_report.html"
    params:
      dataset_index: "./work/dataset_index/dataset_index.json"
      output_dir: "./reports/dataset_evaluation"
    parallel_level: project
    gpu_supported: false
    cache: false
9. 新增 backend/app/tools/gpu_check_cli.py

创建文件：

backend/app/tools/gpu_check_cli.py

内容：

from __future__ import annotations

import json

from backend.app.tools.gpu_utils import detect_gpu


def main() -> int:
    result = detect_gpu()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
10. 新增 backend/app/tools/run_gpu_alff_pipeline_cli.py

创建文件：

backend/app/tools/run_gpu_alff_pipeline_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_gpu_alff.yaml")

    summary = run_pipeline(project_config, pipeline)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    status = summary.get("status")
    if status == "SUCCESS":
        return 0
    if status == "INVALID":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
11. 修改 backend/app/api/models.py

新增：

class GpuCheckResponse(BaseModel):
    ok: bool

如果不需要独立 response model，也可以不加。保持简单即可。

12. 修改 backend/app/api/routes.py

新增 API：

GET /api/gpu/check
GET /api/reports/gpu-benchmark

新增导入：

from backend.app.tools.gpu_utils import detect_gpu

新增路由：

@router.get("/api/gpu/check")
def api_gpu_check() -> dict[str, Any]:
    return detect_gpu()


@router.get("/api/reports/gpu-benchmark")
def get_gpu_benchmark_report() -> dict[str, Any]:
    base = Path("reports") / "gpu_benchmark"

    return {
        "ok": True,
        "gpu_benchmark_summary": _read_json_if_exists(base / "gpu_benchmark_summary.json"),
        "gpu_benchmark_report": _read_text_if_exists(base / "gpu_benchmark_report.md"),
    }
13. 修改 frontend/src/api.ts

新增：

export async function checkGpu(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/gpu/check");
}

export async function getGpuBenchmarkReport(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/reports/gpu-benchmark"
  );
}
14. 创建 frontend/src/components/GpuPanel.tsx

创建文件：

frontend/src/components/GpuPanel.tsx

内容：

import { useState } from "react";
import { checkGpu, getGpuBenchmarkReport } from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function GpuPanel({ baseUrl }: Props) {
  const [gpuInfo, setGpuInfo] = useState<unknown>(null);
  const [benchmark, setBenchmark] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleGpuCheck() {
    setStatus("CHECKING");
    setError("");

    try {
      const result = await checkGpu(baseUrl);
      setGpuInfo(result);
      setStatus(result.gpu_available ? "GPU_AVAILABLE" : "CPU_FALLBACK");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadBenchmark() {
    setError("");

    try {
      const result = await getGpuBenchmarkReport(baseUrl);
      setBenchmark(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="row">
        <button onClick={handleGpuCheck}>检测 GPU / CuPy</button>
        <button onClick={handleLoadBenchmark}>加载 GPU Benchmark 报告</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <h3>GPU Info</h3>
      <JsonBlock value={gpuInfo} emptyText="尚未检测 GPU" />

      <h3>GPU Benchmark Summary</h3>
      <JsonBlock
        value={benchmark?.gpu_benchmark_summary}
        emptyText="尚未生成 benchmark summary"
      />

      <h3>GPU Benchmark Report</h3>
      <TextViewer
        text={
          typeof benchmark?.gpu_benchmark_report === "string"
            ? benchmark.gpu_benchmark_report
            : null
        }
        emptyText="尚未生成 benchmark report"
      />
    </div>
  );
}
15. 修改 frontend/src/App.tsx

新增导入：

import { GpuPanel } from "./components/GpuPanel";

在 Scheduler / Resource Plan 后面新增 Section：

<Section
  title="4. GPU Acceleration / Benchmark"
  description="检测 CuPy/GPU 可用性，查看 ALFF/fALFF 加速 benchmark。"
>
  <GpuPanel baseUrl={baseUrl} />
</Section>

后续章节编号顺延。

16. 修改 backend/app/tools/api_smoke_test.py

新增测试：

call("GET", "/api/gpu/check")
call("GET", "/api/reports/gpu-benchmark")

不要在 smoke test 中自动运行 GPU pipeline。

17. 更新 README.md

追加第十五步说明：

## Step 15: MVP GPU ALFF / fALFF Acceleration

This step adds an experimental CPU/GPU ALFF and fALFF module.

It supports:

- NumPy CPU backend
- optional CuPy GPU backend
- CPU fallback
- ALFF / fALFF NIfTI outputs
- benchmark summary
- benchmark report

### Install CPU dependencies

```bash
pip install numpy nibabel pyyaml
Optional CuPy installation

Install a CuPy package matching your CUDA environment, for example:

pip install cupy-cuda12x

If CuPy or GPU is unavailable, the pipeline falls back to CPU.

Check GPU
python -m backend.app.tools.gpu_check_cli
Run GPU ALFF Pipeline
python -m backend.app.tools.run_gpu_alff_pipeline_cli

Expected outputs:

derivatives/gpu_alff/sub-001/func/sub-001_alff.nii
derivatives/gpu_alff/sub-001/func/sub-001_falff.nii
derivatives/gpu_alff/sub-001/func/gpu_alff_result.json

reports/gpu_benchmark/gpu_benchmark_summary.json
reports/gpu_benchmark/gpu_benchmark_report.md
API
curl http://127.0.0.1:8000/api/gpu/check
curl http://127.0.0.1:8000/api/reports/gpu-benchmark
Safety

This GPU module is experimental and for engineering benchmark only.

It does not:

modify rawdata
modify SPM or DPABI
replace validated clinical or research pipelines
make clinical conclusions

---

## 18. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/gpu_runtime_spec.md
examples/project_config_dataset.yaml
examples/pipeline_gpu_alff.yaml
backend/app/tools/gpu_utils.py
backend/app/tools/alff_compute.py
backend/app/tools/gpu_alff_runner.py
backend/app/tools/gpu_benchmark_report.py
backend/app/runtime/node_registry.py
backend/app/tools/gpu_check_cli.py
backend/app/tools/run_gpu_alff_pipeline_cli.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/GpuPanel.tsx
frontend/src/App.tsx
README.md

检测 GPU：

python -m backend.app.tools.gpu_check_cli

如果没有 CuPy 或 GPU，也应该返回 ok=true，并说明 fallback。

运行 GPU ALFF pipeline：

python -m backend.app.tools.run_gpu_alff_pipeline_cli

成功后应生成：

derivatives/gpu_alff/sub-001/func/sub-001_alff.nii
derivatives/gpu_alff/sub-001/func/sub-001_falff.nii
derivatives/gpu_alff/sub-001/func/gpu_alff_result.json

reports/gpu_benchmark/gpu_benchmark_summary.json
reports/gpu_benchmark/gpu_benchmark_report.md

work/pipeline_runs/run_gpu_alff_001/summary.json

summary 应包含 gpu_alff_subject 节点状态。

如果没有 GPU：

pipeline 不应直接失败。
gpu_alff_result.json 中 backend 应为 cpu-numpy。
warnings 中应说明 GPU 不可用或 CuPy 未安装。

如果有 GPU 和 CuPy：

backend 应为 gpu-cupy。
如果 benchmark_compare_cpu_gpu=true，应记录：
max_abs_diff_alff
mean_abs_diff_alff
max_abs_diff_falff
mean_abs_diff_falff

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/gpu/check
curl http://127.0.0.1:8000/api/reports/gpu-benchmark

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 GPU Acceleration / Benchmark 区域。
点击检测 GPU。
显示 CuPy 是否可用。
显示 GPU 是否可用。
加载 gpu_benchmark_summary。
加载 gpu_benchmark_report。
不自动运行 GPU pipeline。
不声称临床意义。
19. 重要限制

本步骤只做 MVP GPU ALFF / fALFF 原型。

不要实现：

GPU SPM
GPU DPABI
GPU registration
GPU normalization
GPU smoothing
Slurm GPU
多 GPU
CUDA kernel
PyTorch 后端
医学结论
真实数据验证结论
自动替代 DPABI/SPM

完成后请总结：

新增了哪些文件
修改了哪些文件
如何检测 GPU
如何运行 GPU ALFF pipeline
没有 GPU 时如何 fallback
benchmark 输出在哪里
当前 GPU 原型有哪些限制

'''
Step 15 主要实现的是 GPU 加速原型 + CPU 回退 + Benchmark 闭环 。

## 核心目标
这一步构建一个 最小可行的 GPU 加速原型 ，用于加速神经影像计算中的矩阵密集型操作（ALFF/fALFF），同时确保：

1. GPU 加速 - 使用 CuPy 实现 GPU 版本的 ALFF/fALFF 计算
2. CPU 回退 - 当 GPU 不可用时自动回退到 NumPy CPU 实现
3. Benchmark 对比 - 比较 CPU 和 GPU 的性能和数值精度
## 为什么选择 ALFF/fALFF
ALFF（低频振幅）和 fALFF（分数低频振幅）是基于体素时间序列 FFT 的计算，具有以下特点：

- 矩阵密集型（适合 GPU 加速）
- 不需要修改 SPM 或 DPABI 内部代码
- 计算独立，易于并行化
## 主要组件
组件 功能 gpu_utils.py 检测 CuPy 和 CUDA 设备可用性 alff_compute.py ALFF/fALFF 计算（NumPy CPU + CuPy GPU） gpu_alff_runner.py 运行单个 subject 的 GPU ALFF gpu_benchmark_cli.py CLI 工具用于 benchmark gpu_alff_node.py Pipeline 节点实现 GpuBenchmarkPanel.tsx 前端 GPU Benchmark 面板

## 安全规则
- 不修改 rawdata
- 不删除文件
- 不修改 SPM 或 DPABI
- CPU 回退必须可用
- GPU 结果标记为实验性，需要验证
'''