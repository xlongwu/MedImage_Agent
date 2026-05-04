# 第四十步 Prompt：SPM Normalization + Normalization QC 闭环

```text
你是我的工程搭建助手。前三十九步已经完成：

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

现在开始第四十步。

第四十步目标：实现 “SPM Normalization + Normalization QC 闭环”。

当前系统已经可以完成：

synthetic raw BOLD
→ SPM slice timing correction
→ SPM realignment
→ motion QC
→ SPM coregistration
→ registration QC
→ SPM segmentation
→ tissue QC

但还缺少把功能像标准化到 MNI/template space 的关键步骤。  
本步骤要继续深入 rs-fMRI 核心预处理，实现：

segmentation deformation field
→ realigned functional image
→ SPM normalize write
→ normalized functional image
→ normalization QC
→ subject-level normalization report
→ dataset-level normalization QC report

本步骤要实现：

1. SPM normalization write wrapper。
2. 对 synthetic BIDS-like functional derivative 执行 SPM normalization。
3. 使用 segmentation 输出的 deformation field：
   - `derivatives/rsfmri_preproc/{subject_id}/anat/y_coreg_{subject_id}_T1w.nii`
4. 使用 realignment 输出的 functional image：
   - 优先 `derivatives/rsfmri_preproc/{subject_id}/func/r{slice_timing_output_basename}.nii`
   - 例如 `rasub-001_bold.nii`
5. 可选同时 normalize mean functional image。
6. 输出 normalized functional：
   - `wrasub-001_bold.nii` 或对应 `w*.nii`
7. 输出 SPM normalization result JSON。
8. 生成 normalization QC：
   - deformation field 是否存在
   - input functional 是否存在
   - normalized output 是否存在
   - input shape / output shape
   - input voxel size / output voxel size
   - output affine
   - output finite-value check
   - frames_total
   - target voxel size
   - normalization_qc_status
9. 生成 subject-level normalization QC JSON / Markdown。
10. 生成 dataset-level normalization QC summary / Markdown report。
11. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC → Normalization → Normalization QC
12. 后端 API 暴露 normalization + normalization QC 结果。
13. 前端新增 rs-fMRI Normalization + Normalization QC 面板。
14. 增加轻量 unit test。
15. 更新 README。

本步骤允许调用 SPM，但必须满足：

- 只处理 synthetic BIDS-like 数据。
- 必须 approved=true 才执行 SPM normalization。
- normalization 输入必须来自 derivatives。
- deformation field 必须来自 derivatives 中的 segmentation 输出。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- smoothing
- nuisance regression
- temporal filtering
- ALFF / fALFF / ReHo
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：SPM normalization + normalization QC。

---

## 1. 创建 specs/spm_normalization_qc_spec.md

创建文件：

```text
specs/spm_normalization_qc_spec.md
```

内容：

```markdown
# SPM Normalization and Normalization QC Specification

This document defines the MVP SPM normalization and normalization QC stage for rs-fMRI preprocessing.

## Goals

The goal is to apply the deformation field estimated during SPM segmentation to functional images, producing normalized functional derivatives and lightweight normalization QC metrics.

This step prepares functional images for later smoothing, nuisance regression, temporal filtering, and rs-fMRI metrics.

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM normalize write
- derivative realigned functional input
- derivative deformation field input
- normalized functional output
- optional normalized mean functional output
- subject-level normalization QC JSON / Markdown
- dataset-level normalization QC summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- smoothing
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
derivatives/rsfmri_preproc/{subject_id}/func/r*.nii
derivatives/rsfmri_preproc/{subject_id}/func/mean*.nii
derivatives/rsfmri_preproc/{subject_id}/anat/y_coreg_{subject_id}_T1w.nii
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/wr*.nii
derivatives/rsfmri_preproc/{subject_id}/func/wmean*.nii
derivatives/rsfmri_preproc/{subject_id}/func/spm_normalization_result.json
derivatives/rsfmri_qc/{subject_id}/normalization_qc.json
derivatives/rsfmri_qc/{subject_id}/normalization_qc.md
reports/rsfmri/normalization_qc_summary.json
reports/rsfmri/normalization_qc_report.md
```

## Normalization QC Metrics

- input_exists
- deformation_field_exists
- normalized_output_exists
- input_shape
- normalized_shape
- input_voxel_size
- normalized_voxel_size
- target_voxel_size
- frames_total
- finite_fraction
- normalized_intensity_mean
- normalized_intensity_std
- normalization_qc_status

## Safety Rules

- Execution requires approved=true.
- Only derivative functional input is allowed.
- Only derivative deformation field input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not call DPABI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
```

