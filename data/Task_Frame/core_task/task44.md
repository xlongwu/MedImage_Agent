# 第四十四步 Prompt：ALFF / fALFF 计算 + QC + GPU Candidate Backend 设计闭环

```text
你是我的工程搭建助手。前四十三步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- SPM Slice Timing Correction + Metadata QC
- SPM Realignment + Motion QC
- Slice Timing → Realignment → Motion QC 链式核心 pipeline
- SPM Coregistration + Registration QC
- SPM Segmentation + Tissue QC
- SPM Normalization + Normalization QC
- SPM Smoothing + Smoothing QC
- Nuisance Regression 参数计划 + Confound Matrix + Python/DPABI 双后端设计
- Temporal Filtering + Filtering QC

现在开始第四十四步。

第四十四步目标：实现 “ALFF / fALFF 计算 + QC + GPU Candidate Backend 设计闭环”。

当前系统已经可以完成：

synthetic raw BOLD
→ SPM slice timing correction
→ SPM realignment
→ motion QC
→ SPM coregistration
→ registration QC
→ SPM segmentation
→ tissue QC
→ SPM normalization
→ normalization QC
→ SPM smoothing
→ smoothing QC
→ confound matrix
→ Python nuisance regression
→ nuisance regression QC
→ Python temporal filtering
→ filtering QC

但还缺少 rs-fMRI 低频振幅指标计算。  
本步骤要继续深入 rs-fMRI 后处理，实现：

nuisance-regressed functional image
+ filtered residual functional image
+ TR / frequency band
→ ALFF map
→ fALFF map
→ ALFF/fALFF QC
→ subject-level ALFF/fALFF report
→ dataset-level ALFF/fALFF report

本步骤还要设计 GPU candidate backend，但本步骤不要真正依赖 GPU，不要求 CUDA，不要求 CuPy 必须可用。

本步骤要实现：

1. ALFF / fALFF specification。
2. Python NumPy backend：
   - 从 `resid_swr*.nii` 计算 full-spectrum amplitude。
   - 从 `filt_resid_swr*.nii` 或频段 mask 计算 low-frequency amplitude。
   - 输出 ALFF map。
   - 输出 fALFF map。
3. TR 和频段参数读取：
   - 优先 temporal filtering QC。
   - 其次 slice timing QC。
   - 最后显式 fallback。
4. ALFF / fALFF QC：
   - input exists
   - filtered input exists
   - output exists
   - shape consistency
   - TR
   - low_hz / high_hz
   - Nyquist
   - retained frequency bins
   - ALFF finite fraction
   - fALFF finite fraction
   - ALFF mean/std
   - fALFF mean/std
   - fALFF range sanity
   - alff_qc_status
5. 输出 subject-level ALFF/fALFF QC JSON / Markdown。
6. 输出 dataset-level ALFF/fALFF QC summary / Markdown report。
7. GPU candidate backend contract：
   - 记录未来可用 CuPy / Torch / MATLAB GPU 方向。
   - 本步骤只生成 contract，不执行 GPU。
   - 明确 `gpu_executed=false`。
8. DPABI ALFF backend contract：
   - 本步骤只生成 contract，不执行 DPABI。
   - 不调用 DPARSF_run / DPARSFA_run。
   - 不调用 DPABI GUI。
9. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC → Normalization → Normalization QC → Smoothing → Smoothing QC → Confound Matrix → Python Nuisance Regression → Regression QC → Temporal Filtering → Filtering QC → ALFF/fALFF → ALFF/fALFF QC
10. 后端 API 暴露 ALFF / fALFF 结果。
11. 前端新增 rs-fMRI ALFF / fALFF 面板。
12. 增加轻量 unit test。
13. 更新 README。

本步骤允许执行 Python NumPy ALFF/fALFF，但必须满足：

- 只处理 synthetic BIDS-like derivative 数据。
- ALFF 输入必须来自 derivatives 中的 nuisance regression 或 filtering 输出。
- TR 必须来自 temporal filtering QC、slice timing QC 或显式 fallback。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不执行 GPU。
- 不要求 CUDA / CuPy / Torch。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- ReHo
- functional connectivity
- group-level statistics
- 真实 DPABI ALFF/fALFF 执行
- 真实 GPU 执行
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：Python NumPy ALFF/fALFF、ALFF/fALFF QC、GPU candidate contract、DPABI ALFF backend contract。

---

## 1. 创建 specs/alff_falff_qc_spec.md

创建文件：

```text
specs/alff_falff_qc_spec.md
```

内容：

```markdown
# ALFF / fALFF and QC Specification

This document defines the MVP ALFF and fALFF computation stage for rs-fMRI post-processing.

## Goals

The goal is to compute ALFF and fALFF maps from nuisance-regressed and temporally filtered synthetic rs-fMRI derivatives, then generate lightweight QC reports.

This step prepares subject-level low-frequency amplitude maps for later reporting, visualization, and group-level analysis.

## Scope

Supported in this step:

- synthetic derivative input only
- Python NumPy ALFF/fALFF backend
- TR discovery from temporal filtering QC or slice timing QC
- explicit TR fallback
- ALFF map output
- fALFF map output
- subject-level ALFF/fALFF QC JSON / Markdown
- dataset-level ALFF/fALFF QC summary / report
- GPU candidate backend contract generation without GPU execution
- DPABI ALFF backend contract generation without DPABI execution
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- GPU execution
- ReHo
- functional connectivity
- group-level statistics
- rawdata modification
- source modification in SPM / DPABI
- file deletion

## Inputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii
derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii
derivatives/rsfmri_qc/{subject_id}/temporal_filtering_qc.json
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_metrics/{subject_id}/alff.nii
derivatives/rsfmri_metrics/{subject_id}/falff.nii
derivatives/rsfmri_metrics/{subject_id}/alff_falff_result.json
derivatives/rsfmri_qc/{subject_id}/alff_falff_qc.json
derivatives/rsfmri_qc/{subject_id}/alff_falff_qc.md
reports/rsfmri/alff_falff_qc_summary.json
reports/rsfmri/alff_falff_qc_report.md
work/gpu/contracts/alff_falff_gpu_candidate_contract.json
work/dpabi/contracts/alff_falff_backend_contract.json
```

## ALFF Definition for MVP

ALFF is computed as the mean amplitude of the frequency-domain signal within the configured low-frequency band.

For this MVP:

- FFT is applied along the time axis.
- Amplitude is `abs(rfft(time_series))`.
- ALFF is mean amplitude over retained low-frequency bins.
- The DC component is excluded.

## fALFF Definition for MVP

fALFF is computed as:

```text
fALFF = mean amplitude in low-frequency band / mean amplitude across non-DC full spectrum
```

The denominator is computed from the nuisance-regressed residual signal before temporal filtering when available.

## Default Frequency Band

```text
low_hz = 0.01
high_hz = 0.08
```

## QC Metrics

- residual_input_exists
- filtered_input_exists
- alff_exists
- falff_exists
- input_shape
- filtered_shape
- output_shape
- tr
- low_hz
- high_hz
- nyquist_hz
- retained_frequency_bin_count
- alff_finite_fraction
- falff_finite_fraction
- alff_mean
- alff_std
- falff_mean
- falff_std
- falff_min
- falff_max
- alff_qc_status

## Safety Rules

- Only derivative nuisance-regressed and filtered functional input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not execute DPABI in this step.
- Do not execute GPU backend in this step.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
```

---

## 2. 创建 backend/app/tools/alff_falff.py

创建文件：

```text
backend/app/tools/alff_falff.py
```

目标：实现 Python NumPy ALFF/fALFF 计算和 QC。

提供函数：

