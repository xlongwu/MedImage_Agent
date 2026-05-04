你是我的工程搭建助手。前三十八步已经完成：

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

现在开始第三十九步。

第三十九步目标：实现 “SPM Segmentation + Tissue QC 闭环”。

当前系统已经可以完成：

synthetic raw BOLD
→ SPM slice timing correction
→ SPM realignment
→ motion QC
→ SPM coregistration
→ registration QC

但还缺少 T1w 结构像组织分割步骤。  
本步骤要继续深入 rs-fMRI 核心预处理，实现：

coregistered T1w
→ SPM segmentation
→ GM / WM / CSF tissue probability maps
→ deformation field
→ tissue QC
→ subject-level segmentation report
→ dataset-level tissue QC report

本步骤要实现：

1. SPM segmentation wrapper。
2. 对 synthetic BIDS-like T1w derivative 执行 SPM segmentation。
3. 使用 coregistration 输出的 `coreg_{subject_id}_T1w.nii` 作为 segmentation input。
4. 输出 GM / WM / CSF tissue maps。
5. 输出 deformation field。
6. 输出 SPM segmentation result JSON。
7. 生成 tissue QC：
   - GM / WM / CSF 文件是否存在
   - deformation field 是否存在
   - tissue map shape
   - tissue map voxel size
   - tissue intensity summary
   - tissue voxel count
   - tissue volume estimate
   - segmentation_qc_status
8. 生成 subject-level tissue QC JSON / Markdown。
9. 生成 dataset-level tissue QC summary / Markdown report。
10. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC
11. 后端 API 暴露 segmentation + tissue QC 结果。
12. 前端新增 rs-fMRI Segmentation + Tissue QC 面板。
13. 增加轻量 unit test。
14. 更新 README。

本步骤允许调用 SPM，但必须满足：

- 只处理 synthetic BIDS-like 数据。
- 必须 approved=true 才执行 SPM segmentation。
- segmentation 输入必须是 derivatives 中的 coregistered T1w。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- normalization
- smoothing
- nuisance regression
- temporal filtering
- ALFF / fALFF / ReHo
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：SPM segmentation + tissue QC。

---

## 1. 创建 specs/spm_segmentation_tissue_qc_spec.md

创建文件：

```text
specs/spm_segmentation_tissue_qc_spec.md
```

内容：

```markdown
# SPM Segmentation and Tissue QC Specification

This document defines the MVP SPM segmentation and tissue QC stage for rs-fMRI preprocessing.

## Goals

The goal is to segment the coregistered anatomical T1w image into tissue probability maps and compute lightweight tissue QC metrics.

This step prepares tissue maps and deformation fields for later nuisance regression and normalization.

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM segmentation
- derivative coregistered T1w input
- GM / WM / CSF tissue probability maps
- deformation field output
- subject-level tissue QC JSON / Markdown
- dataset-level tissue QC summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- normalization
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
derivatives/rsfmri_preproc/{subject_id}/anat/coreg_{subject_id}_T1w.nii
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_preproc/{subject_id}/anat/c1coreg_{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/c2coreg_{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/c3coreg_{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/y_coreg_{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/spm_segmentation_result.json
derivatives/rsfmri_qc/{subject_id}/tissue_qc.json
derivatives/rsfmri_qc/{subject_id}/tissue_qc.md
reports/rsfmri/tissue_qc_summary.json
reports/rsfmri/tissue_qc_report.md
```

## Tissue QC Metrics

- gm_exists
- wm_exists
- csf_exists
- deformation_field_exists
- gm_shape
- wm_shape
- csf_shape
- gm_voxel_size
- wm_voxel_size
- csf_voxel_size
- gm_mean
- wm_mean
- csf_mean
- gm_voxel_count
- wm_voxel_count
- csf_voxel_count
- gm_volume_mm3
- wm_volume_mm3
- csf_volume_mm3
- segmentation_qc_status

## Safety Rules

