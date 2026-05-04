# 第四十一步 Prompt：SPM Smoothing + Smoothing QC 闭环

```text
你是我的工程搭建助手。前四十步已经完成：

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

现在开始第四十一步。

第四十一步目标：实现 “SPM Smoothing + Smoothing QC 闭环”。

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

但还缺少 rs-fMRI 预处理中常见的空间平滑步骤。  
本步骤要继续深入 rs-fMRI 核心预处理，实现：

normalized functional image
→ SPM smoothing
→ smoothed normalized functional image
→ smoothing QC
→ subject-level smoothing report
→ dataset-level smoothing QC report

本步骤要实现：

1. SPM smoothing wrapper。
2. 对 synthetic BIDS-like normalized functional derivative 执行 SPM smoothing。
3. 使用 normalization 输出的 functional image：
   - `derivatives/rsfmri_preproc/{subject_id}/func/wr*.nii`
   - 优先 `wrasub-001_bold.nii` 或对应 `w*.nii`
4. 输出 smoothed normalized functional：
   - `swrasub-001_bold.nii` 或对应 `sw*.nii`
5. 输出 SPM smoothing result JSON。
6. 生成 smoothing QC：
   - input normalized file 是否存在
   - smoothed output 是否存在
   - input shape / output shape
   - input voxel size / output voxel size
   - fwhm parameter
   - finite fraction
   - input intensity mean/std
   - smoothed intensity mean/std
   - approximate variance reduction ratio
   - output filename convention check
   - smoothing_qc_status
7. 生成 subject-level smoothing QC JSON / Markdown。
8. 生成 dataset-level smoothing QC summary / Markdown report。
9. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC → Normalization → Normalization QC → Smoothing → Smoothing QC
10. 后端 API 暴露 smoothing + smoothing QC 结果。
11. 前端新增 rs-fMRI Smoothing + Smoothing QC 面板。
12. 增加轻量 unit test。
13. 更新 README。

本步骤允许调用 SPM，但必须满足：

- 只处理 synthetic BIDS-like 数据。
- 必须 approved=true 才执行 SPM smoothing。
- smoothing 输入必须来自 derivatives 中的 normalization 输出。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- nuisance regression
- temporal filtering
- ALFF / fALFF / ReHo
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：SPM smoothing + smoothing QC。

---

## 1. 创建 specs/spm_smoothing_qc_spec.md

创建文件：

```text
specs/spm_smoothing_qc_spec.md
```

内容：

```markdown
# SPM Smoothing and Smoothing QC Specification

This document defines the MVP SPM smoothing and smoothing QC stage for rs-fMRI preprocessing.

## Goals

The goal is to apply Gaussian spatial smoothing to normalized functional images and compute lightweight smoothing QC metrics.

This step prepares normalized rs-fMRI data for later nuisance regression, temporal filtering, ALFF, fALFF, ReHo, and group-level analysis.

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM smoothing
- derivative normalized functional input
- smoothed normalized functional output
- subject-level smoothing QC JSON / Markdown
- dataset-level smoothing QC summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- nuisance regression
- temporal filtering
- ALFF / fALFF / ReHo
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- rawdata modification
- source modification in SPM / DPABI
- file deletion

## Inputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/wr*.nii
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/swr*.nii
derivatives/rsfmri_preproc/{subject_id}/func/spm_smoothing_result.json
derivatives/rsfmri_qc/{subject_id}/smoothing_qc.json
derivatives/rsfmri_qc/{subject_id}/smoothing_qc.md
reports/rsfmri/smoothing_qc_summary.json
reports/rsfmri/smoothing_qc_report.md
```

## Smoothing QC Metrics

- input_exists
- smoothed_output_exists
- input_shape
- smoothed_shape
- input_voxel_size
- smoothed_voxel_size
- fwhm
- finite_fraction
- input_intensity_mean
- input_intensity_std
- smoothed_intensity_mean
- smoothed_intensity_std
- variance_reduction_ratio
- filename_prefix_ok
- smoothing_qc_status

## Safety Rules

- Execution requires approved=true.
- Only derivative normalized functional input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not call DPABI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
```

---

## 2. 创建 matlab/spm_smooth_wrapper.m