```python
run_python_alff_falff_subject(
    subject_id: str,
    derivatives_dir: str,
    low_hz: float | None = None,
    high_hz: float | None = None,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict

write_alff_falff_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. residual input 必须是：

```text
derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii
```

2. filtered input 优先是：

```text
derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii
```

3. 如果 filtered input 不存在，可以直接从 residual input 用 low/high 频段计算 ALFF，但必须 warning：
   - `"filtered residual input missing; ALFF computed directly from residual spectrum"`
4. TR 获取顺序：
   - 函数参数 `tr`
   - temporal filtering QC 的 `tr`
   - slice timing QC 的 `tr`
   - fallback_tr
   - 如果仍缺失，则失败
5. frequency band 获取顺序：
   - 函数参数 low_hz / high_hz
   - temporal filtering QC 的 low_hz / high_hz
   - 默认 0.01 / 0.08
6. ALFF：
   - 对 filtered input 或 residual input 做 rFFT。
   - 保留 low/high band。
   - 排除 DC。
   - ALFF = mean(abs(spectrum[..., mask]), axis=-1)
7. fALFF：
   - 对 residual input 做 rFFT。
   - numerator = low-frequency mean amplitude。
   - denominator = non-DC full-spectrum mean amplitude。
   - fALFF = numerator / denominator。
   - denominator 为 0 的 voxel 输出 0。
8. 输出 3D NIfTI：
   - `derivatives/rsfmri_metrics/{subject_id}/alff.nii`
   - `derivatives/rsfmri_metrics/{subject_id}/falff.nii`
9. 保留 residual input 的 affine/header；但输出是 3D image。
10. 输出 result JSON、QC JSON、QC Markdown。
11. 不修改 input。
12. 不处理 rawdata。

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_residual_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    preferred = func_dir / f"resid_swra{subject_id}_bold.nii"
    if preferred.exists():
        return preferred

    candidates = sorted(func_dir.glob("resid_swr*.nii"))
    return candidates[0] if candidates else None


def _find_filtered_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    preferred = func_dir / f"filt_resid_swra{subject_id}_bold.nii"
    if preferred.exists():
        return preferred

    candidates = sorted(func_dir.glob("filt_resid_swr*.nii"))
    return candidates[0] if candidates else None


def _safe_func_path(path: Path, subject_id: str, derivatives_dir: str, prefix: str) -> bool:
    func_dir = (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
    ).resolve()

    try:
        path.resolve().relative_to(func_dir)
    except ValueError:
        return False

    return path.name.startswith(prefix) and path.name.endswith(".nii")


def _resolve_tr_and_band(
    subject_id: str,
    derivatives_dir: str,
    tr: float | None,
    fallback_tr: float | None,
    low_hz: float | None,
    high_hz: float | None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    filtering_qc = _read_json(
        Path(derivatives_dir) / "rsfmri_qc" / subject_id / "temporal_filtering_qc.json"
    )
    slice_qc = _read_json(
        Path(derivatives_dir) / "rsfmri_qc" / subject_id / "slice_timing_qc.json"
    )

    tr_source = None
    final_tr = tr

    if final_tr is not None:
        tr_source = "parameter"
    elif filtering_qc and filtering_qc.get("tr") is not None:
        final_tr = filtering_qc.get("tr")
        tr_source = "temporal_filtering_qc"
    elif slice_qc and slice_qc.get("tr") is not None:
        final_tr = slice_qc.get("tr")
        tr_source = "slice_timing_qc"
    elif fallback_tr is not None:
        final_tr = fallback_tr
        tr_source = "fallback_tr"
        warnings.append("Using fallback TR.")

    if final_tr is None:
        errors.append("TR is missing. Provide tr/fallback_tr or run upstream QC.")
    else:
        try:
            final_tr = float(final_tr)
            if final_tr <= 0:
                errors.append("TR must be positive.")
        except Exception:
            errors.append("TR must be numeric.")

    final_low = low_hz
    final_high = high_hz

    if final_low is None and filtering_qc and filtering_qc.get("low_hz") is not None:
        final_low = filtering_qc.get("low_hz")
    if final_high is None and filtering_qc and filtering_qc.get("high_hz") is not None:
        final_high = filtering_qc.get("high_hz")

    if final_low is None:
        final_low = 0.01
    if final_high is None:
        final_high = 0.08

    try:
        final_low = float(final_low)
        final_high = float(final_high)
        if final_low < 0 or final_high <= 0 or final_low >= final_high:
            errors.append(f"Invalid ALFF band: low_hz={final_low}, high_hz={final_high}")
    except Exception:
        errors.append("low_hz and high_hz must be numeric.")

    return {
        "tr": final_tr,
        "tr_source": tr_source,
        "low_hz": final_low,
        "high_hz": final_high,
    }, warnings, errors


def _write_qc_markdown(path: Path, qc: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# ALFF / fALFF QC: {qc.get('subject_id')}")
    lines.append("")
    lines.append(f"- OK: {qc.get('ok')}")
    lines.append(f"- Status: {qc.get('alff_qc_status')}")
    lines.append(f"- Residual input: `{qc.get('residual_input_nii')}`")
    lines.append(f"- Filtered input: `{qc.get('filtered_input_nii')}`")
    lines.append(f"- ALFF: `{qc.get('alff_file')}`")
    lines.append(f"- fALFF: `{qc.get('falff_file')}`")
    lines.append(f"- TR: {qc.get('tr')}")
    lines.append(f"- Band: {qc.get('low_hz')} - {qc.get('high_hz')} Hz")
    lines.append(f"- Retained frequency bins: {qc.get('retained_frequency_bin_count')}")
    lines.append(f"- ALFF mean/std: {qc.get('alff_mean')} / {qc.get('alff_std')}")
    lines.append(f"- fALFF mean/std: {qc.get('falff_mean')} / {qc.get('falff_std')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("ALFF/fALFF computation reads derivative files only and does not modify rawdata.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _failure(
    subject_id: str,
    result_json: Path,
    qc_json: Path,
    qc_md: Path,
    errors: list[str],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    warnings = warnings or []

    qc = {
        "ok": False,
        "node_id": "alff_falff_qc_subject",
        "backend": "python",
        "subject_id": subject_id,
        "alff_qc_status": "FAIL",
        "outputs": [str(qc_json), str(qc_md)],
        "warnings": warnings,
        "errors": errors,
    }

    result = {
        "ok": False,
        "node_id": "python_alff_falff_subject",
        "backend": "python",
        "subject_id": subject_id,
        "outputs": [str(result_json), str(qc_json), str(qc_md)],
        "warnings": warnings,
        "errors": errors,
    }

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_markdown(qc_md, qc)
    return result


def run_python_alff_falff_subject(
    subject_id: str,
    derivatives_dir: str,
    low_hz: float | None = None,
    high_hz: float | None = None,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    metrics_dir = Path(derivatives_dir) / "rsfmri_metrics" / subject_id
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    metrics_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    result_json = metrics_dir / "alff_falff_result.json"
    qc_json = qc_dir / "alff_falff_qc.json"
    qc_md = qc_dir / "alff_falff_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    residual_path = _find_residual_functional(subject_id, derivatives_dir)
    if not residual_path:
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"No residual functional input found for subject {subject_id}."],
        )

    if not _safe_func_path(residual_path, subject_id, derivatives_dir, "resid_swr"):
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"Unsafe residual functional input: {residual_path}"],
        )

    filtered_path = _find_filtered_functional(subject_id, derivatives_dir)
    if filtered_path and not _safe_func_path(filtered_path, subject_id, derivatives_dir, "filt_resid_swr"):
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"Unsafe filtered functional input: {filtered_path}"],
        )

    params, param_warnings, param_errors = _resolve_tr_and_band(
        subject_id=subject_id,
        derivatives_dir=derivatives_dir,
        tr=tr,
        fallback_tr=fallback_tr,
        low_hz=low_hz,
        high_hz=high_hz,
    )
    warnings.extend(param_warnings)
    errors.extend(param_errors)

    if errors:
        return _failure(subject_id, result_json, qc_json, qc_md, errors, warnings)

    final_tr = float(params["tr"])
    final_low = float(params["low_hz"])
    final_high = float(params["high_hz"])

    try:
        residual_img = nib.load(str(residual_path))
        residual_data = residual_img.get_fdata(dtype="float32")

        if residual_data.ndim != 4:
            raise ValueError(f"Residual input must be 4D. Shape was: {residual_data.shape}")

        if filtered_path:
            alff_img = nib.load(str(filtered_path))
            alff_input_data = alff_img.get_fdata(dtype="float32")
            filtered_input_used = str(filtered_path)
        else:
            alff_input_data = residual_data
            filtered_input_used = None
            warnings.append("filtered residual input missing; ALFF computed directly from residual spectrum")

        if list(alff_input_data.shape) != list(residual_data.shape):
            raise ValueError(
                f"Filtered input shape {list(alff_input_data.shape)} does not match residual shape {list(residual_data.shape)}."
            )

        n_time = int(residual_data.shape[3])
        if n_time < 3:
            raise ValueError(f"ALFF/fALFF requires at least 3 timepoints. Got {n_time}.")

        nyquist = 1.0 / (2.0 * final_tr)
        if final_high >= nyquist:
            warnings.append(
                f"high_hz={final_high} is >= Nyquist={nyquist}. Clipping high_hz to Nyquist."
            )
            final_high = nyquist

        freqs = np.fft.rfftfreq(n_time, d=final_tr)
        non_dc_mask = freqs > 0
        band_mask = (freqs >= final_low) & (freqs <= final_high) & non_dc_mask

        retained_bins = int(np.count_nonzero(band_mask))
        if retained_bins == 0:
            raise ValueError(
                f"No ALFF frequency bins retained for band {final_low}-{final_high} Hz with TR={final_tr} and n_time={n_time}."
            )

        alff_spectrum = np.fft.rfft(alff_input_data, axis=3)
        residual_spectrum = np.fft.rfft(residual_data, axis=3)

        low_amp_for_alff = np.abs(alff_spectrum[..., band_mask])
        alff_map = np.mean(low_amp_for_alff, axis=3).astype("float32")

        residual_amp = np.abs(residual_spectrum)
        numerator = np.mean(residual_amp[..., band_mask], axis=3)
        denominator = np.mean(residual_amp[..., non_dc_mask], axis=3)

        with np.errstate(divide="ignore", invalid="ignore"):
            falff_map = np.where(denominator > 0, numerator / denominator, 0.0).astype("float32")

        alff_file = metrics_dir / "alff.nii"
        falff_file = metrics_dir / "falff.nii"

        header_3d = residual_img.header.copy()
        try:
            header_3d.set_data_shape(alff_map.shape)
        except Exception:
            pass

        nib.save(nib.Nifti1Image(alff_map, affine=residual_img.affine, header=header_3d), str(alff_file))
        nib.save(nib.Nifti1Image(falff_map, affine=residual_img.affine, header=header_3d), str(falff_file))

        alff_finite = np.isfinite(alff_map)
        falff_finite = np.isfinite(falff_map)

        alff_finite_fraction = float(np.count_nonzero(alff_finite) / alff_map.size) if alff_map.size else 0.0
        falff_finite_fraction = float(np.count_nonzero(falff_finite) / falff_map.size) if falff_map.size else 0.0

        falff_min = float(np.nanmin(falff_map)) if falff_map.size else None
        falff_max = float(np.nanmax(falff_map)) if falff_map.size else None

        status = "PASS"
        if alff_finite_fraction < 0.95 or falff_finite_fraction < 0.95:
            status = "WARNING"
            warnings.append("ALFF/fALFF finite fraction below 0.95.")
        if falff_min is not None and falff_min < -1e-6:
            status = "WARNING"
            warnings.append(f"fALFF minimum is negative: {falff_min}")
        if falff_max is not None and falff_max > 1.5:
            status = "WARNING"
            warnings.append(f"fALFF maximum is unusually high: {falff_max}")

        qc = {
            "ok": True,
            "node_id": "alff_falff_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "residual_input_nii": str(residual_path),
            "filtered_input_nii": filtered_input_used,
            "alff_file": str(alff_file),
            "falff_file": str(falff_file),
            "input_shape": list(residual_data.shape),
            "filtered_shape": list(alff_input_data.shape),
            "output_shape": list(alff_map.shape),
            "tr": final_tr,
            "tr_source": params.get("tr_source"),
            "low_hz": final_low,
            "high_hz": final_high,
            "nyquist_hz": nyquist,
            "frequency_bin_count": int(len(freqs)),
            "retained_frequency_bin_count": retained_bins,
            "alff_finite_fraction": alff_finite_fraction,
            "falff_finite_fraction": falff_finite_fraction,
            "alff_mean": float(np.nanmean(alff_map)),
            "alff_std": float(np.nanstd(alff_map)),
            "falff_mean": float(np.nanmean(falff_map)),
            "falff_std": float(np.nanstd(falff_map)),
            "falff_min": falff_min,
            "falff_max": falff_max,
            "alff_qc_status": status,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [],
        }

        result = {
            "ok": True,
            "node_id": "python_alff_falff_subject",
            "backend": "python",
            "subject_id": subject_id,
            "residual_input_nii": str(residual_path),
            "filtered_input_nii": filtered_input_used,
            "alff_file": str(alff_file),
            "falff_file": str(falff_file),
            "qc": qc,
            "outputs": [str(alff_file), str(falff_file), str(result_json), str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [],
        }

    except Exception as exc:
        return _failure(subject_id, result_json, qc_json, qc_md, [str(exc)], warnings)

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_markdown(qc_md, qc)
    return result


def write_alff_falff_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/alff_falff_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid ALFF/fALFF QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("alff_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("alff_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("alff_qc_status") == "FAIL")

    alff_means = [float(item["alff_mean"]) for item in subjects if item.get("alff_mean") is not None]
    falff_means = [float(item["falff_mean"]) for item in subjects if item.get("falff_mean") is not None]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "alff_falff_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_alff_mean": float(mean(alff_means)) if alff_means else None,
        "mean_falff_mean": float(mean(falff_means)) if falff_means else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "alff_falff_qc_summary.json"
    report_path = report_out / "alff_falff_qc_report.md"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# rs-fMRI ALFF / fALFF QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean ALFF mean: {summary['mean_alff_mean']}")
    lines.append(f"- Mean fALFF mean: {summary['mean_falff_mean']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | ALFF Mean | fALFF Mean | fALFF Max | Band Hz |")
    lines.append("|---|---|---:|---:|---:|---|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('alff_qc_status')} | "
            f"{item.get('alff_mean')} | {item.get('falff_mean')} | "
            f"{item.get('falff_max')} | {item.get('low_hz')}-{item.get('high_hz')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative ALFF/fALFF QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "alff_falff_qc_dataset_report",
        "backend": "python",
        "outputs": [str(summary_path), str(report_path)],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_pass": pass_count,
            "subjects_warning": warning_count,
            "subjects_fail": fail_count,
        },
        "warnings": warnings,
        "errors": errors,
    }
```