- Execution requires approved=true.
- Only derivative coregistered T1w input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not call DPABI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
```

---

## 2. 创建 matlab/spm_segment_wrapper.m

创建文件：

```text
matlab/spm_segment_wrapper.m
```

功能要求：

1. 接收参数：
   - spm_dir
   - input_t1w
   - output_json

2. input_t1w 必须是 derivatives workspace 中的 coregistered T1w，不直接处理 rawdata。
3. 添加 SPM 路径。
4. 使用 SPM segmentation。
5. 输出 GM / WM / CSF tissue probability maps。
6. 输出 deformation field。
7. 输出 JSON，记录：
   - ok
   - input_t1w
   - output_dir
   - gm_file
   - wm_file
   - csf_file
   - deformation_field
   - native_tissue_files
   - errors
   - warnings
8. 不调用 DPABI。
9. 不调用 DPARSF_run / DPARSFA_run。
10. 不修改 rawdata。
11. 不删除文件。

参考实现：

```matlab
function spm_segment_wrapper(spm_dir, input_t1w, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_segment_wrapper';
    result.backend = 'matlab-spm';
    result.input_t1w = input_t1w;
    result.output_dir = fileparts(input_t1w);
    result.gm_file = '';
    result.wm_file = '';
    result.csf_file = '';
    result.deformation_field = '';
    result.native_tissue_files = {};
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_t1w, 'file')
            error(['Input T1w not found: ', input_t1w]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        tpm_path = fullfile(spm_dir, 'tpm', 'TPM.nii');
        if ~exist(tpm_path, 'file')
            error(['SPM TPM not found: ', tpm_path]);
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.preproc.channel.vols = {[input_t1w, ',1']};
        matlabbatch{1}.spm.spatial.preproc.channel.biasreg = 0.001;
        matlabbatch{1}.spm.spatial.preproc.channel.biasfwhm = 60;
        matlabbatch{1}.spm.spatial.preproc.channel.write = [0 0];

        for tissue_index = 1:6
            matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).tpm = ...
                {[tpm_path, ',', num2str(tissue_index)]};

            if tissue_index <= 3
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).ngaus = tissue_index;
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).native = [1 0];
            else
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).ngaus = 2;
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).native = [0 0];
            end

            matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).warped = [0 0];
        end

        matlabbatch{1}.spm.spatial.preproc.warp.mrf = 1;
        matlabbatch{1}.spm.spatial.preproc.warp.cleanup = 1;
        matlabbatch{1}.spm.spatial.preproc.warp.reg = [0 0.001 0.5 0.05 0.2];
        matlabbatch{1}.spm.spatial.preproc.warp.affreg = 'mni';
        matlabbatch{1}.spm.spatial.preproc.warp.fwhm = 0;
        matlabbatch{1}.spm.spatial.preproc.warp.samp = 3;
        matlabbatch{1}.spm.spatial.preproc.warp.write = [0 1];

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_t1w);
        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        gm_file = fullfile(input_dir, ['c1', input_name, '.nii']);
        wm_file = fullfile(input_dir, ['c2', input_name, '.nii']);
        csf_file = fullfile(input_dir, ['c3', input_name, '.nii']);
        deformation_field = fullfile(input_dir, ['y_', input_name, '.nii']);

        if exist(gm_file, 'file')
            result.gm_file = gm_file;
            result.native_tissue_files{end+1} = gm_file;
        else
            result.warnings{end+1} = ['Expected GM file not found: ', gm_file];
        end

        if exist(wm_file, 'file')
            result.wm_file = wm_file;
            result.native_tissue_files{end+1} = wm_file;
        else
            result.warnings{end+1} = ['Expected WM file not found: ', wm_file];
        end

        if exist(csf_file, 'file')
            result.csf_file = csf_file;
            result.native_tissue_files{end+1} = csf_file;
        else
            result.warnings{end+1} = ['Expected CSF file not found: ', csf_file];
        end

        if exist(deformation_field, 'file')
            result.deformation_field = deformation_field;
        else
            result.warnings{end+1} = ['Expected deformation field not found: ', deformation_field];
        end

        if isempty(result.gm_file) || isempty(result.wm_file) || isempty(result.csf_file)
            error('SPM segmentation did not produce required tissue maps.');
        end

        if isempty(result.deformation_field)
            error('SPM segmentation did not produce deformation field.');
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