---

## 2. 创建 matlab/spm_normalize_write_wrapper.m

创建文件：

```text
matlab/spm_normalize_write_wrapper.m
```

功能要求：

1. 接收参数：
   - spm_dir
   - deformation_field
   - input_nii
   - normalize_mean
   - mean_nii
   - voxel_size_json
   - bounding_box_json
   - output_json

2. deformation_field 必须是 derivatives workspace 中 segmentation 输出的 deformation field。
3. input_nii 必须是 derivatives workspace 中 realignment 输出的 functional image。
4. 使用 SPM normalise write。
5. 支持 4D NIfTI functional input。
6. 可选同时 normalize mean functional image。
7. 输出 JSON，记录：
   - ok
   - deformation_field
   - input_nii
   - mean_nii
   - normalized_file
   - normalized_mean_file
   - voxel_size
   - bounding_box
   - output_dir
   - errors
   - warnings
8. 不调用 DPABI。
9. 不调用 DPARSF_run / DPARSFA_run。
10. 不修改 rawdata。
11. 不删除文件。

参考实现：

```matlab
function spm_normalize_write_wrapper(spm_dir, deformation_field, input_nii, normalize_mean, mean_nii, voxel_size_json, bounding_box_json, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_normalize_write_wrapper';
    result.backend = 'matlab-spm';
    result.deformation_field = deformation_field;
    result.input_nii = input_nii;
    result.mean_nii = mean_nii;
    result.normalized_file = '';
    result.normalized_mean_file = '';
    result.output_dir = fileparts(input_nii);
    result.voxel_size = [];
    result.bounding_box = [];
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(deformation_field, 'file')
            error(['Deformation field not found: ', deformation_field]);
        end

        if ~exist(input_nii, 'file')
            error(['Input functional NIfTI not found: ', input_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        voxel_size = jsondecode(voxel_size_json);
        voxel_size = double(voxel_size(:)');
        result.voxel_size = voxel_size;

        bounding_box = jsondecode(bounding_box_json);
        bounding_box = double(bounding_box);
        result.bounding_box = bounding_box;

        vols = spm_vol(input_nii);
        n_frames = numel(vols);

        resample = cell(n_frames, 1);
        for i = 1:n_frames
            resample{i} = [input_nii, ',', num2str(i)];
        end

        if strcmpi(normalize_mean, 'true') && exist(mean_nii, 'file')
            resample{end+1} = [mean_nii, ',1'];
        elseif strcmpi(normalize_mean, 'true')
            result.warnings{end+1} = ['normalize_mean=true but mean_nii not found: ', mean_nii];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.normalise.write.subj.def = {deformation_field};
        matlabbatch{1}.spm.spatial.normalise.write.subj.resample = resample;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.bb = bounding_box;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.vox = voxel_size;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.interp = 4;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.prefix = 'w';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);
        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        normalized_file = fullfile(input_dir, ['w', input_name, '.nii']);
        if exist(normalized_file, 'file')
            result.normalized_file = normalized_file;
        else
            error(['Expected normalized functional file not found: ', normalized_file]);
        end

        if strcmpi(normalize_mean, 'true') && exist(mean_nii, 'file')
            [mean_dir, mean_name, mean_ext] = fileparts(mean_nii);
            if strcmp(mean_ext, '.gz')
                [~, mean_name, ~] = fileparts(mean_name);
            end

            normalized_mean_file = fullfile(mean_dir, ['w', mean_name, '.nii']);
            if exist(normalized_mean_file, 'file')
                result.normalized_mean_file = normalized_mean_file;
            else
                result.warnings{end+1} = ['Expected normalized mean file not found: ', normalized_mean_file];
            end
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

## 3. 创建 backend/app/tools/normalization_qc.py

创建文件：

```text
backend/app/tools/normalization_qc.py
```

目标：根据 functional input、deformation field、normalized output 计算 lightweight normalization QC。

提供函数：

```python
compute_normalization_qc_for_subject(
    subject_id: str,
    input_nii: str,
    deformation_field: str,
    normalized_nii: str,
    derivatives_dir: str,
    target_voxel_size: list[float] | None = None,
    finite_fraction_warning: float = 0.95,
) -> dict