创建文件：

```text
matlab/spm_smooth_wrapper.m
```

功能要求：

1. 接收参数：
   - spm_dir
   - input_nii
   - fwhm_json
   - output_json

2. input_nii 必须是 derivatives workspace 中 normalization 输出的 normalized functional image。
3. 使用 SPM smooth。
4. 支持 4D NIfTI functional input。
5. 输出 JSON，记录：
   - ok
   - input_nii
   - smoothed_file
   - fwhm
   - frames_total
   - output_dir
   - errors
   - warnings
6. 不调用 DPABI。
7. 不调用 DPARSF_run / DPARSFA_run。
8. 不修改 rawdata。
9. 不删除文件。

参考实现：

```matlab
function spm_smooth_wrapper(spm_dir, input_nii, fwhm_json, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_smooth_wrapper';
    result.backend = 'matlab-spm';
    result.input_nii = input_nii;
    result.smoothed_file = '';
    result.fwhm = [];
    result.frames_total = 0;
    result.output_dir = fileparts(input_nii);
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_nii, 'file')
            error(['Input normalized functional NIfTI not found: ', input_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        fwhm = jsondecode(fwhm_json);
        fwhm = double(fwhm(:)');
        result.fwhm = fwhm;

        if numel(fwhm) ~= 3
            error('FWHM must contain exactly 3 values.');
        end

        vols = spm_vol(input_nii);
        n_frames = numel(vols);
        result.frames_total = n_frames;

        scans = cell(n_frames, 1);
        for i = 1:n_frames
            scans{i} = [input_nii, ',', num2str(i)];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.smooth.data = scans;
        matlabbatch{1}.spm.spatial.smooth.fwhm = fwhm;
        matlabbatch{1}.spm.spatial.smooth.dtype = 0;
        matlabbatch{1}.spm.spatial.smooth.im = 0;
        matlabbatch{1}.spm.spatial.smooth.prefix = 's';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);
        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        smoothed_file = fullfile(input_dir, ['s', input_name, '.nii']);

        if exist(smoothed_file, 'file')
            result.smoothed_file = smoothed_file;
        else
            error(['Expected smoothed file not found: ', smoothed_file]);
        end

    catch ME
        result.ok = false;
        try
            result.errors{end+1} = getReport(ME, 'extended', 'hyperlinks', 'off');
        catch
            result.errors{end+1} = ME.message;
        end
    end

    fid = fopen(output_json, 'w');
    if fid == -1
        error(['Cannot open output JSON for writing: ', output_json]);
    end

    fwrite(fid, jsonencode(result), 'char');
    fclose(fid);

    if ~result.ok
        exit(1);
    end
end
```

---

## 3. 创建 backend/app/tools/smoothing_qc.py

创建文件：

```text
backend/app/tools/smoothing_qc.py
```

目标：根据 normalized functional input 和 smoothed output 计算 lightweight smoothing QC。

提供函数：