---

## 3. 创建 backend/app/tools/gpu_alff_contract.py

创建文件：

```text
backend/app/tools/gpu_alff_contract.py
```

目标：生成 GPU candidate backend contract，但不执行 GPU。

提供函数：

```python
write_alff_falff_gpu_candidate_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/gpu/contracts/alff_falff_gpu_candidate_contract.json
```

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_alff_falff_gpu_candidate_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "gpu" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "alff_falff_gpu_candidate_contract.json"

    payload = {
        "ok": True,
        "node_id": "alff_falff_gpu_candidate_contract",
        "backend": "python",
        "backend_id": "gpu_candidate_alff_falff",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "gpu_executed": False,
        "required_approval": True,
        "description": "GPU candidate contract for future ALFF/fALFF acceleration. This step does not execute GPU code.",
        "candidate_backends": [
            {
                "name": "cupy_fft",
                "language": "python",
                "requirement": "cupy",
                "notes": "Potential drop-in replacement for NumPy FFT when CUDA is available."
            },
            {
                "name": "torch_fft",
                "language": "python",
                "requirement": "torch with CUDA",
                "notes": "Potential backend for batched voxel-wise FFT."
            },
            {
                "name": "matlab_gpuarray_fft",
                "language": "matlab",
                "requirement": "Parallel Computing Toolbox",
                "notes": "Potential MATLAB GPU backend for FFT-based metrics."
            }
        ],
        "planned_inputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii",
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii"
        ],
        "planned_outputs": [
            "outputs/derivatives/rsfmri_metrics/{subject_id}/alff_gpu.nii",
            "outputs/derivatives/rsfmri_metrics/{subject_id}/falff_gpu.nii"
        ],
        "safety": {
            "gpu_executed": False,
            "rawdata_modified": False,
            "files_deleted": False
        },
        "outputs": [str(path)],
        "warnings": [
            "This is a contract only. GPU execution is intentionally not implemented in Step 44."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 4. 创建 backend/app/tools/dpabi_alff_contract.py

创建文件：

```text
backend/app/tools/dpabi_alff_contract.py
```

目标：生成 DPABI ALFF/fALFF backend contract，但不执行 DPABI。

提供函数：

```python
write_dpabi_alff_falff_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/dpabi/contracts/alff_falff_backend_contract.json
```

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_dpabi_alff_falff_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "alff_falff_backend_contract.json"

    payload = {
        "ok": True,
        "node_id": "dpabi_alff_falff_contract",
        "backend": "python",
        "backend_id": "dpabi_alff_falff",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "required_approval": True,
        "description": "DPABI ALFF/fALFF backend contract. This step does not execute DPABI.",
        "planned_inputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii",
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii"
        ],
        "planned_outputs": [
            "outputs/derivatives/rsfmri_metrics/{subject_id}/dpabi_alff.nii",
            "outputs/derivatives/rsfmri_metrics/{subject_id}/dpabi_falff.nii",
            "outputs/logs/{subject_id}_dpabi_alff_falff.log"
        ],
        "parameters": {
            "low_hz": 0.01,
            "high_hz": 0.08,
            "tr_source": "temporal_filtering_qc_or_user_parameter"
        },
        "blocked_functions": [
            "DPARSF_run",
            "DPARSFA_run"
        ],
        "allowed_future_mode": "single_function_wrapper_only",
        "safety": {
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dparsfa_run_executed": False,
            "dpabi_gui_called": False,
            "rawdata_modified": False,
            "files_deleted": False
        },
        "outputs": [str(path)],
        "warnings": [
            "This is a contract only. DPABI ALFF/fALFF execution is intentionally not implemented in Step 44."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 5. 创建 backend/app/tools/alff_falff_runner.py

创建文件：

```text
backend/app/tools/alff_falff_runner.py
```

目标：包装 Python ALFF/fALFF、GPU contract 和 DPABI contract mode。

提供函数：

```python
run_alff_falff_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    low_hz: float | None = None,
    high_hz: float | None = None,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict
```

支持 backend：

- `python`
- `gpu_contract`
- `dpabi_contract`

参考实现：

```python
from __future__ import annotations

from typing import Any

from backend.app.tools.alff_falff import run_python_alff_falff_subject
from backend.app.tools.gpu_alff_contract import write_alff_falff_gpu_candidate_contract
from backend.app.tools.dpabi_alff_contract import write_dpabi_alff_falff_contract


def run_alff_falff_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    low_hz: float | None = None,
    high_hz: float | None = None,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict[str, Any]:
    if backend == "gpu_contract":
        contract = write_alff_falff_gpu_candidate_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend == "dpabi_contract":
        contract = write_dpabi_alff_falff_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend != "python":
        return {
            "ok": False,
            "node_id": "alff_falff_subject",
            "backend": backend,
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsupported ALFF/fALFF backend: {backend}"],
        }

    result = run_python_alff_falff_subject(
        subject_id=subject_id,
        derivatives_dir=derivatives_dir,
        low_hz=low_hz,
        high_hz=high_hz,
        tr=tr,
        fallback_tr=fallback_tr,
    )

    result["node_id"] = "alff_falff_subject"
    return result
```

---

## 6. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
alff_falff_subject
alff_falff_qc_dataset_report
alff_falff_gpu_candidate_contract
dpabi_alff_falff_contract
```

新增导入：

```python
from backend.app.tools.alff_falff_runner import run_alff_falff_subject
from backend.app.tools.alff_falff import write_alff_falff_dataset_report
from backend.app.tools.gpu_alff_contract import write_alff_falff_gpu_candidate_contract
from backend.app.tools.dpabi_alff_contract import write_dpabi_alff_falff_contract
```

新增 runner：

```python
def run_alff_falff_subject_node(
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

    result = run_alff_falff_subject(
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        backend=node.params.get("backend", "python"),
        low_hz=node.params.get("low_hz"),
        high_hz=node.params.get("high_hz"),
        tr=node.params.get("tr"),
        fallback_tr=node.params.get("fallback_tr"),
    )

    result["node_id"] = node.id
    return result


def run_alff_falff_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_alff_falff_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_alff_falff_gpu_candidate_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_alff_falff_gpu_candidate_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_alff_falff_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_alff_falff_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"alff_falff_subject": run_alff_falff_subject_node,
"alff_falff_qc_dataset_report": run_alff_falff_qc_dataset_report_node,
"alff_falff_gpu_candidate_contract": run_alff_falff_gpu_candidate_contract_node,
"dpabi_alff_falff_contract": run_dpabi_alff_falff_contract_node,
```

---

## 7. 创建 examples/pipeline_rsfmri_alff_falff.yaml

创建文件：

```text
examples/pipeline_rsfmri_alff_falff.yaml
```

内容：

```yaml
pipeline_id: rsfmri_alff_falff_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run Python ALFF/fALFF on filtered synthetic derivatives and generate GPU/DPABI backend contracts."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_alff_falff_001"
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

  - id: environment_check
    name: Environment Check
    agent: system
    backend: matlab
    depends_on: []
    inputs: []
    outputs:
      - "./work/environment_check.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: spm_slice_timing_subject
    name: Approved SPM Slice Timing
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - data_inspection
      - environment_check
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs: []
    params:
      approved: false
      tr: null
      slice_order: null
      reference_slice: null
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: spm_realign_subject
    name: Approved SPM Realignment From Slice Timing Output
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - spm_slice_timing_subject
    inputs: []
    outputs: []
    params:
      approved: false
      use_slice_timing_output: true
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: motion_qc_subject
    name: Motion QC
    agent: qc-runner
    backend: python
    depends_on:
      - spm_realign_subject
    inputs: []
    outputs: []
    params:
      fd_threshold: 0.5
      head_radius_mm: 50.0
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: spm_coregister_subject
    name: Approved SPM Coregistration
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - spm_realign_subject
    inputs: []
    outputs: []
    params:
      approved: false
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: spm_segment_subject
    name: Approved SPM Segmentation
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - spm_coregister_subject
    inputs: []
    outputs: []
    params:
      approved: false
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: spm_normalize_subject
    name: Approved SPM Normalization
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - spm_segment_subject
    inputs: []
    outputs: []
    params:
      approved: false
      voxel_size: [3.0, 3.0, 3.0]
      bounding_box:
        - [-90.0, -126.0, -72.0]
        - [90.0, 90.0, 108.0]
      normalize_mean: true
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: spm_smooth_subject
    name: Approved SPM Smoothing
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - spm_normalize_subject
    inputs: []
    outputs: []
    params:
      approved: false
      fwhm: [6.0, 6.0, 6.0]
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: nuisance_regression_subject
    name: Python Nuisance Regression
    agent: regression-runner
    backend: python
    depends_on:
      - spm_smooth_subject
      - motion_qc_subject
      - spm_segment_subject
    inputs: []
    outputs: []
    params:
      backend: python
      model: friston24
      include_intercept: true
      include_linear_trend: true
      include_global_signal: false
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: temporal_filtering_subject
    name: Python Temporal Filtering
    agent: filtering-runner
    backend: python
    depends_on:
      - nuisance_regression_subject
    inputs: []
    outputs: []
    params:
      backend: python
      low_hz: 0.01
      high_hz: 0.08
      tr: null
      fallback_tr: 2.0
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: alff_falff_subject
    name: Python ALFF fALFF
    agent: metrics-runner
    backend: python
    depends_on:
      - temporal_filtering_subject
    inputs: []
    outputs: []
    params:
      backend: python
      low_hz: null
      high_hz: null
      tr: null
      fallback_tr: 2.0
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: alff_falff_gpu_candidate_contract
    name: ALFF fALFF GPU Candidate Contract
    agent: contract-runner
    backend: python
    depends_on:
      - alff_falff_subject
    inputs: []
    outputs:
      - "./work/gpu/contracts/alff_falff_gpu_candidate_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_alff_falff_contract
    name: DPABI ALFF fALFF Backend Contract
    agent: contract-runner
    backend: python
    depends_on:
      - alff_falff_subject
    inputs: []
    outputs:
      - "./work/dpabi/contracts/alff_falff_backend_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: alff_falff_qc_dataset_report
    name: ALFF fALFF QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - alff_falff_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/alff_falff_qc_summary.json"
      - "./reports/rsfmri/alff_falff_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。  
Python ALFF/fALFF 本身不需要 MATLAB approval，但它依赖前面的 SPM derivative 输出。

---

## 8. 创建 backend/app/tools/run_rsfmri_alff_falff_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_alff_falff_cli.py
```

内容：

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def _make_approved_pipeline_copy(source: Path, target: Path) -> Path:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
            "spm_segment_subject",
            "spm_normalize_subject",
            "spm_smooth_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_alff_falff.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("outputs/work/rsfmri/approved_pipeline_alff_falff.yaml"),
        )

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
```

---

## 9. 修改 backend/app/api/models.py

新增 request model：

```python
class RsfmriAlffFalffRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_alff_falff.yaml")
    approved: bool = Field(default=False)
```

---

## 10. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/alff-falff/run
GET  /api/rsfmri/alff-falff
```

新增导入：

```python
from backend.app.api.models import RsfmriAlffFalffRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_alff_falff_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
            "spm_segment_subject",
            "spm_normalize_subject",
            "spm_smooth_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target
```

新增路由：

```python
@router.post("/api/rsfmri/alff-falff/run")
def api_run_rsfmri_alff_falff(
    request: RsfmriAlffFalffRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="ALFF/fALFF pipeline requires approved=true because it depends on approved SPM preprocessing derivatives.",
        )

    try:
        approved_pipeline = _make_alff_falff_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("outputs/work/rsfmri/approved_pipeline_alff_falff.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/alff-falff")
def api_get_rsfmri_alff_falff() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")
    gpu_contract_base = Path("work") / "gpu" / "contracts"
    dpabi_contract_base = Path("work") / "dpabi" / "contracts"

    subject_alff_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/alff_falff_qc.json")):
        subject_alff_qc.append(_read_json_if_exists(path))

    subject_results = []
    for path in sorted((derivatives_base / "rsfmri_metrics").glob("*/alff_falff_result.json")):
        subject_results.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "alff_falff_qc_summary": _read_json_if_exists(report_base / "alff_falff_qc_summary.json"),
        "alff_falff_qc_report": _read_text_if_exists(report_base / "alff_falff_qc_report.md"),
        "subject_alff_falff_qc": subject_alff_qc,
        "subject_alff_falff_results": subject_results,
        "gpu_candidate_contract": _read_json_if_exists(gpu_contract_base / "alff_falff_gpu_candidate_contract.json"),
        "dpabi_backend_contract": _read_json_if_exists(dpabi_contract_base / "alff_falff_backend_contract.json"),
    }
```

---

## 11. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriAlffFalff(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/alff-falff/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriAlffFalff(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/alff-falff"
  );
}
```

---

## 12. 创建 frontend/src/components/RsfmriAlffFalffPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriAlffFalffPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriAlffFalff,
  runRsfmriAlffFalff
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriAlffFalffPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 Python ALFF/fALFF？这只处理 synthetic derivatives，不会修改 rawdata，不会执行 DPABI 或 GPU。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriAlffFalff(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_alff_falff.yaml",
        approved: true
      });
      setResult(response);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await getRsfmriAlffFalff(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.alff_falff_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Python ALFF/fALFF
        </button>
        <button onClick={handleLoad}>加载 ALFF/fALFF 结果</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(summary?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(summary?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>WARNING</span>
          <strong>{String(summary?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>FAIL</span>
          <strong>{String(summary?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Mean fALFF</span>
          <strong>
            {summary?.mean_falff_mean == null
              ? "-"
              : Number(summary.mean_falff_mean).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>ALFF/fALFF QC Summary</h3>
      <JsonBlock value={loaded?.alff_falff_qc_summary} emptyText="暂无 ALFF/fALFF QC summary" />

      <h3>Subject ALFF/fALFF QC</h3>
      <JsonBlock value={loaded?.subject_alff_falff_qc} emptyText="暂无 subject ALFF/fALFF QC" />

      <h3>Subject ALFF/fALFF Results</h3>
      <JsonBlock value={loaded?.subject_alff_falff_results} emptyText="暂无 subject ALFF/fALFF results" />

      <h3>GPU Candidate Contract</h3>
      <JsonBlock value={loaded?.gpu_candidate_contract} emptyText="暂无 GPU candidate contract" />

      <h3>DPABI Backend Contract</h3>
      <JsonBlock value={loaded?.dpabi_backend_contract} emptyText="暂无 DPABI backend contract" />

      <h3>ALFF/fALFF QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.alff_falff_qc_report === "string"
            ? loaded.alff_falff_qc_report
            : null
        }
        emptyText="暂无 ALFF/fALFF QC report"
      />
    </div>
  );
}
```

---

## 13. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriAlffFalffPanel } from "./components/RsfmriAlffFalffPanel";
```

在 `rs-fMRI Temporal Filtering` 后新增 Section：

```tsx
<Section
  title="rs-fMRI ALFF / fALFF"
  description="计算 ALFF/fALFF 指标图，并生成 GPU candidate 与 DPABI 后端 contract。"
>
  <RsfmriAlffFalffPanel baseUrl={baseUrl} />
</Section>
```

---

## 14. 新增轻量测试

创建文件：

```text
tests/unit/test_alff_falff.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.alff_falff import run_python_alff_falff_subject


def test_python_alff_falff_outputs_metric_maps(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    qc_dir = derivatives / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True)
    qc_dir.mkdir(parents=True)

    residual = func_dir / "resid_swrasub-001_bold.nii"
    filtered = func_dir / "filt_resid_swrasub-001_bold.nii"

    tr = 2.0
    n_time = 32
    t = np.arange(n_time) * tr

    low_signal = np.sin(2 * np.pi * 0.03 * t)
    high_signal = 0.5 * np.sin(2 * np.pi * 0.2 * t)
    residual_signal = low_signal + high_signal
    filtered_signal = low_signal

    residual_data = np.zeros((3, 3, 3, n_time), dtype=np.float32)
    filtered_data = np.zeros((3, 3, 3, n_time), dtype=np.float32)
    residual_data[:] = residual_signal.astype(np.float32)
    filtered_data[:] = filtered_signal.astype(np.float32)

    nib.save(nib.Nifti1Image(residual_data, affine=np.eye(4)), str(residual))
    nib.save(nib.Nifti1Image(filtered_data, affine=np.eye(4)), str(filtered))

    (qc_dir / "temporal_filtering_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": subject_id,
            "tr": tr,
            "low_hz": 0.01,
            "high_hz": 0.08,
            "filtering_qc_status": "PASS",
        }),
        encoding="utf-8",
    )

    result = run_python_alff_falff_subject(
        subject_id=subject_id,
        derivatives_dir=str(derivatives),
    )

    assert result["ok"] is True

    alff = derivatives / "rsfmri_metrics" / subject_id / "alff.nii"
    falff = derivatives / "rsfmri_metrics" / subject_id / "falff.nii"
    assert alff.exists()
    assert falff.exists()

    qc_path = qc_dir / "alff_falff_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == subject_id
    assert payload["alff_qc_status"] in {"PASS", "WARNING"}
    assert payload["retained_frequency_bin_count"] > 0
    assert payload["falff_mean"] >= 0
```

---

## 15. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/alff-falff")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 16. 更新 README.md

追加第四十四步说明：

```markdown
## Step 44: ALFF / fALFF and QC

This step implements Python NumPy ALFF/fALFF computation.

It supports:

- derivative nuisance-regressed functional input
- derivative filtered functional input
- TR from temporal filtering QC or slice timing QC
- default band-pass 0.01-0.08 Hz
- ALFF map output
- fALFF map output
- subject-level ALFF/fALFF QC
- dataset-level ALFF/fALFF QC report
- GPU candidate backend contract without GPU execution
- DPABI backend contract without DPABI execution
- frontend visualization

It does not execute DPABI or GPU code.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_alff_falff_cli
```

This should fail safely because upstream SPM steps are not approved.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_alff_falff_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_alff_falff.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_metrics/sub-001/alff.nii
derivatives/rsfmri_metrics/sub-001/falff.nii
derivatives/rsfmri_metrics/sub-001/alff_falff_result.json
derivatives/rsfmri_qc/sub-001/alff_falff_qc.json
derivatives/rsfmri_qc/sub-001/alff_falff_qc.md
reports/rsfmri/alff_falff_qc_summary.json
reports/rsfmri/alff_falff_qc_report.md
work/gpu/contracts/alff_falff_gpu_candidate_contract.json
work/dpabi/contracts/alff_falff_backend_contract.json
work/pipeline_runs/run_rsfmri_alff_falff_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/alff-falff
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/alff-falff/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_alff_falff.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI ALFF / fALFF
```

### Safety

This step:

- only processes derivative residual and filtered functional inputs
- obtains TR from temporal filtering QC, slice timing QC, or explicit fallback
- does not modify rawdata
- does not run DPABI
- does not run GPU
- only creates GPU and DPABI backend contracts
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing
```

---

## 17. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/alff_falff_qc_spec.md
backend/app/tools/alff_falff.py
backend/app/tools/gpu_alff_contract.py
backend/app/tools/dpabi_alff_contract.py
backend/app/tools/alff_falff_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_alff_falff.yaml
backend/app/tools/run_rsfmri_alff_falff_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriAlffFalffPanel.tsx
frontend/src/App.tsx
tests/unit/test_alff_falff.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_alff_falff_cli
```

应该安全失败，不应启动 SPM / DPABI / GPU。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_alff_falff_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_alff_falff.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_metrics/sub-001/alff.nii
derivatives/rsfmri_metrics/sub-001/falff.nii
derivatives/rsfmri_qc/sub-001/alff_falff_qc.json
reports/rsfmri/alff_falff_qc_summary.json
work/gpu/contracts/alff_falff_gpu_candidate_contract.json
work/dpabi/contracts/alff_falff_backend_contract.json
```

ALFF/fALFF QC JSON 必须包含：

```json
{
  "node_id": "alff_falff_qc_subject",
  "subject_id": "sub-001",
  "alff_qc_status": "PASS",
  "tr": 2.0,
  "low_hz": 0.01,
  "high_hz": 0.08,
  "retained_frequency_bin_count": 0,
  "alff_mean": 0,
  "falff_mean": 0
}
```

实际数值根据 synthetic 数据、TR 和频率 bins 决定。

运行测试：

```bash
python -m pytest tests/unit/test_alff_falff.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/alff-falff

curl -X POST http://127.0.0.1:8000/api/rsfmri/alff-falff/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/alff-falff/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI ALFF / fALFF 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 ALFF/fALFF 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean fALFF。
8. 显示 ALFF/fALFF QC summary JSON。
9. 显示 subject ALFF/fALFF QC JSON。
10. 显示 subject ALFF/fALFF result JSON。
11. 显示 GPU candidate contract。
12. 显示 DPABI backend contract。
13. 显示 ALFF/fALFF QC Markdown report。
14. 不修改 rawdata。
15. 不运行 DPABI。
16. 不运行 GPU。
17. 不调用 DPARSF_run / DPARSFA_run。
18. 不执行完整 preprocessing。

---

## 18. 重要限制

本步骤只做 Python NumPy ALFF/fALFF、ALFF/fALFF QC、GPU candidate contract、DPABI ALFF backend contract。

不要实现：

- ReHo
- functional connectivity
- group-level statistics
- 真实 DPABI ALFF/fALFF 执行
- 真实 GPU 执行
- 真实医学影像处理
- DPABI 全流程执行
- DPARSF_run 自动执行
- DPARSFA_run 自动执行
- DPABI GUI 自动化
- rawdata 修改
- 文件删除

完成后请总结：

1. 新增了哪些文件
2. 修改了哪些文件
3. ALFF 如何计算
4. fALFF 如何计算
5. TR 和频段如何获取
6. GPU candidate backend contract 为什么只生成不执行
7. DPABI ALFF backend contract 为什么只生成不执行
8. 输出哪些 derivatives、metrics 和 reports
9. 为什么本步骤仍然不是完整 preprocessing
10. 下一步如何实现 ReHo 计算与 ReHo QC

```
这一步给 rs-fMRI 后处理加上了低频振幅指标计算。用 NumPy FFT 对 nuisance regression 和 temporal filtering 产出的功能像做频谱分析，ALFF 是低频段（0.01-0.08 Hz，排除直流分量）振幅的均值，fALFF 是低频振幅除以全频段非直流振幅的比值，输出两张 3D 指标图 `alff.nii` 和 `falff.nii`。TR 自动从 temporal_filtering_qc.json → slice_timing_qc.json → fallback 三级获取。同时生成了 GPU candidate contract（列出未来可用的 CuPy/Torch/MATLAB GPU 方案）和 DPABI ALFF contract，但都不执行。Pipeline 现在 16 个节点，从原始 BOLD 一路跑到了 ALFF/fALFF 指标图。
```