## 3. 创建 backend/app/tools/tissue_qc.py

创建文件：

```text
backend/app/tools/tissue_qc.py
```

目标：根据 GM / WM / CSF tissue maps 和 deformation field 计算 lightweight tissue QC。

提供函数：

```python
compute_tissue_qc_for_subject(
    subject_id: str,
    gm_file: str,
    wm_file: str,
    csf_file: str,
    deformation_field: str,
    derivatives_dir: str,
    probability_threshold: float = 0.2,
) -> dict

write_tissue_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. 使用 nibabel 读取 tissue map。
2. tissue QC 可以读取 tissue map 数据，因为 synthetic 数据很小；后续真实数据再做采样优化。
3. 计算：
   - shape
   - voxel size
   - mean probability
   - max probability
   - voxel_count over threshold
   - volume estimate
4. QC 状态：
   - 任一 tissue map 缺失 → FAIL
   - deformation field 缺失 → FAIL
   - tissue map shape 不一致 → FAIL
   - 三个 tissue map voxel_count 都为 0 → WARNING
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


def _load_tissue_stats(path: Path, probability_threshold: float) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    img = nib.load(str(path))
    data = img.get_fdata(dtype="float32")
    zooms = list(img.header.get_zooms()[:3])
    voxel_volume = float(zooms[0] * zooms[1] * zooms[2])

    mask = data > probability_threshold
    voxel_count = int(np.count_nonzero(mask))

    return {
        "path": str(path),
        "shape": list(data.shape),
        "voxel_size": [float(x) for x in zooms],
        "mean_probability": float(np.mean(data)),
        "max_probability": float(np.max(data)),
        "voxel_count_over_threshold": voxel_count,
        "volume_mm3": float(voxel_count * voxel_volume),
    }


def compute_tissue_qc_for_subject(
    subject_id: str,
    gm_file: str,
    wm_file: str,
    csf_file: str,
    deformation_field: str,
    derivatives_dir: str,
    probability_threshold: float = 0.2,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "tissue_qc.json"
    qc_md = out_dir / "tissue_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    gm_path = Path(gm_file)
    wm_path = Path(wm_file)
    csf_path = Path(csf_file)
    deformation_path = Path(deformation_field)

    missing = [
        str(path)
        for path in [gm_path, wm_path, csf_path, deformation_path]
        if not path.exists()
    ]

    if missing:
        result = {
            "ok": False,
            "node_id": "tissue_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "segmentation_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            gm = _load_tissue_stats(gm_path, probability_threshold)
            wm = _load_tissue_stats(wm_path, probability_threshold)
            csf = _load_tissue_stats(csf_path, probability_threshold)

            shapes = {tuple(gm["shape"]), tuple(wm["shape"]), tuple(csf["shape"])}

            if len(shapes) != 1:
                status = "FAIL"
                errors.append("Tissue map shapes are inconsistent.")
            elif (
                gm["voxel_count_over_threshold"] == 0
                and wm["voxel_count_over_threshold"] == 0
                and csf["voxel_count_over_threshold"] == 0
            ):
                status = "WARNING"
                warnings.append("All tissue maps have zero voxels above threshold.")
            else:
                status = "PASS"

            result = {
                "ok": status != "FAIL",
                "node_id": "tissue_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "gm_file": str(gm_path),
                "wm_file": str(wm_path),
                "csf_file": str(csf_path),
                "deformation_field": str(deformation_path),
                "probability_threshold": probability_threshold,
                "gm_stats": gm,
                "wm_stats": wm,
                "csf_stats": csf,
                "gm_volume_mm3": gm["volume_mm3"],
                "wm_volume_mm3": wm["volume_mm3"],
                "csf_volume_mm3": csf["volume_mm3"],
                "segmentation_qc_status": status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "tissue_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "segmentation_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Tissue QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('segmentation_qc_status')}")
    lines.append(f"- GM volume mm3: {result.get('gm_volume_mm3')}")
    lines.append(f"- WM volume mm3: {result.get('wm_volume_mm3')}")
    lines.append(f"- CSF volume mm3: {result.get('csf_volume_mm3')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Tissue QC reads derivative tissue maps only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_tissue_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/tissue_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid tissue QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("segmentation_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("segmentation_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("segmentation_qc_status") == "FAIL")

    gm_volumes = [float(item["gm_volume_mm3"]) for item in subjects if item.get("gm_volume_mm3") is not None]
    wm_volumes = [float(item["wm_volume_mm3"]) for item in subjects if item.get("wm_volume_mm3") is not None]
    csf_volumes = [float(item["csf_volume_mm3"]) for item in subjects if item.get("csf_volume_mm3") is not None]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "tissue_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_gm_volume_mm3": float(mean(gm_volumes)) if gm_volumes else None,
        "mean_wm_volume_mm3": float(mean(wm_volumes)) if wm_volumes else None,
        "mean_csf_volume_mm3": float(mean(csf_volumes)) if csf_volumes else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "tissue_qc_summary.json"
    report_path = report_out / "tissue_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Tissue QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean GM volume mm3: {summary['mean_gm_volume_mm3']}")
    lines.append(f"- Mean WM volume mm3: {summary['mean_wm_volume_mm3']}")
    lines.append(f"- Mean CSF volume mm3: {summary['mean_csf_volume_mm3']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | GM Volume | WM Volume | CSF Volume |")
    lines.append("|---|---|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('segmentation_qc_status')} | "
            f"{item.get('gm_volume_mm3')} | {item.get('wm_volume_mm3')} | "
            f"{item.get('csf_volume_mm3')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative tissue QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "tissue_qc_dataset_report",
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

## 4. 创建 backend/app/tools/spm_segment_runner.py

创建文件：

```text
backend/app/tools/spm_segment_runner.py
```

目标：Python 调用 MATLAB SPM segmentation wrapper。

提供函数：

```python
run_spm_segment_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict
```

实现要求：

1. approved=false 时安全失败，不启动 MATLAB。
2. segmentation input 必须是：

```text
derivatives/rsfmri_preproc/{subject_id}/anat/coreg_{subject_id}_T1w.nii
```

3. input 必须存在。
4. 不接受 rawdata T1w。
5. 调用 `spm_segment_wrapper.m`。
6. 调用 `compute_tissue_qc_for_subject`。
7. 输出：
   - c1coreg_*.nii
   - c2coreg_*.nii
   - c3coreg_*.nii
   - y_coreg_*.nii
   - spm_segmentation_result.json
   - tissue_qc.json
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

from backend.app.tools.tissue_qc import compute_tissue_qc_for_subject


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _expected_coreg_t1w(subject_id: str, derivatives_dir: str) -> Path:
    return (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "anat"
        / f"coreg_{subject_id}_T1w.nii"
    )


def _is_safe_coreg_t1w(input_t1w: Path, subject_id: str, derivatives_dir: str) -> bool:
    return input_t1w.resolve() == _expected_coreg_t1w(subject_id, derivatives_dir).resolve()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_spm_segment_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_segment_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM segmentation requires approved=true."],
        }

    input_t1w = _expected_coreg_t1w(subject_id, derivatives_dir)

    if not input_t1w.exists():
        return {
            "ok": False,
            "node_id": "spm_segment_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Expected coregistered T1w not found: {input_t1w}"],
        }

    if not _is_safe_coreg_t1w(input_t1w, subject_id, derivatives_dir):
        return {
            "ok": False,
            "node_id": "spm_segment_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsafe segmentation input: {input_t1w}"],
        }

    anat_dir = input_t1w.parent

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_segment_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_segment_stderr.log"
    result_json = anat_dir / "spm_segmentation_result.json"

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_segment_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(input_t1w.resolve()))}', "
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
        "errors": ["SPM segmentation did not produce result JSON."],
    }

    data["node_id"] = "spm_segment_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["input_t1w"] = str(input_t1w)
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    qc_outputs = []
    if data.get("gm_file") and data.get("wm_file") and data.get("csf_file") and data.get("deformation_field"):
        qc = compute_tissue_qc_for_subject(
            subject_id=subject_id,
            gm_file=data["gm_file"],
            wm_file=data["wm_file"],
            csf_file=data["csf_file"],
            deformation_field=data["deformation_field"],
            derivatives_dir=derivatives_dir,
        )
        data["tissue_qc"] = qc
        qc_outputs = qc.get("outputs", [])

    outputs = []
    for key in ["gm_file", "wm_file", "csf_file", "deformation_field"]:
        if data.get(key):
            outputs.append(data[key])

    outputs.extend(qc_outputs)
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
```