```python
compute_smoothing_qc_for_subject(
    subject_id: str,
    input_nii: str,
    smoothed_nii: str,
    derivatives_dir: str,
    fwhm: list[float] | None = None,
    finite_fraction_warning: float = 0.95,
) -> dict

write_smoothing_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. 使用 nibabel 读取 header / affine。
2. 可以读取 small synthetic data，用于 finite check 和 intensity summary。
3. 计算：
   - input shape
   - smoothed shape
   - input voxel size
   - smoothed voxel size
   - finite fraction
   - input mean/std
   - smoothed mean/std
   - variance reduction ratio = smoothed_std / input_std
4. QC 状态：
   - input / smoothed 缺失 → FAIL
   - shape 不一致 → FAIL
   - finite_fraction < threshold → WARNING
   - smoothed_std > input_std * 1.2 → WARNING
   - filename 不以 s 开头 → WARNING
   - 其他 → PASS
5. 输出 subject-level JSON / Markdown。
6. 输出 dataset-level JSON / Markdown。

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _load_nifti_stats(path: Path) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    img = nib.load(str(path))
    shape = list(img.shape)
    zooms = [float(x) for x in img.header.get_zooms()[:3]]
    affine = img.affine.tolist()

    data = img.get_fdata(dtype="float32")
    finite_mask = np.isfinite(data)
    finite_fraction = float(np.count_nonzero(finite_mask) / data.size) if data.size else 0.0

    if np.count_nonzero(finite_mask):
        finite_data = data[finite_mask]
        intensity_mean = float(np.mean(finite_data))
        intensity_std = float(np.std(finite_data))
    else:
        intensity_mean = None
        intensity_std = None

    return {
        "path": str(path),
        "shape": shape,
        "voxel_size": zooms,
        "affine": affine,
        "frames_total": int(shape[3]) if len(shape) >= 4 else 1,
        "finite_fraction": finite_fraction,
        "intensity_mean": intensity_mean,
        "intensity_std": intensity_std,
    }


def compute_smoothing_qc_for_subject(
    subject_id: str,
    input_nii: str,
    smoothed_nii: str,
    derivatives_dir: str,
    fwhm: list[float] | None = None,
    finite_fraction_warning: float = 0.95,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "smoothing_qc.json"
    qc_md = out_dir / "smoothing_qc.md"

    fwhm = fwhm or [6.0, 6.0, 6.0]

    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    smoothed_path = Path(smoothed_nii)

    missing = [
        str(path)
        for path in [input_path, smoothed_path]
        if not path.exists()
    ]

    if missing:
        result = {
            "ok": False,
            "node_id": "smoothing_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "smoothing_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            input_stats = _load_nifti_stats(input_path)
            smoothed_stats = _load_nifti_stats(smoothed_path)

            status = "PASS"

            if input_stats["shape"] != smoothed_stats["shape"]:
                status = "FAIL"
                errors.append("Input and smoothed output shapes differ.")

            if smoothed_stats["finite_fraction"] < finite_fraction_warning and status != "FAIL":
                status = "WARNING"
                warnings.append(
                    f"Finite fraction {smoothed_stats['finite_fraction']:.4f} below threshold {finite_fraction_warning}."
                )

            input_std = input_stats["intensity_std"]
            smoothed_std = smoothed_stats["intensity_std"]

            if input_std is None or input_std == 0 or smoothed_std is None:
                variance_reduction_ratio = None
            else:
                variance_reduction_ratio = float(smoothed_std / input_std)

            if (
                variance_reduction_ratio is not None
                and variance_reduction_ratio > 1.2
                and status != "FAIL"
            ):
                status = "WARNING"
                warnings.append(
                    f"Smoothed std appears larger than input std. Ratio={variance_reduction_ratio:.4f}."
                )

            filename_prefix_ok = smoothed_path.name.startswith("s")
            if not filename_prefix_ok and status != "FAIL":
                status = "WARNING"
                warnings.append("Smoothed output filename does not start with SPM prefix 's'.")

            result = {
                "ok": status != "FAIL",
                "node_id": "smoothing_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "input_nii": str(input_path),
                "smoothed_nii": str(smoothed_path),
                "input_shape": input_stats["shape"],
                "smoothed_shape": smoothed_stats["shape"],
                "input_voxel_size": input_stats["voxel_size"],
                "smoothed_voxel_size": smoothed_stats["voxel_size"],
                "frames_total": smoothed_stats["frames_total"],
                "fwhm": fwhm,
                "finite_fraction": smoothed_stats["finite_fraction"],
                "input_intensity_mean": input_stats["intensity_mean"],
                "input_intensity_std": input_stats["intensity_std"],
                "smoothed_intensity_mean": smoothed_stats["intensity_mean"],
                "smoothed_intensity_std": smoothed_stats["intensity_std"],
                "variance_reduction_ratio": variance_reduction_ratio,
                "filename_prefix_ok": filename_prefix_ok,
                "smoothing_qc_status": status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "smoothing_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "smoothing_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Smoothing QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('smoothing_qc_status')}")
    lines.append(f"- Input: `{result.get('input_nii')}`")
    lines.append(f"- Smoothed: `{result.get('smoothed_nii')}`")
    lines.append(f"- FWHM: {result.get('fwhm')}")
    lines.append(f"- Shape: {result.get('smoothed_shape')}")
    lines.append(f"- Voxel size: {result.get('smoothed_voxel_size')}")
    lines.append(f"- Finite fraction: {result.get('finite_fraction')}")
    lines.append(f"- Variance reduction ratio: {result.get('variance_reduction_ratio')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Smoothing QC reads derivative files only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_smoothing_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/smoothing_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid smoothing QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("smoothing_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("smoothing_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("smoothing_qc_status") == "FAIL")

    finite_fractions = [
        float(item["finite_fraction"])
        for item in subjects
        if item.get("finite_fraction") is not None
    ]

    variance_ratios = [
        float(item["variance_reduction_ratio"])
        for item in subjects
        if item.get("variance_reduction_ratio") is not None
    ]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "smoothing_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_finite_fraction": float(mean(finite_fractions)) if finite_fractions else None,
        "mean_variance_reduction_ratio": float(mean(variance_ratios)) if variance_ratios else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "smoothing_qc_summary.json"
    report_path = report_out / "smoothing_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Smoothing QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean finite fraction: {summary['mean_finite_fraction']}")
    lines.append(f"- Mean variance reduction ratio: {summary['mean_variance_reduction_ratio']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | FWHM | Shape | Finite Fraction | Variance Ratio |")
    lines.append("|---|---|---|---|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('smoothing_qc_status')} | "
            f"{item.get('fwhm')} | {item.get('smoothed_shape')} | "
            f"{item.get('finite_fraction')} | {item.get('variance_reduction_ratio')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative smoothing QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "smoothing_qc_dataset_report",
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

## 4. 创建 backend/app/tools/spm_smooth_runner.py

创建文件：

```text
backend/app/tools/spm_smooth_runner.py
```

目标：Python 调用 MATLAB SPM smoothing wrapper。

提供函数：

```python
run_spm_smooth_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    fwhm: list[float] | None = None,
    matlab_script_dir: str = "./matlab",
) -> dict
```

实现要求：

1. approved=false 时安全失败，不启动 MATLAB。
2. smoothing input 必须来自：

```text
derivatives/rsfmri_preproc/{subject_id}/func/wr*.nii
```

优先选择：

```text
derivatives/rsfmri_preproc/{subject_id}/func/wrasub-001_bold.nii
```

或任意 `wr*.nii`，但不能选择：
- `wmean*.nii`
- `swr*.nii`
- `rp_*.txt`
- rawdata

3. 调用 `spm_smooth_wrapper.m`。
4. 调用 `compute_smoothing_qc_for_subject`。
5. 输出：
   - `swr*.nii`
   - `spm_smoothing_result.json`
   - `smoothing_qc.json`
   - stdout / stderr logs
6. 不使用 shell=True。
7. 不调用 DPABI。
8. 不调用 DPARSF_run / DPARSFA_run。

参考实现：

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from backend.app.tools.smoothing_qc import compute_smoothing_qc_for_subject


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _find_normalized_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    preferred = func_dir / f"wra{subject_id}_bold.nii"
    if preferred.exists():
        return preferred

    candidates = []
    for path in sorted(func_dir.glob("wr*.nii")):
        name = path.name
        if name.startswith("wmean"):
            continue
        if name.startswith("swr"):
            continue
        if name.startswith("rp_"):
            continue
        candidates.append(path)

    return candidates[0] if candidates else None


def _is_safe_normalized_input(path: Path, subject_id: str, derivatives_dir: str) -> bool:
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

    name = path.name
    return (
        name.startswith("wr")
        and name.endswith(".nii")
        and not name.startswith("wmean")
        and not name.startswith("swr")
        and not name.startswith("rp_")
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_spm_smooth_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    fwhm: list[float] | None = None,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_smooth_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM smoothing requires approved=true."],
        }

    fwhm = fwhm or [6.0, 6.0, 6.0]

    input_func = _find_normalized_functional(subject_id, derivatives_dir)
    if not input_func:
        return {
            "ok": False,
            "node_id": "spm_smooth_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                f"No normalized functional input found under derivatives/rsfmri_preproc/{subject_id}/func."
            ],
        }

    if not _is_safe_normalized_input(input_func, subject_id, derivatives_dir):
        return {
            "ok": False,
            "node_id": "spm_smooth_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsafe smoothing functional input: {input_func}"],
        }

    func_dir = input_func.parent

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_smooth_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_smooth_stderr.log"
    result_json = func_dir / "spm_smoothing_result.json"

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_smooth_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(input_func.resolve()))}', "
        f"'{_matlab_quote(json.dumps(fwhm))}', "
        f"'{_matlab_quote(str(result_json.resolve()))}'); "
        "catch ME, disp(getReport(ME)); exit(1); end; exit(0);"
    )

    cmd = [
        matlab_command,
        "-nodisplay",
        "-nosplash",
        "-r",
        matlab_code,
    ]

    with stdout_log.open("w", encoding="utf-8") as out, stderr_log.open("w", encoding="utf-8") as err:
        completed = subprocess.run(cmd, stdout=out, stderr=err, check=False)

    data = _read_json(result_json) or {
        "ok": False,
        "errors": ["SPM smoothing did not produce result JSON."],
    }

    data["node_id"] = "spm_smooth_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["input_func"] = str(input_func)
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    qc_outputs = []
    smoothed_file = data.get("smoothed_file")

    if smoothed_file:
        qc = compute_smoothing_qc_for_subject(
            subject_id=subject_id,
            input_nii=str(input_func),
            smoothed_nii=smoothed_file,
            derivatives_dir=derivatives_dir,
            fwhm=fwhm,
        )
        data["smoothing_qc"] = qc
        qc_outputs = qc.get("outputs", [])

    outputs = []
    if data.get("smoothed_file"):
        outputs.append(data["smoothed_file"])

    outputs.extend(qc_outputs)
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
```

