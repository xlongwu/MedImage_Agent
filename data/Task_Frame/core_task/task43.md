# 第四十三步 Prompt：Temporal Filtering + Filtering QC 闭环

```text
你是我的工程搭建助手。前四十二步已经完成：

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

现在开始第四十三步。

第四十三步目标：实现 “Temporal Filtering + Filtering QC 闭环”。

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

但还缺少 rs-fMRI 后处理中常见的时间滤波步骤。  
本步骤要继续深入 rs-fMRI 核心预处理，实现：

nuisance-regressed functional image
→ temporal band-pass filtering
→ filtered residual functional image
→ filtering QC
→ subject-level filtering report
→ dataset-level filtering QC report

本步骤要实现：

1. temporal filtering specification。
2. Python temporal filtering backend。
3. 从 slice timing QC 或参数中读取 TR。
4. 对 `resid_swr*.nii` 执行 band-pass filtering。
5. 默认频段：
   - low_hz = 0.01
   - high_hz = 0.08
6. 使用 FFT mask 实现轻量 band-pass，不依赖 scipy。
7. 输出 filtered functional：
   - `filt_resid_swr*.nii`
8. 输出 temporal filtering result JSON。
9. 生成 filtering QC：
   - input exists
   - output exists
   - TR
   - low_hz / high_hz
   - Nyquist frequency
   - frequency band validity
   - input/output shape consistency
   - finite fraction
   - input temporal std
   - filtered temporal std
   - variance ratio
   - retained frequency bins
   - filtering_qc_status
10. 生成 subject-level filtering QC JSON / Markdown。
11. 生成 dataset-level filtering QC summary / Markdown report。
12. 生成 DPABI temporal filtering backend contract，但本步骤不执行 DPABI。
13. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC → Normalization → Normalization QC → Smoothing → Smoothing QC → Confound Matrix → Python Nuisance Regression → Regression QC → Temporal Filtering → Filtering QC
14. 后端 API 暴露 temporal filtering 结果。
15. 前端新增 rs-fMRI Temporal Filtering 面板。
16. 增加轻量 unit test。
17. 更新 README。

本步骤允许执行 Python temporal filtering，但必须满足：

- 只处理 synthetic BIDS-like derivative 数据。
- temporal filtering 输入必须来自 derivatives 中的 nuisance regression 输出。
- TR 必须来自 subject slice timing QC 或显式参数 fallback。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- ALFF / fALFF / ReHo
- 真实 DPABI temporal filtering 执行
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：Python temporal filtering、Filtering QC、DPABI filtering backend contract。

---

## 1. 创建 specs/temporal_filtering_qc_spec.md

创建文件：

```text
specs/temporal_filtering_qc_spec.md
```

内容：

```markdown
# Temporal Filtering and Filtering QC Specification

This document defines the MVP temporal filtering stage for rs-fMRI preprocessing.

## Goals

The goal is to apply temporal band-pass filtering to nuisance-regressed rs-fMRI derivatives and compute lightweight filtering QC metrics.

This step prepares cleaned and filtered rs-fMRI data for ALFF, fALFF, ReHo, and functional connectivity analysis.

## Scope

Supported in this step:

- synthetic derivative input only
- Python FFT-based temporal band-pass filtering
- TR discovery from slice timing QC
- explicit TR fallback
- subject-level filtering QC JSON / Markdown
- dataset-level filtering QC summary / report
- DPABI temporal filtering backend contract generation without execution
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- ALFF / fALFF / ReHo
- rawdata modification
- source modification in SPM / DPABI
- file deletion

## Inputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii
derivatives/rsfmri_preproc/{subject_id}/func/temporal_filtering_result.json
derivatives/rsfmri_qc/{subject_id}/temporal_filtering_qc.json
derivatives/rsfmri_qc/{subject_id}/temporal_filtering_qc.md
reports/rsfmri/temporal_filtering_qc_summary.json
reports/rsfmri/temporal_filtering_qc_report.md
work/dpabi/contracts/temporal_filtering_backend_contract.json
```

## Filtering Parameters

Default values:

- low_hz: 0.01
- high_hz: 0.08
- tr: read from slice timing QC, fallback to 2.0 only if explicitly configured

## Filtering QC Metrics

- input_exists
- output_exists
- input_shape
- output_shape
- tr
- low_hz
- high_hz
- nyquist_hz
- frequency_bin_count
- retained_frequency_bin_count
- retained_frequency_fraction
- finite_fraction
- input_temporal_std_mean
- filtered_temporal_std_mean
- variance_ratio
- filtering_qc_status

## Safety Rules

- Only derivative nuisance-regressed functional input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not execute DPABI in this step.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
```

---

## 2. 创建 backend/app/tools/temporal_filtering.py

创建文件：

```text
backend/app/tools/temporal_filtering.py
```

目标：实现 Python FFT-based temporal band-pass filtering 和 QC。

提供函数：