---

## 5. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
spm_segment_subject
tissue_qc_dataset_report
```

新增导入：

```python
from backend.app.tools.spm_segment_runner import run_spm_segment_subject
from backend.app.tools.tissue_qc import write_tissue_qc_dataset_report
```

新增 runner：

```python
def run_spm_segment_subject_node(
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

    result = run_spm_segment_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        matlab_script_dir="./matlab",
    )

    result["node_id"] = node.id
    return result


def run_tissue_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_tissue_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"spm_segment_subject": run_spm_segment_subject_node,
"tissue_qc_dataset_report": run_tissue_qc_dataset_report_node,
```

---

## 6. 创建 examples/pipeline_rsfmri_segmentation_tissue_qc.yaml

创建文件：

```text
examples/pipeline_rsfmri_segmentation_tissue_qc.yaml
```

内容：

```yaml
pipeline_id: rsfmri_segmentation_tissue_qc_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run approved SPM segmentation on coregistered synthetic T1w and compute tissue QC."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_segmentation_tissue_qc_001"
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
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。

---

## 7. 创建 backend/app/tools/run_rsfmri_segmentation_tissue_qc_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_segmentation_tissue_qc_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_segmentation_tissue_qc.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("outputs/work/rsfmri/approved_pipeline_segmentation_tissue_qc.yaml"),
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
class RsfmriSegmentationTissueQcRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_segmentation_tissue_qc.yaml")
    approved: bool = Field(default=False)