---

## 5. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
spm_smooth_subject
smoothing_qc_dataset_report
```

新增导入：

```python
from backend.app.tools.spm_smooth_runner import run_spm_smooth_subject
from backend.app.tools.smoothing_qc import write_smoothing_qc_dataset_report
```

新增 runner：

```python
def run_spm_smooth_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    if not context.subject_id:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id in context."],
        }

    result = run_spm_smooth_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        fwhm=node.params.get("fwhm", [6.0, 6.0, 6.0]),
        matlab_script_dir="./matlab",
    )

    result["node_id"] = node.id
    return result


def run_smoothing_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_smoothing_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"spm_smooth_subject": run_spm_smooth_subject_node,
"smoothing_qc_dataset_report": run_smoothing_qc_dataset_report_node,
```

---

## 6. 创建 examples/pipeline_rsfmri_smoothing_qc.yaml

创建文件：

```text
examples/pipeline_rsfmri_smoothing_qc.yaml
```

内容：

```yaml
pipeline_id: rsfmri_smoothing_qc_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run approved SPM smoothing on normalized synthetic functional derivatives and compute smoothing QC."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_smoothing_qc_001"
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

  - id: registration_qc_dataset_report
    name: Registration QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - spm_coregister_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/registration_qc_summary.json"
      - "./reports/rsfmri/registration_qc_report.md"
    params: {}
    parallel_level: project
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

  - id: tissue_qc_dataset_report
    name: Tissue QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - spm_segment_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/tissue_qc_summary.json"
      - "./reports/rsfmri/tissue_qc_report.md"
    params: {}
    parallel_level: project
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

  - id: normalization_qc_dataset_report
    name: Normalization QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - spm_normalize_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/normalization_qc_summary.json"
      - "./reports/rsfmri/normalization_qc_report.md"
    params: {}
    parallel_level: project
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

  - id: smoothing_qc_dataset_report
    name: Smoothing QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - spm_smooth_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/smoothing_qc_summary.json"
      - "./reports/rsfmri/smoothing_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。