```python
run_python_temporal_filter_subject(
    subject_id: str,
    derivatives_dir: str,
    low_hz: float = 0.01,
    high_hz: float = 0.08,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict

write_temporal_filtering_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. 输入必须是：

```text
derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii
```

2. 输出为同目录：

```text
filt_resid_swr*.nii
```

3. TR 获取顺序：
   - 函数参数 `tr`
   - `derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json` 中的 `tr`
   - `fallback_tr`
   - 如果仍缺失，则失败
4. band-pass filtering：
   - 使用 numpy FFT。
   - 对最后一维 time 进行 rFFT。
   - 使用 `np.fft.rfftfreq(n_time, d=tr)` 构造频率。
   - 保留 `low_hz <= freq <= high_hz`。
   - 始终保留 DC 分量由参数决定：本步骤默认不保留 DC，因为 nuisance regression 已包含 intercept。
   - 反变换回 time domain。
5. 输入输出 shape 必须一致。
6. 保留 affine/header。
7. 输出：
   - `temporal_filtering_result.json`
   - `temporal_filtering_qc.json`
   - `temporal_filtering_qc.md`
8. QC：
   - finite fraction
   - input/output shape
   - TR
   - frequency band validity
   - retained frequency bins
   - temporal std ratio
9. 不修改 input。
10. 不处理 rawdata。

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


def _safe_residual_input(path: Path, subject_id: str, derivatives_dir: str) -> bool:
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

    return path.name.startswith("resid_swr") and path.name.endswith(".nii")


def _resolve_tr(
    subject_id: str,
    derivatives_dir: str,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> tuple[float | None, list[str], list[str], str | None]:
    warnings: list[str] = []
    errors: list[str] = []

    if tr is not None:
        try:
            parsed = float(tr)
            if parsed <= 0:
                errors.append("TR must be positive.")
                return None, warnings, errors, "parameter"
            return parsed, warnings, errors, "parameter"
        except Exception:
            errors.append("TR parameter must be numeric.")
            return None, warnings, errors, "parameter"

    qc_path = Path(derivatives_dir) / "rsfmri_qc" / subject_id / "slice_timing_qc.json"
    payload = _read_json(qc_path)
    if payload and payload.get("tr") is not None:
        try:
            parsed = float(payload["tr"])
            if parsed <= 0:
                errors.append(f"TR from slice timing QC is not positive: {parsed}")
                return None, warnings, errors, str(qc_path)
            return parsed, warnings, errors, str(qc_path)
        except Exception:
            errors.append("TR in slice timing QC is not numeric.")
            return None, warnings, errors, str(qc_path)

    if fallback_tr is not None:
        warnings.append("Using explicit fallback TR because slice timing QC TR was unavailable.")
        try:
            parsed = float(fallback_tr)
            if parsed <= 0:
                errors.append("fallback_tr must be positive.")
                return None, warnings, errors, "fallback_tr"
            return parsed, warnings, errors, "fallback_tr"
        except Exception:
            errors.append("fallback_tr must be numeric.")
            return None, warnings, errors, "fallback_tr"

    errors.append("TR is missing. Provide tr or fallback_tr, or run slice timing QC first.")
    return None, warnings, errors, None


def _write_qc_markdown(path: Path, qc: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# Temporal Filtering QC: {qc.get('subject_id')}")
    lines.append("")
    lines.append(f"- OK: {qc.get('ok')}")
    lines.append(f"- Status: {qc.get('filtering_qc_status')}")
    lines.append(f"- Input: `{qc.get('input_nii')}`")
    lines.append(f"- Output: `{qc.get('output_nii')}`")
    lines.append(f"- TR: {qc.get('tr')}")
    lines.append(f"- Band: {qc.get('low_hz')} - {qc.get('high_hz')} Hz")
    lines.append(f"- Nyquist: {qc.get('nyquist_hz')} Hz")
    lines.append(f"- Retained frequency bins: {qc.get('retained_frequency_bin_count')} / {qc.get('frequency_bin_count')}")
    lines.append(f"- Finite fraction: {qc.get('finite_fraction')}")
    lines.append(f"- Variance ratio: {qc.get('variance_ratio')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Temporal filtering reads derivative files only and does not modify rawdata.")
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
        "node_id": "temporal_filtering_qc_subject",
        "backend": "python",
        "subject_id": subject_id,
        "filtering_qc_status": "FAIL",
        "outputs": [str(qc_json), str(qc_md)],
        "warnings": warnings,
        "errors": errors,
    }

    result = {
        "ok": False,
        "node_id": "python_temporal_filter_subject",
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


def run_python_temporal_filter_subject(
    subject_id: str,
    derivatives_dir: str,
    low_hz: float = 0.01,
    high_hz: float = 0.08,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    result_json = func_dir / "temporal_filtering_result.json"
    qc_json = qc_dir / "temporal_filtering_qc.json"
    qc_md = qc_dir / "temporal_filtering_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    input_path = _find_residual_functional(subject_id, derivatives_dir)
    if not input_path:
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"No residual functional input found for subject {subject_id}."],
        )

    if not _safe_residual_input(input_path, subject_id, derivatives_dir):
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"Unsafe temporal filtering input: {input_path}"],
        )

    resolved_tr, tr_warnings, tr_errors, tr_source = _resolve_tr(
        subject_id=subject_id,
        derivatives_dir=derivatives_dir,
        tr=tr,
        fallback_tr=fallback_tr,
    )
    warnings.extend(tr_warnings)
    errors.extend(tr_errors)

    if resolved_tr is None:
        return _failure(subject_id, result_json, qc_json, qc_md, errors, warnings)

    try:
        low_hz = float(low_hz)
        high_hz = float(high_hz)
    except Exception:
        return _failure(subject_id, result_json, qc_json, qc_md, ["low_hz and high_hz must be numeric."], warnings)

    if low_hz < 0 or high_hz <= 0 or low_hz >= high_hz:
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"Invalid band-pass range: low_hz={low_hz}, high_hz={high_hz}"],
            warnings,
        )

    try:
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")

        if data.ndim != 4:
            raise ValueError(f"Input NIfTI must be 4D. Shape was: {data.shape}")

        n_time = int(data.shape[3])
        if n_time < 3:
            raise ValueError(f"Temporal filtering requires at least 3 timepoints. Got {n_time}.")

        nyquist = 1.0 / (2.0 * resolved_tr)

        if high_hz >= nyquist:
            warnings.append(
                f"high_hz={high_hz} is >= Nyquist={nyquist}. Clipping high_hz to Nyquist."
            )
            high_hz = nyquist

        freqs = np.fft.rfftfreq(n_time, d=resolved_tr)
        mask = (freqs >= low_hz) & (freqs <= high_hz)

        retained_bins = int(np.count_nonzero(mask))
        if retained_bins == 0:
            raise ValueError(
                f"No frequency bins retained for band {low_hz}-{high_hz} Hz with TR={resolved_tr} and n_time={n_time}."
            )

        spectrum = np.fft.rfft(data, axis=3)
        spectrum[..., ~mask] = 0.0
        filtered = np.fft.irfft(spectrum, n=n_time, axis=3).astype("float32")

        output_path = input_path.with_name(f"filt_{input_path.name}")
        out_img = nib.Nifti1Image(filtered, affine=img.affine, header=img.header)
        nib.save(out_img, str(output_path))

        finite_mask = np.isfinite(filtered)
        finite_fraction = float(np.count_nonzero(finite_mask) / filtered.size) if filtered.size else 0.0

        input_std_by_voxel = np.std(data, axis=3)
        filtered_std_by_voxel = np.std(filtered, axis=3)

        input_temporal_std_mean = float(np.mean(input_std_by_voxel))
        filtered_temporal_std_mean = float(np.mean(filtered_std_by_voxel))
        variance_ratio = (
            float(filtered_temporal_std_mean / input_temporal_std_mean)
            if input_temporal_std_mean > 0
            else None
        )

        status = "PASS"
        if finite_fraction < 0.95:
            status = "WARNING"
            warnings.append(f"Filtered finite fraction {finite_fraction:.4f} below 0.95.")
        if variance_ratio is not None and variance_ratio > 1.2:
            status = "WARNING"
            warnings.append(f"Filtered temporal std larger than input. Ratio={variance_ratio:.4f}.")

        qc = {
            "ok": True,
            "node_id": "temporal_filtering_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "output_nii": str(output_path),
            "input_shape": list(data.shape),
            "output_shape": list(filtered.shape),
            "tr": resolved_tr,
            "tr_source": tr_source,
            "low_hz": low_hz,
            "high_hz": high_hz,
            "nyquist_hz": nyquist,
            "frequency_bin_count": int(len(freqs)),
            "retained_frequency_bin_count": retained_bins,
            "retained_frequency_fraction": float(retained_bins / len(freqs)),
            "finite_fraction": finite_fraction,
            "input_temporal_std_mean": input_temporal_std_mean,
            "filtered_temporal_std_mean": filtered_temporal_std_mean,
            "variance_ratio": variance_ratio,
            "filtering_qc_status": status,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

        result = {
            "ok": True,
            "node_id": "python_temporal_filter_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "output_nii": str(output_path),
            "qc": qc,
            "outputs": [str(output_path), str(result_json), str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        return _failure(subject_id, result_json, qc_json, qc_md, [str(exc)], warnings)

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_markdown(qc_md, qc)
    return result


def write_temporal_filtering_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/temporal_filtering_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid temporal filtering QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("filtering_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("filtering_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("filtering_qc_status") == "FAIL")

    variance_ratios = [
        float(item["variance_ratio"])
        for item in subjects
        if item.get("variance_ratio") is not None
    ]

    retained_fractions = [
        float(item["retained_frequency_fraction"])
        for item in subjects
        if item.get("retained_frequency_fraction") is not None
    ]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "temporal_filtering_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_variance_ratio": float(mean(variance_ratios)) if variance_ratios else None,
        "mean_retained_frequency_fraction": float(mean(retained_fractions)) if retained_fractions else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "temporal_filtering_qc_summary.json"
    report_path = report_out / "temporal_filtering_qc_report.md"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# rs-fMRI Temporal Filtering QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean variance ratio: {summary['mean_variance_ratio']}")
    lines.append(f"- Mean retained frequency fraction: {summary['mean_retained_frequency_fraction']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | TR | Band Hz | Retained Bins | Variance Ratio |")
    lines.append("|---|---|---:|---|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('filtering_qc_status')} | "
            f"{item.get('tr')} | {item.get('low_hz')}-{item.get('high_hz')} | "
            f"{item.get('retained_frequency_bin_count')} | {item.get('variance_ratio')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative temporal filtering QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "temporal_filtering_qc_dataset_report",
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

## 3. 创建 backend/app/tools/dpabi_filtering_contract.py

创建文件：

```text
backend/app/tools/dpabi_filtering_contract.py
```

目标：生成 DPABI temporal filtering backend contract，但不执行 DPABI。

提供函数：

```python
write_dpabi_temporal_filtering_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/dpabi/contracts/temporal_filtering_backend_contract.json
```

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_dpabi_temporal_filtering_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "temporal_filtering_backend_contract.json"

    payload = {
        "ok": True,
        "node_id": "dpabi_temporal_filtering_contract",
        "backend": "python",
        "backend_id": "dpabi_temporal_filtering",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "required_approval": True,
        "description": "DPABI temporal filtering backend contract. This step does not execute DPABI.",
        "planned_inputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii",
            "outputs/derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json"
        ],
        "planned_outputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/dpabi_filtered_resid_swr*.nii",
            "outputs/logs/{subject_id}_dpabi_temporal_filtering.log"
        ],
        "parameters": {
            "low_hz": 0.01,
            "high_hz": 0.08,
            "tr_source": "slice_timing_qc_or_user_parameter"
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
            "This is a contract only. DPABI temporal filtering execution is intentionally not implemented in Step 43."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 4. 创建 backend/app/tools/temporal_filtering_runner.py

创建文件：

```text
backend/app/tools/temporal_filtering_runner.py
```

目标：包装 Python temporal filtering 与 DPABI contract mode。

提供函数：

```python
run_temporal_filtering_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    low_hz: float = 0.01,
    high_hz: float = 0.08,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict
```

参考实现：

```python
from __future__ import annotations

from typing import Any

from backend.app.tools.dpabi_filtering_contract import write_dpabi_temporal_filtering_contract
from backend.app.tools.temporal_filtering import run_python_temporal_filter_subject


def run_temporal_filtering_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    low_hz: float = 0.01,
    high_hz: float = 0.08,
    tr: float | None = None,
    fallback_tr: float | None = None,
) -> dict[str, Any]:
    if backend == "dpabi_contract":
        contract = write_dpabi_temporal_filtering_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend != "python":
        return {
            "ok": False,
            "node_id": "temporal_filtering_subject",
            "backend": backend,
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsupported temporal filtering backend: {backend}"],
        }

    result = run_python_temporal_filter_subject(
        subject_id=subject_id,
        derivatives_dir=derivatives_dir,
        low_hz=low_hz,
        high_hz=high_hz,
        tr=tr,
        fallback_tr=fallback_tr,
    )

    result["node_id"] = "temporal_filtering_subject"
    return result
```

---

## 5. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
temporal_filtering_subject
temporal_filtering_qc_dataset_report
dpabi_temporal_filtering_contract
```

新增导入：

```python
from backend.app.tools.temporal_filtering_runner import run_temporal_filtering_subject
from backend.app.tools.temporal_filtering import write_temporal_filtering_dataset_report
from backend.app.tools.dpabi_filtering_contract import write_dpabi_temporal_filtering_contract
```