```

---

## 9. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/segmentation-tissue-qc/run
GET  /api/rsfmri/segmentation-tissue-qc
```

新增导入：

```python
from backend.app.api.models import RsfmriSegmentationTissueQcRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_segmentation_tissue_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
            "spm_segment_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target
```

新增路由：

```python
@router.post("/api/rsfmri/segmentation-tissue-qc/run")
def api_run_rsfmri_segmentation_tissue_qc(
    request: RsfmriSegmentationTissueQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM segmentation tissue QC pipeline requires approved=true.",
        )

    try:
        approved_pipeline = _make_segmentation_tissue_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("outputs/work/rsfmri/approved_pipeline_segmentation_tissue_qc.yaml"),
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


@router.get("/api/rsfmri/segmentation-tissue-qc")
def api_get_rsfmri_segmentation_tissue_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_tissue_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/tissue_qc.json")):
        subject_tissue_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "tissue_qc_summary": _read_json_if_exists(report_base / "tissue_qc_summary.json"),
        "tissue_qc_report": _read_text_if_exists(report_base / "tissue_qc_report.md"),
        "subject_tissue_qc": subject_tissue_qc,
    }
```

---

## 10. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriSegmentationTissueQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/segmentation-tissue-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriSegmentationTissueQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/segmentation-tissue-qc"
  );
}
```

---

## 11. 创建 frontend/src/components/RsfmriSegmentationTissueQcPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriSegmentationTissueQcPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriSegmentationTissueQc,
  runRsfmriSegmentationTissueQc
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriSegmentationTissueQcPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 SPM Segmentation + Tissue QC？这只处理 synthetic BIDS 数据，不会修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriSegmentationTissueQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_segmentation_tissue_qc.yaml",
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
      const response = await getRsfmriSegmentationTissueQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.tissue_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Segmentation + Tissue QC
        </button>
        <button onClick={handleLoad}>加载 Tissue QC 结果</button>
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
          <span>Mean GM Volume</span>
          <strong>
            {summary?.mean_gm_volume_mm3 == null
              ? "-"
              : Number(summary.mean_gm_volume_mm3).toFixed(2)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Tissue QC Summary</h3>
      <JsonBlock value={loaded?.tissue_qc_summary} emptyText="暂无 tissue QC summary" />

      <h3>Subject Tissue QC</h3>
      <JsonBlock value={loaded?.subject_tissue_qc} emptyText="暂无 subject tissue QC" />

      <h3>Tissue QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.tissue_qc_report === "string"
            ? loaded.tissue_qc_report
            : null
        }
        emptyText="暂无 tissue QC report"
      />
    </div>
  );
}
```