---

## 7. 创建 backend/app/tools/run_rsfmri_smoothing_qc_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_smoothing_qc_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_smoothing_qc.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("outputs/work/rsfmri/approved_pipeline_smoothing_qc.yaml"),
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
class RsfmriSmoothingQcRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_smoothing_qc.yaml")
    approved: bool = Field(default=False)
```

---

## 9. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/smoothing-qc/run
GET  /api/rsfmri/smoothing-qc
```

新增导入：

```python
from backend.app.api.models import RsfmriSmoothingQcRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_smoothing_qc_approved_copy(source: Path, target: Path) -> Path:
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
@router.post("/api/rsfmri/smoothing-qc/run")
def api_run_rsfmri_smoothing_qc(
    request: RsfmriSmoothingQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM smoothing QC pipeline requires approved=true.",
        )

    try:
        approved_pipeline = _make_smoothing_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("outputs/work/rsfmri/approved_pipeline_smoothing_qc.yaml"),
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


@router.get("/api/rsfmri/smoothing-qc")
def api_get_rsfmri_smoothing_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_smoothing_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/smoothing_qc.json")):
        subject_smoothing_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "smoothing_qc_summary": _read_json_if_exists(report_base / "smoothing_qc_summary.json"),
        "smoothing_qc_report": _read_text_if_exists(report_base / "smoothing_qc_report.md"),
        "subject_smoothing_qc": subject_smoothing_qc,
    }
```