write_normalization_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. 使用 nibabel 读取 header / affine。
2. 可以读取 small synthetic normalized data，用于 finite check 和 intensity summary。
3. 计算：
   - input shape
   - normalized shape
   - input voxel size
   - normalized voxel size
   - frames_total
   - finite_fraction
   - intensity mean/std
4. QC 状态：
   - input / deformation / normalized 缺失 → FAIL
   - normalized finite_fraction < threshold → WARNING
   - normalized voxel size 与 target voxel size 差异明显 → WARNING
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


def _voxel_size_close(actual: list[float], target: list[float], tolerance: float = 0.2) -> bool:
    if len(actual) < 3 or len(target) < 3:
        return False
    return all(abs(float(a) - float(t)) <= tolerance for a, t in zip(actual[:3], target[:3]))


def compute_normalization_qc_for_subject(
    subject_id: str,
    input_nii: str,
    deformation_field: str,
    normalized_nii: str,
    derivatives_dir: str,
    target_voxel_size: list[float] | None = None,
    finite_fraction_warning: float = 0.95,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "normalization_qc.json"
    qc_md = out_dir / "normalization_qc.md"

    target_voxel_size = target_voxel_size or [3.0, 3.0, 3.0]

    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    deformation_path = Path(deformation_field)
    normalized_path = Path(normalized_nii)

    missing = [
        str(path)
        for path in [input_path, deformation_path, normalized_path]
        if not path.exists()
    ]

    if missing:
        result = {
            "ok": False,
            "node_id": "normalization_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "normalization_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            input_stats = _load_nifti_stats(input_path)
            normalized_stats = _load_nifti_stats(normalized_path)

            status = "PASS"

            if normalized_stats["finite_fraction"] < finite_fraction_warning:
                status = "WARNING"
                warnings.append(
                    f"Finite fraction {normalized_stats['finite_fraction']:.4f} below threshold {finite_fraction_warning}."
                )

            if not _voxel_size_close(normalized_stats["voxel_size"], target_voxel_size):
                status = "WARNING"
                warnings.append(
                    f"Normalized voxel size {normalized_stats['voxel_size']} differs from target {target_voxel_size}."
                )

            result = {
                "ok": True,
                "node_id": "normalization_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "input_nii": str(input_path),
                "deformation_field": str(deformation_path),
                "normalized_nii": str(normalized_path),
                "input_shape": input_stats["shape"],
                "normalized_shape": normalized_stats["shape"],
                "input_voxel_size": input_stats["voxel_size"],
                "normalized_voxel_size": normalized_stats["voxel_size"],
                "target_voxel_size": target_voxel_size,
                "frames_total": normalized_stats["frames_total"],
                "finite_fraction": normalized_stats["finite_fraction"],
                "normalized_intensity_mean": normalized_stats["intensity_mean"],
                "normalized_intensity_std": normalized_stats["intensity_std"],
                "normalization_qc_status": status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "normalization_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "normalization_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Normalization QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('normalization_qc_status')}")
    lines.append(f"- Input: `{result.get('input_nii')}`")
    lines.append(f"- Deformation field: `{result.get('deformation_field')}`")
    lines.append(f"- Normalized: `{result.get('normalized_nii')}`")
    lines.append(f"- Input shape: {result.get('input_shape')}")
    lines.append(f"- Normalized shape: {result.get('normalized_shape')}")
    lines.append(f"- Normalized voxel size: {result.get('normalized_voxel_size')}")
    lines.append(f"- Finite fraction: {result.get('finite_fraction')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Normalization QC reads derivative files only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_normalization_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/normalization_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid normalization QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("normalization_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("normalization_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("normalization_qc_status") == "FAIL")

    finite_fractions = [
        float(item["finite_fraction"])
        for item in subjects
        if item.get("finite_fraction") is not None
    ]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "normalization_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_finite_fraction": float(mean(finite_fractions)) if finite_fractions else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "normalization_qc_summary.json"
    report_path = report_out / "normalization_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Normalization QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean finite fraction: {summary['mean_finite_fraction']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Shape | Voxel Size | Finite Fraction |")
    lines.append("|---|---|---|---|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('normalization_qc_status')} | "
            f"{item.get('normalized_shape')} | {item.get('normalized_voxel_size')} | "
            f"{item.get('finite_fraction')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative normalization QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "normalization_qc_dataset_report",
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

## 4. 创建 backend/app/tools/spm_normalize_runner.py

创建文件：

```text
backend/app/tools/spm_normalize_runner.py
```

目标：Python 调用 MATLAB SPM normalize write wrapper。

提供函数：

```python
run_spm_normalize_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    voxel_size: list[float] | None = None,
    bounding_box: list[list[float]] | None = None,
    normalize_mean: bool = True,
    matlab_script_dir: str = "./matlab",
) -> dict
```

实现要求：

1. approved=false 时安全失败，不启动 MATLAB。
2. functional input 必须来自：

```text
derivatives/rsfmri_preproc/{subject_id}/func/r*.nii
```

优先选择：

```text
derivatives/rsfmri_preproc/{subject_id}/func/rasub-001_bold.nii
```

或任意 `r*.nii`，但不能选择 `rp_*.txt`、`mean*.nii`、`wr*.nii`。

3. deformation field 必须是：

```text
derivatives/rsfmri_preproc/{subject_id}/anat/y_coreg_{subject_id}_T1w.nii
```

4. mean functional 可选：
   - `derivatives/rsfmri_preproc/{subject_id}/func/mean*.nii`
5. 调用 `spm_normalize_write_wrapper.m`。
6. 调用 `compute_normalization_qc_for_subject`。
7. 输出：
   - `wr*.nii`
   - `wmean*.nii`
   - `spm_normalization_result.json`
   - `normalization_qc.json`
   - stdout / stderr logs
8. 不使用 shell=True。
9. 不调用 DPABI。
10. 不调用 DPARSF_run / DPARSFA_run。

参考实现：

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from backend.app.tools.normalization_qc import compute_normalization_qc_for_subject


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _expected_deformation_field(subject_id: str, derivatives_dir: str) -> Path:
    return (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "anat"
        / f"y_coreg_{subject_id}_T1w.nii"
    )


def _find_realign_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    preferred = func_dir / f"ra{subject_id}_bold.nii"
    if preferred.exists():
        return preferred

    candidates = []
    for path in sorted(func_dir.glob("r*.nii")):
        name = path.name
        if name.startswith("rp_"):
            continue
        if name.startswith("mean"):
            continue
        if name.startswith("wr"):
            continue
        candidates.append(path)

    return candidates[0] if candidates else None


def _find_mean_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    candidates = sorted(func_dir.glob("mean*.nii"))
    return candidates[0] if candidates else None


def _is_safe_functional_input(path: Path, subject_id: str, derivatives_dir: str) -> bool:
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
        name.startswith("r")
        and name.endswith(".nii")
        and not name.startswith("rp_")
        and not name.startswith("mean")
        and not name.startswith("wr")
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_spm_normalize_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    voxel_size: list[float] | None = None,
    bounding_box: list[list[float]] | None = None,
    normalize_mean: bool = True,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_normalize_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM normalization requires approved=true."],
        }

    voxel_size = voxel_size or [3.0, 3.0, 3.0]
    bounding_box = bounding_box or [[-90.0, -126.0, -72.0], [90.0, 90.0, 108.0]]

    deformation_field = _expected_deformation_field(subject_id, derivatives_dir)
    if not deformation_field.exists():
        return {
            "ok": False,
            "node_id": "spm_normalize_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Expected deformation field not found: {deformation_field}"],
        }

    input_func = _find_realign_functional(subject_id, derivatives_dir)
    if not input_func:
        return {
            "ok": False,
            "node_id": "spm_normalize_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                f"No realigned functional input found under derivatives/rsfmri_preproc/{subject_id}/func."
            ],
        }

    if not _is_safe_functional_input(input_func, subject_id, derivatives_dir):
        return {
            "ok": False,
            "node_id": "spm_normalize_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsafe normalization functional input: {input_func}"],
        }

    mean_func = _find_mean_functional(subject_id, derivatives_dir)
    mean_func_text = str(mean_func) if mean_func else ""

    func_dir = input_func.parent

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_normalize_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_normalize_stderr.log"
    result_json = func_dir / "spm_normalization_result.json"

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_normalize_write_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(deformation_field.resolve()))}', "
        f"'{_matlab_quote(str(input_func.resolve()))}', "
        f"'{str(bool(normalize_mean)).lower()}', "
        f"'{_matlab_quote(str(Path(mean_func_text).resolve()) if mean_func_text else '')}', "
        f"'{_matlab_quote(json.dumps(voxel_size))}', "
        f"'{_matlab_quote(json.dumps(bounding_box))}', "
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
        "errors": ["SPM normalization did not produce result JSON."],
    }

    data["node_id"] = "spm_normalize_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["input_func"] = str(input_func)
    data["deformation_field"] = str(deformation_field)
    data["mean_func"] = mean_func_text
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    qc_outputs = []
    normalized_file = data.get("normalized_file")

    if normalized_file:
        qc = compute_normalization_qc_for_subject(
            subject_id=subject_id,
            input_nii=str(input_func),
            deformation_field=str(deformation_field),
            normalized_nii=normalized_file,
            derivatives_dir=derivatives_dir,
            target_voxel_size=voxel_size,
        )
        data["normalization_qc"] = qc
        qc_outputs = qc.get("outputs", [])

    outputs = []
    if data.get("normalized_file"):
        outputs.append(data["normalized_file"])
    if data.get("normalized_mean_file"):
        outputs.append(data["normalized_mean_file"])

    outputs.extend(qc_outputs)
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
```

---

## 5. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
spm_normalize_subject
normalization_qc_dataset_report
```