新增 runner：

```python
def run_temporal_filtering_subject_node(
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

    result = run_temporal_filtering_subject(
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        backend=node.params.get("backend", "python"),
        low_hz=float(node.params.get("low_hz", 0.01)),
        high_hz=float(node.params.get("high_hz", 0.08)),
        tr=node.params.get("tr"),
        fallback_tr=node.params.get("fallback_tr"),
    )

    result["node_id"] = node.id
    return result


def run_temporal_filtering_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_temporal_filtering_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_dpabi_temporal_filtering_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_temporal_filtering_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"temporal_filtering_subject": run_temporal_filtering_subject_node,
"temporal_filtering_qc_dataset_report": run_temporal_filtering_qc_dataset_report_node,
"dpabi_temporal_filtering_contract": run_dpabi_temporal_filtering_contract_node,
```

---

## 6. 创建 examples/pipeline_rsfmri_temporal_filtering.yaml

创建文件：

```text
examples/pipeline_rsfmri_temporal_filtering.yaml
```

内容：

```yaml
pipeline_id: rsfmri_temporal_filtering_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run Python temporal filtering on nuisance-regressed synthetic derivatives and generate DPABI backend contract."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_temporal_filtering_001"
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

  - id: dpabi_temporal_filtering_contract
    name: DPABI Temporal Filtering Backend Contract
    agent: contract-runner
    backend: python
    depends_on:
      - temporal_filtering_subject
    inputs: []
    outputs:
      - "./work/dpabi/contracts/temporal_filtering_backend_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: temporal_filtering_qc_dataset_report
    name: Temporal Filtering QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - temporal_filtering_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/temporal_filtering_qc_summary.json"
      - "./reports/rsfmri/temporal_filtering_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。  
Python temporal filtering 本身不需要 MATLAB approval，但它依赖前面的 SPM derivative 输出。

---

## 7. 创建 backend/app/tools/run_rsfmri_temporal_filtering_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_temporal_filtering_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_temporal_filtering.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("outputs/work/rsfmri/approved_pipeline_temporal_filtering.yaml"),
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

## 8. 修改 backend/app/api/models.py

新增 request model：

```python
class RsfmriTemporalFilteringRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_temporal_filtering.yaml")
    approved: bool = Field(default=False)