---

## 10. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriSmoothingQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/smoothing-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriSmoothingQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/smoothing-qc"
  );
}
```

---

## 11. 创建 frontend/src/components/RsfmriSmoothingQcPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriSmoothingQcPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriSmoothingQc,
  runRsfmriSmoothingQc
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriSmoothingQcPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 SPM Smoothing + Smoothing QC？这只处理 synthetic BIDS 数据，不会修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriSmoothingQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_smoothing_qc.yaml",
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
      const response = await getRsfmriSmoothingQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.smoothing_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Smoothing + Smoothing QC
        </button>
        <button onClick={handleLoad}>加载 Smoothing QC 结果</button>
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
            {summary?.mean_variance_reduction_ratio == null
              ? "-"
              : Number(summary.mean_variance_reduction_ratio).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Smoothing QC Summary</h3>
      <JsonBlock value={loaded?.smoothing_qc_summary} emptyText="暂无 smoothing QC summary" />

      <h3>Subject Smoothing QC</h3>
      <JsonBlock value={loaded?.subject_smoothing_qc} emptyText="暂无 subject smoothing QC" />

      <h3>Smoothing QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.smoothing_qc_report === "string"
            ? loaded.smoothing_qc_report
            : null
        }
        emptyText="暂无 smoothing QC report"
      />
    </div>
  );
}
```

---

## 12. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriSmoothingQcPanel } from "./components/RsfmriSmoothingQcPanel";
```

在 `rs-fMRI SPM Normalization + Normalization QC` 后新增 Section：

```tsx
<Section
  title="rs-fMRI SPM Smoothing + Smoothing QC"
  description="对 normalized functional image 执行 SPM smoothing，并生成 smoothing QC。"
>
  <RsfmriSmoothingQcPanel baseUrl={baseUrl} />
</Section>
```

---

## 13. 新增轻量测试

创建文件：

```text
tests/unit/test_smoothing_qc.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.smoothing_qc import compute_smoothing_qc_for_subject


def test_smoothing_qc_computes_variance_ratio(tmp_path: Path):
    derivatives = tmp_path / "derivatives"

    input_func = tmp_path / "wrasub-001_bold.nii"
    smoothed = tmp_path / "swrasub-001_bold.nii"

    affine = np.diag([3.0, 3.0, 3.0, 1.0])

    rng = np.random.default_rng(42)
    input_data = rng.normal(0, 2, size=(6, 6, 6, 5)).astype(np.float32)
    smoothed_data = input_data * 0.5

    nib.save(nib.Nifti1Image(input_data, affine), str(input_func))
    nib.save(nib.Nifti1Image(smoothed_data, affine), str(smoothed))

    result = compute_smoothing_qc_for_subject(
        subject_id="sub-001",
        input_nii=str(input_func),
        smoothed_nii=str(smoothed),
        derivatives_dir=str(derivatives),
        fwhm=[6.0, 6.0, 6.0],
    )

    assert result["ok"] is True
    assert result["smoothing_qc_status"] == "PASS"
    assert result["frames_total"] == 5
    assert result["finite_fraction"] == 1.0
    assert result["variance_reduction_ratio"] < 1.0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "smoothing_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