新增导入：

```python
from backend.app.tools.spm_normalize_runner import run_spm_normalize_subject
from backend.app.tools.normalization_qc import write_normalization_qc_dataset_report
```

新增 runner：

```python
def run_spm_normalize_subject_node(
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

    result = run_spm_normalize_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        voxel_size=node.params.get("voxel_size", [3.0, 3.0, 3.0]),
        bounding_box=node.params.get("bounding_box"),
        normalize_mean=bool(node.params.get("normalize_mean", True)),
        matlab_script_dir="./matlab",
    )

    result["node_id"] = node.id
    return result


def run_normalization_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_normalization_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"spm_normalize_subject": run_spm_normalize_subject_node,
"normalization_qc_dataset_report": run_normalization_qc_dataset_report_node,
```

---

## 6. 创建 examples/pipeline_rsfmri_normalization_qc.yaml

创建文件：

```text
examples/pipeline_rsfmri_normalization_qc.yaml
```

内容：

```yaml
pipeline_id: rsfmri_normalization_qc_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run approved SPM normalization using segmentation deformation field and compute normalization QC."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_normalization_qc_001"
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
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。

---

## 7. 创建 backend/app/tools/run_rsfmri_normalization_qc_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_normalization_qc_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_normalization_qc.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("outputs/work/rsfmri/approved_pipeline_normalization_qc.yaml"),
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
class RsfmriNormalizationQcRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_normalization_qc.yaml")
    approved: bool = Field(default=False)
```