```

---

## 9. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/temporal-filtering/run
GET  /api/rsfmri/temporal-filtering
```

新增导入：

```python
from backend.app.api.models import RsfmriTemporalFilteringRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_temporal_filtering_approved_copy(source: Path, target: Path) -> Path:
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
@router.post("/api/rsfmri/temporal-filtering/run")
def api_run_rsfmri_temporal_filtering(
    request: RsfmriTemporalFilteringRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="Temporal filtering pipeline requires approved=true because it depends on approved SPM preprocessing derivatives.",
        )

    try:
        approved_pipeline = _make_temporal_filtering_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("outputs/work/rsfmri/approved_pipeline_temporal_filtering.yaml"),
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


@router.get("/api/rsfmri/temporal-filtering")
def api_get_rsfmri_temporal_filtering() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")
    work_base = Path("work") / "dpabi" / "contracts"

    subject_filtering_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/temporal_filtering_qc.json")):
        subject_filtering_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "temporal_filtering_qc_summary": _read_json_if_exists(report_base / "temporal_filtering_qc_summary.json"),
        "temporal_filtering_qc_report": _read_text_if_exists(report_base / "temporal_filtering_qc_report.md"),
        "subject_temporal_filtering_qc": subject_filtering_qc,
        "dpabi_backend_contract": _read_json_if_exists(work_base / "temporal_filtering_backend_contract.json"),
    }
```

---