```

---

## 14. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/smoothing-qc")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 15. 更新 README.md

追加第四十一步说明：

```markdown
## Step 41: SPM Smoothing and Smoothing QC

This step implements SPM smoothing using the normalized functional image produced by normalization.

It supports:

- approved SPM smoothing
- derivative normalized functional input only
- smoothed normalized functional output
- smoothing QC metrics
- subject-level smoothing QC
- dataset-level smoothing QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_smoothing_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_smoothing_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_smoothing_qc.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_preproc/sub-001/func/swrasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/spm_smoothing_result.json
derivatives/rsfmri_qc/sub-001/smoothing_qc.json
derivatives/rsfmri_qc/sub-001/smoothing_qc.md
reports/rsfmri/smoothing_qc_summary.json
reports/rsfmri/smoothing_qc_report.md
work/pipeline_runs/run_rsfmri_smoothing_qc_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/smoothing-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/smoothing-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_smoothing_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI SPM Smoothing + Smoothing QC
```

### Safety

This step:

- requires approved=true
- only processes derivative normalized functional input
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing
```

---

## 16. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/spm_smoothing_qc_spec.md
matlab/spm_smooth_wrapper.m
backend/app/tools/smoothing_qc.py
backend/app/tools/spm_smooth_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_smoothing_qc.yaml
backend/app/tools/run_rsfmri_smoothing_qc_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriSmoothingQcPanel.tsx
frontend/src/App.tsx
tests/unit/test_smoothing_qc.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_smoothing_qc_cli
```

应该安全失败，不应启动 SPM smoothing。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_smoothing_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_smoothing_qc.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_preproc/sub-001/func/swrasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/spm_smoothing_result.json
derivatives/rsfmri_qc/sub-001/smoothing_qc.json
reports/rsfmri/smoothing_qc_summary.json
reports/rsfmri/smoothing_qc_report.md
```

smoothing QC JSON 必须包含：

```json
{
  "node_id": "smoothing_qc_subject",
  "subject_id": "sub-001",
  "smoothing_qc_status": "PASS",
  "input_shape": [],
  "smoothed_shape": [],
  "fwhm": [6.0, 6.0, 6.0],
  "finite_fraction": 1.0
}
```

实际数值根据 synthetic 数据和 SPM 输出决定。

运行测试：

```bash
python -m pytest tests/unit/test_smoothing_qc.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/smoothing-qc

curl -X POST http://127.0.0.1:8000/api/rsfmri/smoothing-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/smoothing-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI SPM Smoothing + Smoothing QC 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 smoothing QC 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean variance reduction ratio。
8. 显示 smoothing QC summary JSON。
9. 显示 subject smoothing QC JSON。
10. 显示 smoothing QC Markdown report。
11. 不修改 rawdata。
12. 不运行 DPABI。
13. 不调用 DPARSF_run / DPARSFA_run。
14. 不执行完整 preprocessing。

---

## 17. 重要限制

本步骤只做 SPM smoothing + smoothing QC。

不要实现：

- nuisance regression
- temporal filtering
- ALFF / fALFF / ReHo
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
3. SPM smoothing wrapper 如何工作
4. normalized functional input 如何保证来自 derivatives
5. smoothing QC 如何计算
6. 输出哪些 derivatives 和 reports
7. 为什么本步骤仍然不是完整 preprocessing
8. 下一步如何实现 nuisance regression 参数计划与 DPABI/Python 双后端设计

```
这一步给预处理流水线加了最后的空间平滑。

**SPM smooth wrapper** 拿 normalization 产出的 `wr*.nii`，调 `spm.spatial.smooth` 做 FWHM=6mm 的高斯平滑，输出前缀 `s`（变成 `swr*.nii`）。**smoothing QC** 检查输入输出形状是否一致、finite fraction 是否低于 95%、平滑后标准差是否反而比输入大（ratio > 1.2 标 WARNING）、文件名是否以 `s` 开头。

现在整条 SPM 预处理链有 6 个 SPM 节点（slice timing → realignment → coregistration → segmentation → normalization → smoothing）串在一起了，还剩 nuisance regression、temporal filtering 和 ALFF/fALFF/ReHo 等后处理步骤没做。
```