---

## 9. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/normalization-qc/run
GET  /api/rsfmri/normalization-qc
```

新增导入：

```python
from backend.app.api.models import RsfmriNormalizationQcRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_normalization_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
            "spm_segment_subject",
            "spm_normalize_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target
```

新增路由：

```python
@router.post("/api/rsfmri/normalization-qc/run")
def api_run_rsfmri_normalization_qc(
    request: RsfmriNormalizationQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM normalization QC pipeline requires approved=true.",
        )

    try:
        approved_pipeline = _make_normalization_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("outputs/work/rsfmri/approved_pipeline_normalization_qc.yaml"),
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


@router.get("/api/rsfmri/normalization-qc")
def api_get_rsfmri_normalization_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_normalization_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/normalization_qc.json")):
        subject_normalization_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "normalization_qc_summary": _read_json_if_exists(report_base / "normalization_qc_summary.json"),
        "normalization_qc_report": _read_text_if_exists(report_base / "normalization_qc_report.md"),
        "subject_normalization_qc": subject_normalization_qc,
    }
```

---

## 10. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriNormalizationQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/normalization-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriNormalizationQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/normalization-qc"
  );
}
```

---

## 11. 创建 frontend/src/components/RsfmriNormalizationQcPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriNormalizationQcPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriNormalizationQc,
  runRsfmriNormalizationQc
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriNormalizationQcPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 SPM Normalization + Normalization QC？这只处理 synthetic BIDS 数据，不会修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriNormalizationQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_normalization_qc.yaml",
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
      const response = await getRsfmriNormalizationQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.normalization_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Normalization + Normalization QC
        </button>
        <button onClick={handleLoad}>加载 Normalization QC 结果</button>
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
          <span>Mean Finite Fraction</span>
          <strong>
            {summary?.mean_finite_fraction == null
              ? "-"
              : Number(summary.mean_finite_fraction).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Normalization QC Summary</h3>
      <JsonBlock value={loaded?.normalization_qc_summary} emptyText="暂无 normalization QC summary" />

      <h3>Subject Normalization QC</h3>
      <JsonBlock value={loaded?.subject_normalization_qc} emptyText="暂无 subject normalization QC" />

      <h3>Normalization QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.normalization_qc_report === "string"
            ? loaded.normalization_qc_report
            : null
        }
        emptyText="暂无 normalization QC report"
      />
    </div>
  );
}
```

---

## 12. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriNormalizationQcPanel } from "./components/RsfmriNormalizationQcPanel";
```