## 10. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriTemporalFiltering(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/temporal-filtering/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriTemporalFiltering(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/temporal-filtering"
  );
}
```

---

## 11. 创建 frontend/src/components/RsfmriTemporalFilteringPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriTemporalFilteringPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriTemporalFiltering,
  runRsfmriTemporalFiltering
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriTemporalFilteringPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 Python Temporal Filtering？这只处理 synthetic derivatives，不会修改 rawdata，也不会执行 DPABI。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriTemporalFiltering(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_temporal_filtering.yaml",
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
      const response = await getRsfmriTemporalFiltering(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.temporal_filtering_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Python Temporal Filtering
        </button>
        <button onClick={handleLoad}>加载 Temporal Filtering 结果</button>
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
          <span>Mean Variance Ratio</span>
          <strong>
            {summary?.mean_variance_ratio == null
              ? "-"
              : Number(summary.mean_variance_ratio).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Temporal Filtering QC Summary</h3>
      <JsonBlock value={loaded?.temporal_filtering_qc_summary} emptyText="暂无 temporal filtering QC summary" />

      <h3>Subject Temporal Filtering QC</h3>
      <JsonBlock value={loaded?.subject_temporal_filtering_qc} emptyText="暂无 subject temporal filtering QC" />

      <h3>DPABI Backend Contract</h3>
      <JsonBlock value={loaded?.dpabi_backend_contract} emptyText="暂无 DPABI backend contract" />

      <h3>Temporal Filtering QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.temporal_filtering_qc_report === "string"
            ? loaded.temporal_filtering_qc_report
            : null
        }
        emptyText="暂无 temporal filtering QC report"
      />
    </div>
  );
}
```

---

## 12. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriTemporalFilteringPanel } from "./components/RsfmriTemporalFilteringPanel";
```

在 `rs-fMRI Nuisance Regression` 后新增 Section：

```tsx
<Section
  title="rs-fMRI Temporal Filtering"
  description="对 nuisance-regressed functional image 执行 Python band-pass filtering，并生成 DPABI 后端 contract。"
>
  <RsfmriTemporalFilteringPanel baseUrl={baseUrl} />
</Section>
```

---

## 13. 新增轻量测试

创建文件：

```text
tests/unit/test_temporal_filtering.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.temporal_filtering import run_python_temporal_filter_subject


def test_python_temporal_filter_outputs_filtered_nifti(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    qc_dir = derivatives / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True)
    qc_dir.mkdir(parents=True)

    input_nii = func_dir / "resid_swrasub-001_bold.nii"

    tr = 2.0
    n_time = 32
    t = np.arange(n_time) * tr

    low_signal = np.sin(2 * np.pi * 0.03 * t)
    high_signal = 0.5 * np.sin(2 * np.pi * 0.2 * t)
    signal = low_signal + high_signal

    data = np.zeros((3, 3, 3, n_time), dtype=np.float32)
    data[:] = signal.astype(np.float32)

    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))

    (qc_dir / "slice_timing_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": subject_id,
            "tr": tr,
            "slice_timing_status": "PASS",
        }),
        encoding="utf-8",
    )

    result = run_python_temporal_filter_subject(
        subject_id=subject_id,
        derivatives_dir=str(derivatives),
        low_hz=0.01,
        high_hz=0.08,
    )

    assert result["ok"] is True

    output_nii = func_dir / "filt_resid_swrasub-001_bold.nii"
    assert output_nii.exists()

    qc_path = qc_dir / "temporal_filtering_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == subject_id
    assert payload["filtering_qc_status"] in {"PASS", "WARNING"}
    assert payload["tr"] == tr
    assert payload["retained_frequency_bin_count"] > 0
```

---

## 14. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/temporal-filtering")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 15. 更新 README.md

追加第四十三步说明：

```markdown
## Step 43: Temporal Filtering and Filtering QC

This step implements Python FFT-based temporal band-pass filtering.

It supports:

- derivative nuisance-regressed functional input only
- TR from slice timing QC or explicit fallback
- default band-pass 0.01-0.08 Hz
- filtered functional output
- subject-level filtering QC
- dataset-level filtering QC report
- DPABI backend contract generation without execution
- frontend visualization

It does not execute DPABI.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_temporal_filtering_cli
```

This should fail safely because upstream SPM steps are not approved.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_temporal_filtering_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_temporal_filtering.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_preproc/sub-001/func/filt_resid_swrasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/temporal_filtering_result.json
derivatives/rsfmri_qc/sub-001/temporal_filtering_qc.json
derivatives/rsfmri_qc/sub-001/temporal_filtering_qc.md
reports/rsfmri/temporal_filtering_qc_summary.json
reports/rsfmri/temporal_filtering_qc_report.md
work/dpabi/contracts/temporal_filtering_backend_contract.json
work/pipeline_runs/run_rsfmri_temporal_filtering_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/temporal-filtering
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/temporal-filtering/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_temporal_filtering.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI Temporal Filtering
```