---

## 12. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriSegmentationTissueQcPanel } from "./components/RsfmriSegmentationTissueQcPanel";
```

在 `rs-fMRI SPM Coregistration + Registration QC` 后新增 Section：

```tsx
<Section
  title="rs-fMRI SPM Segmentation + Tissue QC"
  description="对 coregistered synthetic T1w 执行 SPM segmentation，并生成 GM/WM/CSF tissue QC。"
>
  <RsfmriSegmentationTissueQcPanel baseUrl={baseUrl} />
</Section>
```

---

## 13. 新增轻量测试

创建文件：

```text
tests/unit/test_tissue_qc.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.tissue_qc import compute_tissue_qc_for_subject


def test_tissue_qc_computes_volume_metrics(tmp_path: Path):
    derivatives = tmp_path / "derivatives"

    gm = tmp_path / "c1coreg_sub-001_T1w.nii"
    wm = tmp_path / "c2coreg_sub-001_T1w.nii"
    csf = tmp_path / "c3coreg_sub-001_T1w.nii"
    deformation = tmp_path / "y_coreg_sub-001_T1w.nii"

    affine = np.eye(4)

    gm_data = np.zeros((4, 4, 4), dtype=np.float32)
    wm_data = np.zeros((4, 4, 4), dtype=np.float32)
    csf_data = np.zeros((4, 4, 4), dtype=np.float32)

    gm_data[:2, :, :] = 0.8
    wm_data[2:3, :, :] = 0.7
    csf_data[3:4, :, :] = 0.6

    nib.save(nib.Nifti1Image(gm_data, affine), str(gm))
    nib.save(nib.Nifti1Image(wm_data, affine), str(wm))
    nib.save(nib.Nifti1Image(csf_data, affine), str(csf))
    nib.save(nib.Nifti1Image(np.zeros((4, 4, 4, 1, 3), dtype=np.float32), affine), str(deformation))

    result = compute_tissue_qc_for_subject(
        subject_id="sub-001",
        gm_file=str(gm),
        wm_file=str(wm),
        csf_file=str(csf),
        deformation_field=str(deformation),
        derivatives_dir=str(derivatives),
        probability_threshold=0.2,
    )

    assert result["ok"] is True
    assert result["segmentation_qc_status"] == "PASS"
    assert result["gm_volume_mm3"] > 0
    assert result["wm_volume_mm3"] > 0
    assert result["csf_volume_mm3"] > 0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "tissue_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
```

---

## 14. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/segmentation-tissue-qc")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 15. 更新 README.md

追加第三十九步说明：

```markdown
## Step 39: SPM Segmentation and Tissue QC

This step implements SPM segmentation of the coregistered synthetic T1w image.

It supports:

- approved SPM segmentation
- derivative coregistered T1w input only
- GM / WM / CSF tissue probability maps
- deformation field output
- tissue QC metrics
- subject-level tissue QC
- dataset-level tissue QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_segmentation_tissue_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_segmentation_tissue_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_segmentation_tissue_qc.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_preproc/sub-001/anat/c1coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/c2coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/c3coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/y_coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/spm_segmentation_result.json
derivatives/rsfmri_qc/sub-001/tissue_qc.json
derivatives/rsfmri_qc/sub-001/tissue_qc.md
reports/rsfmri/tissue_qc_summary.json
reports/rsfmri/tissue_qc_report.md
work/pipeline_runs/run_rsfmri_segmentation_tissue_qc_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/segmentation-tissue-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/segmentation-tissue-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_segmentation_tissue_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI SPM Segmentation + Tissue QC
```

### Safety

This step:

- requires approved=true
- only processes derivative coregistered T1w input
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
specs/spm_segmentation_tissue_qc_spec.md
matlab/spm_segment_wrapper.m
backend/app/tools/tissue_qc.py
backend/app/tools/spm_segment_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_segmentation_tissue_qc.yaml
backend/app/tools/run_rsfmri_segmentation_tissue_qc_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriSegmentationTissueQcPanel.tsx
frontend/src/App.tsx
tests/unit/test_tissue_qc.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_segmentation_tissue_qc_cli
```

应该安全失败，不应启动 SPM segmentation。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_segmentation_tissue_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_segmentation_tissue_qc.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_preproc/sub-001/anat/c1coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/c2coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/c3coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/y_coreg_sub-001_T1w.nii
derivatives/rsfmri_qc/sub-001/tissue_qc.json
reports/rsfmri/tissue_qc_summary.json
reports/rsfmri/tissue_qc_report.md
```

tissue QC JSON 必须包含：

```json
{
  "node_id": "tissue_qc_subject",
  "subject_id": "sub-001",
  "segmentation_qc_status": "PASS",
  "gm_volume_mm3": 0,
  "wm_volume_mm3": 0,
  "csf_volume_mm3": 0
}
```

实际数值根据 synthetic 数据和 SPM 输出决定。

运行测试：

```bash
python -m pytest tests/unit/test_tissue_qc.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/segmentation-tissue-qc

curl -X POST http://127.0.0.1:8000/api/rsfmri/segmentation-tissue-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/segmentation-tissue-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI SPM Segmentation + Tissue QC 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 tissue QC 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean GM volume。
8. 显示 tissue QC summary JSON。
9. 显示 subject tissue QC JSON。
10. 显示 tissue QC Markdown report。
11. 不修改 rawdata。
12. 不运行 DPABI。
13. 不调用 DPARSF_run / DPARSFA_run。
14. 不执行完整 preprocessing。

---

## 17. 重要限制

本步骤只做 SPM segmentation + tissue QC。

不要实现：

- normalization
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
3. SPM segmentation wrapper 如何工作
4. segmentation input 如何保证来自 derivatives
5. tissue QC 如何计算
6. 输出哪些 derivatives 和 reports
7. 为什么本步骤仍然不是完整 preprocessing
8. 下一步如何实现 Normalization + Normalization QC

'''
这一步给预处理流水线加上了 T1w 结构像的组织分割。

**核心改动是 SPM segmentation wrapper。** `spm_segment_wrapper.m` 拿 coregistration 产出的 `coreg_{subject}_T1w.nii` 做 SPM Unified Segmentation，调用 SPM12 的组织概率图（TPM.nii）把图像分割成灰质、白质、脑脊液三张概率图（`c1*` / `c2*` / `c3*`），同时产出一张 deformation field（`y_*`）。

**写了 tissue QC 模块。** `tissue_qc.py` 读三张组织图的实际体素数据，算每张图的 mean/max 概率、超过阈值（0.2）的体素数和体积估计。QC 判定：形状不一致或文件缺失 → FAIL，三个组织图体素全为零 → WARNING，否则 PASS。

**输入安全靠路径强校验。** segmentation runner 不接受任意 T1w 文件，只认精确路径 `derivatives/rsfmri_preproc/{subject}/anat/coreg_{subject}_T1w.nii`，不匹配就拒绝，不碰 rawdata。

**接入全栈。** node_registry 加两个新节点，pipeline 从 7 节点扩到 9 节点（4 个 SPM 阶段 + 4 个 QC 阶段 + 数据集报告），API 暴露了 run 和 get，前端面板显示 PASS/WARNING/FAIL 和平均灰质体积。

现在预处理链是：synthetic BOLD → slice timing → realignment → motion QC → coregistration → registration QC → segmentation → tissue QC。
'''