在 `rs-fMRI SPM Segmentation + Tissue QC` 后新增 Section：

```tsx
<Section
  title="rs-fMRI SPM Normalization + Normalization QC"
  description="使用 segmentation deformation field 对 realigned functional image 执行 SPM normalization，并生成 normalization QC。"
>
  <RsfmriNormalizationQcPanel baseUrl={baseUrl} />
</Section>
```

---

## 13. 新增轻量测试

创建文件：

```text
tests/unit/test_normalization_qc.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.normalization_qc import compute_normalization_qc_for_subject


def test_normalization_qc_computes_output_metrics(tmp_path: Path):
    derivatives = tmp_path / "derivatives"

    input_func = tmp_path / "rasub-001_bold.nii"
    deformation = tmp_path / "y_coreg_sub-001_T1w.nii"
    normalized = tmp_path / "wrasub-001_bold.nii"

    affine_input = np.eye(4)
    affine_norm = np.diag([3.0, 3.0, 3.0, 1.0])

    input_data = np.ones((4, 4, 4, 5), dtype=np.float32)
    normalized_data = np.ones((6, 6, 6, 5), dtype=np.float32)

    nib.save(nib.Nifti1Image(input_data, affine_input), str(input_func))
    nib.save(nib.Nifti1Image(np.zeros((4, 4, 4, 1, 3), dtype=np.float32), affine_input), str(deformation))
    nib.save(nib.Nifti1Image(normalized_data, affine_norm), str(normalized))

    result = compute_normalization_qc_for_subject(
        subject_id="sub-001",
        input_nii=str(input_func),
        deformation_field=str(deformation),
        normalized_nii=str(normalized),
        derivatives_dir=str(derivatives),
        target_voxel_size=[3.0, 3.0, 3.0],
    )

    assert result["ok"] is True
    assert result["normalization_qc_status"] == "PASS"
    assert result["frames_total"] == 5
    assert result["finite_fraction"] == 1.0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "normalization_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
```

---

## 14. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/normalization-qc")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 15. 更新 README.md

追加第四十步说明：