### Safety

This step:

- only processes derivative nuisance-regressed functional input
- obtains TR from slice timing QC or explicit fallback
- does not modify rawdata
- does not run DPABI
- only creates a DPABI backend contract
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing
```

---

## 16. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/temporal_filtering_qc_spec.md
backend/app/tools/temporal_filtering.py
backend/app/tools/dpabi_filtering_contract.py
backend/app/tools/temporal_filtering_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_temporal_filtering.yaml
backend/app/tools/run_rsfmri_temporal_filtering_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriTemporalFilteringPanel.tsx
frontend/src/App.tsx
tests/unit/test_temporal_filtering.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_temporal_filtering_cli
```

应该安全失败，不应启动 SPM / DPABI。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_temporal_filtering_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_temporal_filtering.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_preproc/sub-001/func/filt_resid_swrasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/temporal_filtering_result.json
derivatives/rsfmri_qc/sub-001/temporal_filtering_qc.json
reports/rsfmri/temporal_filtering_qc_summary.json
work/dpabi/contracts/temporal_filtering_backend_contract.json
```

temporal filtering QC JSON 必须包含：

```json
{
  "node_id": "temporal_filtering_qc_subject",
  "subject_id": "sub-001",
  "filtering_qc_status": "PASS",
  "tr": 2.0,
  "low_hz": 0.01,
  "high_hz": 0.08,
  "retained_frequency_bin_count": 0,
  "finite_fraction": 1.0
}
```

实际数值根据 synthetic 数据、TR 和频率 bins 决定。

运行测试：

```bash
python -m pytest tests/unit/test_temporal_filtering.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/temporal-filtering

curl -X POST http://127.0.0.1:8000/api/rsfmri/temporal-filtering/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/temporal-filtering/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI Temporal Filtering 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 temporal filtering 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean variance ratio。
8. 显示 temporal filtering QC summary JSON。
9. 显示 subject temporal filtering QC JSON。
10. 显示 DPABI backend contract。
11. 显示 temporal filtering QC Markdown report。
12. 不修改 rawdata。
13. 不运行 DPABI。
14. 不调用 DPARSF_run / DPARSFA_run。
15. 不执行完整 preprocessing。

---

## 17. 重要限制

本步骤只做 Python temporal filtering、Filtering QC、DPABI filtering backend contract。

不要实现：

- ALFF / fALFF / ReHo
- 真实 DPABI temporal filtering 执行
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
3. temporal filtering 如何获取 TR
4. FFT band-pass filtering 如何执行
5. Filtering QC 如何计算
6. DPABI filtering backend contract 为什么只生成不执行
7. 输出哪些 derivatives 和 reports
8. 为什么本步骤仍然不是完整 preprocessing
9. 下一步如何实现 ALFF / fALFF 计算与 GPU candidate backend

```
这一步给预处理流水线加了时间滤波。

**写了 FFT band-pass filter。** `temporal_filtering.py` 读 `resid_swr*.nii`，对时间维做 rFFT，在频域保留 0.01-0.08 Hz，其余频率置零，irFFT 回时域，输出 `filt_resid_swr*.nii`，保留原 header 和 affine。TR 的获取顺序是：函数参数 → slice_timing_qc.json → fallback_tr，三级都没有就报错。

**写了 DPABI filtering contract。** 和上一步 nuisance regression 一样，只生成 JSON contract 标记 `CONTRACT_ONLY`，不执行 DPABI。

**接了全栈。** pipeline 现在 15 个节点，在前端和 API 都暴露了 temporal filtering 结果和 QC（retained frequency bins、finite fraction、temporal std ratio）。
```