```markdown
## Step 40: SPM Normalization and Normalization QC

This step implements SPM normalize write using the deformation field produced by segmentation.

It supports:

- approved SPM normalization
- derivative realigned functional input only
- derivative segmentation deformation field input only
- normalized functional output
- optional normalized mean functional output
- normalization QC metrics
- subject-level normalization QC
- dataset-level normalization QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_normalization_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_normalization_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_normalization_qc.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_preproc/sub-001/func/wrasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/wmeanasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/spm_normalization_result.json
derivatives/rsfmri_qc/sub-001/normalization_qc.json
derivatives/rsfmri_qc/sub-001/normalization_qc.md
reports/rsfmri/normalization_qc_summary.json
reports/rsfmri/normalization_qc_report.md
work/pipeline_runs/run_rsfmri_normalization_qc_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/normalization-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/normalization-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_normalization_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI SPM Normalization + Normalization QC
```

### Safety

This step:

- requires approved=true
- only processes derivative functional input
- only uses derivative deformation field input
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
specs/spm_normalization_qc_spec.md
matlab/spm_normalize_write_wrapper.m
backend/app/tools/normalization_qc.py
backend/app/tools/spm_normalize_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_normalization_qc.yaml
backend/app/tools/run_rsfmri_normalization_qc_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriNormalizationQcPanel.tsx
frontend/src/App.tsx
tests/unit/test_normalization_qc.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_normalization_qc_cli
```

应该安全失败，不应启动 SPM normalization。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_normalization_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_normalization_qc.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_preproc/sub-001/func/wrasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/spm_normalization_result.json
derivatives/rsfmri_qc/sub-001/normalization_qc.json
reports/rsfmri/normalization_qc_summary.json
reports/rsfmri/normalization_qc_report.md
```

normalization QC JSON 必须包含：

```json
{
  "node_id": "normalization_qc_subject",
  "subject_id": "sub-001",
  "normalization_qc_status": "PASS",
  "input_shape": [],
  "normalized_shape": [],
  "normalized_voxel_size": [3.0, 3.0, 3.0],
  "finite_fraction": 1.0
}
```

实际数值根据 synthetic 数据和 SPM 输出决定。

运行测试：

```bash
python -m pytest tests/unit/test_normalization_qc.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/normalization-qc

curl -X POST http://127.0.0.1:8000/api/rsfmri/normalization-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/normalization-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI SPM Normalization + Normalization QC 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 normalization QC 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean finite fraction。
8. 显示 normalization QC summary JSON。
9. 显示 subject normalization QC JSON。
10. 显示 normalization QC Markdown report。
11. 不修改 rawdata。
12. 不运行 DPABI。
13. 不调用 DPARSF_run / DPARSFA_run。
14. 不执行完整 preprocessing。

---

## 17. 重要限制

本步骤只做 SPM normalization + normalization QC。

不要实现：

- smoothing
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
3. SPM normalize write wrapper 如何工作
4. deformation field 和 functional input 如何保证来自 derivatives
5. normalization QC 如何计算
6. 输出哪些 derivatives 和 reports
7. 为什么本步骤仍然不是完整 preprocessing
8. 下一步如何实现 SPM Smoothing + Smoothing QC，并把 normalized functional 接入 smoothing

```
这一步给预处理流水线加上了空间标准化。

**写了 SPM normalize write wrapper。** `spm_normalize_write_wrapper.m` 拿 segmentation 产出的 deformation field（`y_coreg_*.nii`），对 realignment 产出的功能像（`r*.nii`，优先找 `ra{subject}_bold.nii`）做 `spm.spatial.normalise.write`，输出前缀 `w` 的标准化图像。同时可选地把 mean functional 也标准化。

**写了 normalization QC 模块。** `normalization_qc.py` 读标准化前后的 NIfTI，检查 finite fraction（非 NaN/Inf 体素占比，低于 95% 标 WARNING）、输出体素尺寸是否接近目标（3mm iso，差异超 0.2mm 标 WARNING）、以及 intensity 均值和标准差。

**输入安全靠路径规则。** runner 扫描 `func/` 目录下 `r*.nii` 文件，排除 `rp_*`（头动参数）、`mean*`（平均像）、`wr*`（已标准化的），只认来自 derivatives 的合法功能像。deformation field 必须是精确预期路径，不走 rawdata。

目前预处理链是 5 个 SPM 阶段 + 5 个 QC 阶段共 11 个节点：synthetic BOLD → slice timing → realignment → motion QC → coregistration → registration QC → segmentation → tissue QC → normalization → normalization QC。
```
