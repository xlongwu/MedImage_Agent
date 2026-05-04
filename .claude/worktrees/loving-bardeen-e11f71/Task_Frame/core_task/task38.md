你是我的工程搭建助手。前三十七步已经完成：

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

现在开始第三十八步。

第三十八步目标：实现 “SPM Coregistration + Registration QC 闭环”。

当前系统已经形成第一条连续 rs-fMRI 核心预处理链：

synthetic raw BOLD
→ SPM slice timing correction
→ SPM realignment
→ motion QC

但还缺少功能像和结构像之间的配准步骤。  
本步骤要继续深入 rs-fMRI 核心预处理，实现：

realigned mean functional image
→ anatomical T1w image
→ SPM coregistration
→ registration QC
→ subject-level coregistration report
→ dataset-level registration report

本步骤要实现：

1. SPM coregistration wrapper。
2. 对 synthetic BIDS-like 数据执行 mean functional image 与 T1w 的 coregistration。
3. 使用 realignment 输出的 mean functional image 作为 reference。
4. 使用 subject T1w image 作为 source。
5. 输出 coregistered T1w 或更新后的 T1w affine。
6. 生成 coregistration result JSON。
7. 生成 registration QC：
   - reference image shape
   - source image shape
   - voxel size
   - affine difference summary
   - center-of-mass distance
   - output existence
   - registration_qc_status
8. 生成 subject-level registration QC JSON / Markdown。
9. 生成 dataset-level registration QC summary / Markdown report。
10. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC
11. 后端 API 暴露 coregistration + registration QC 结果。
12. 前端新增 rs-fMRI Coregistration + Registration QC 面板。
13. 增加轻量 unit test。
14. 更新 README。

本步骤允许调用 SPM，但必须满足：

- 只处理 synthetic BIDS-like 数据。
- 必须 approved=true 才执行 SPM coregistration。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- segmentation
- normalization
- smoothing
- nuisance regression
- temporal filtering
- ALFF / fALFF / ReHo
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：SPM coregistration + registration QC。

---

## 1. 创建 specs/spm_coregistration_qc_spec.md

创建文件：

```text
specs/spm_coregistration_qc_spec.md
```

内容：

```markdown
# SPM Coregistration and Registration QC Specification

This document defines the MVP SPM coregistration and registration QC stage for rs-fMRI preprocessing.

## Goals

The goal is to coregister anatomical T1w images to the mean functional image produced by SPM realignment, then compute lightweight registration QC metrics.

This step extends the rs-fMRI core chain from motion correction into anatomical-functional alignment.

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM coregistration
- mean functional image as reference
- T1w anatomical image as source
- derivative-only workspace input
- subject-level registration QC JSON / Markdown
- dataset-level registration QC summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- segmentation
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
examples/synthetic_bids/rawdata/{subject_id}/anat/*_T1w.nii or *.nii.gz
derivatives/rsfmri_preproc/{subject_id}/func/mean*.nii
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_preproc/{subject_id}/anat/{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/coreg_{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/spm_coregistration_result.json
derivatives/rsfmri_qc/{subject_id}/registration_qc.json
derivatives/rsfmri_qc/{subject_id}/registration_qc.md
reports/rsfmri/registration_qc_summary.json
reports/rsfmri/registration_qc_report.md
```

## Registration QC Metrics

- reference_exists
- source_exists
- coregistered_exists
- reference_shape
- source_shape
- reference_voxel_size
- source_voxel_size
- affine_translation_distance_mm
- center_of_mass_distance_mm
- registration_qc_status

## Safety Rules

- Execution requires approved=true.
- Only synthetic BIDS-like input is allowed.
- Realignment mean image must come from derivatives.
- Do not modify rawdata.
- Do not delete files.
- Do not call DPABI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
```

---

## 2. 确保 synthetic BIDS 生成 anat T1w

找到当前 synthetic BIDS 生成工具，可能类似：

```text
backend/app/tools/synthetic_bids.py
backend/app/tools/create_synthetic_bids.py
backend/app/tools/synthetic_dataset.py
```

不要新建重复工具。修改现有 synthetic BIDS 生成逻辑，确保每个 subject 至少包含：

```text
examples/synthetic_bids/rawdata/{subject_id}/anat/{subject_id}_T1w.nii.gz
examples/synthetic_bids/rawdata/{subject_id}/anat/{subject_id}_T1w.json
```

T1w sidecar JSON 至少包含：

```json
{
  "Modality": "MR",
  "ImageType": ["ORIGINAL", "PRIMARY", "T1"],
  "Manufacturer": "Synthetic"
}
```

要求：

- T1w 可以用简单 synthetic 3D volume。
- 不需要模拟真实解剖结构。
- 只用于工程闭环和 SPM wrapper 测试。
- 不破坏已有 synthetic BIDS 生成逻辑。
- 如果已经有 anat/T1w，只补充缺失字段。

---

## 3. 创建 matlab/spm_coregister_wrapper.m

创建文件：

```text
matlab/spm_coregister_wrapper.m
```

功能要求：

1. 接收参数：
   - spm_dir
   - reference_nii
   - source_nii
   - output_json

2. reference_nii 必须是 realignment 产生的 mean functional derivative。
3. source_nii 必须是复制到 derivatives workspace 的 T1w，不直接处理 rawdata。
4. 添加 SPM 路径。
5. 使用 SPM coregister estimate。
6. 复制一份 source 到 coreg_ 前缀文件，用这份 derivative 作为 source，避免修改 rawdata。
7. 输出 JSON，记录：
   - ok
   - reference_nii
   - source_nii
   - coregistered_file
   - output_dir
   - errors
   - warnings
8. 不调用 DPABI。
9. 不调用 DPARSF_run / DPARSFA_run。
10. 不修改 rawdata。
11. 不删除文件。

参考实现：

```matlab
function spm_coregister_wrapper(spm_dir, reference_nii, source_nii, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_coregister_wrapper';
    result.backend = 'matlab-spm';
    result.reference_nii = reference_nii;
    result.source_nii = source_nii;
    result.coregistered_file = '';
    result.output_dir = fileparts(source_nii);
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(reference_nii, 'file')
            error(['Reference NIfTI not found: ', reference_nii]);
        end

        if ~exist(source_nii, 'file')
            error(['Source NIfTI not found: ', source_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        [source_dir, source_name, source_ext] = fileparts(source_nii);
        if strcmp(source_ext, '.gz')
            [~, source_name, ~] = fileparts(source_name);
        end

        coregistered_file = fullfile(source_dir, ['coreg_', source_name, '.nii']);
        copyfile(source_nii, coregistered_file);

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.coreg.estimate.ref = {[reference_nii, ',1']};
        matlabbatch{1}.spm.spatial.coreg.estimate.source = {[coregistered_file, ',1']};
        matlabbatch{1}.spm.spatial.coreg.estimate.other = {''};
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.cost_fun = 'nmi';
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.sep = [4 2];
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.tol = ...
            [0.02 0.02 0.02 0.001 0.001 0.001 0.01 0.01 0.01 0.001 0.001 0.001];
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.fwhm = [7 7];

        spm_jobman('run', matlabbatch);

        if exist(coregistered_file, 'file')
            result.coregistered_file = coregistered_file;
        else
            error(['Expected coregistered file not found: ', coregistered_file]);
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

## 4. 创建 backend/app/tools/registration_qc.py

创建文件：

```text
backend/app/tools/registration_qc.py
```

目标：根据 reference mean functional、source T1w、coregistered T1w 计算 lightweight registration QC。

提供函数：

```python
compute_registration_qc_for_subject(
    subject_id: str,
    reference_nii: str,
    source_nii: str,
    coregistered_nii: str,
    derivatives_dir: str,
    center_distance_warning_mm: float = 30.0,
) -> dict

write_registration_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. 使用 nibabel 读取 header / affine，不读取完整 voxel data。
2. 计算：
   - shape
   - voxel size
   - affine translation distance
   - image center world coordinate
   - center-of-mass distance approximate
3. QC 状态：
   - output 不存在 → FAIL
   - center distance > threshold → WARNING
   - 其他 → PASS
4. 输出：
   - derivatives/rsfmri_qc/{subject_id}/registration_qc.json
   - derivatives/rsfmri_qc/{subject_id}/registration_qc.md
   - reports/rsfmri/registration_qc_summary.json
   - reports/rsfmri/registration_qc_report.md

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _load_meta(path: Path) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    img = nib.load(str(path))
    shape = list(img.shape)
    affine = img.affine
    zooms = list(img.header.get_zooms())

    voxel_center = np.array([(dim - 1) / 2.0 for dim in shape[:3]] + [1.0])
    world_center = affine @ voxel_center

    return {
        "path": str(path),
        "shape": shape,
        "voxel_size": zooms[:3],
        "affine": affine.tolist(),
        "world_center": [float(x) for x in world_center[:3]],
        "translation": [float(x) for x in affine[:3, 3]],
    }


def _euclidean(a: list[float], b: list[float]) -> float:
    return float(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5)


def compute_registration_qc_for_subject(
    subject_id: str,
    reference_nii: str,
    source_nii: str,
    coregistered_nii: str,
    derivatives_dir: str,
    center_distance_warning_mm: float = 30.0,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "registration_qc.json"
    qc_md = out_dir / "registration_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    reference_path = Path(reference_nii)
    source_path = Path(source_nii)
    coreg_path = Path(coregistered_nii)

    missing = [
        str(path)
        for path in [reference_path, source_path, coreg_path]
        if not path.exists()
    ]

    if missing:
        result = {
            "ok": False,
            "node_id": "registration_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "registration_qc_status": "FAIL",
            "missing_files": missing,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [f"Missing files: {missing}"],
        }
    else:
        try:
            reference_meta = _load_meta(reference_path)
            source_meta = _load_meta(source_path)
            coreg_meta = _load_meta(coreg_path)

            affine_translation_distance_mm = _euclidean(
                source_meta["translation"],
                coreg_meta["translation"],
            )

            center_of_mass_distance_mm = _euclidean(
                reference_meta["world_center"],
                coreg_meta["world_center"],
            )

            if center_of_mass_distance_mm > center_distance_warning_mm:
                registration_qc_status = "WARNING"
                warnings.append(
                    f"Center distance {center_of_mass_distance_mm:.3f} exceeds warning threshold {center_distance_warning_mm}."
                )
            else:
                registration_qc_status = "PASS"

            result = {
                "ok": True,
                "node_id": "registration_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "reference_nii": str(reference_path),
                "source_nii": str(source_path),
                "coregistered_nii": str(coreg_path),
                "reference_shape": reference_meta["shape"],
                "source_shape": source_meta["shape"],
                "coregistered_shape": coreg_meta["shape"],
                "reference_voxel_size": reference_meta["voxel_size"],
                "source_voxel_size": source_meta["voxel_size"],
                "coregistered_voxel_size": coreg_meta["voxel_size"],
                "affine_translation_distance_mm": affine_translation_distance_mm,
                "center_of_mass_distance_mm": center_of_mass_distance_mm,
                "center_distance_warning_mm": center_distance_warning_mm,
                "registration_qc_status": registration_qc_status,
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": errors,
            }

        except Exception as exc:
            result = {
                "ok": False,
                "node_id": "registration_qc_subject",
                "backend": "python",
                "subject_id": subject_id,
                "registration_qc_status": "FAIL",
                "outputs": [str(qc_json), str(qc_md)],
                "warnings": warnings,
                "errors": [str(exc)],
            }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Registration QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('registration_qc_status')}")
    lines.append(f"- Reference: `{result.get('reference_nii')}`")
    lines.append(f"- Source: `{result.get('source_nii')}`")
    lines.append(f"- Coregistered: `{result.get('coregistered_nii')}`")
    lines.append(f"- Affine translation distance mm: {result.get('affine_translation_distance_mm')}")
    lines.append(f"- Center distance mm: {result.get('center_of_mass_distance_mm')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Registration QC reads derivative headers only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_registration_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/registration_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid registration QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("registration_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("registration_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("registration_qc_status") == "FAIL")

    center_distances = [
        float(item["center_of_mass_distance_mm"])
        for item in subjects
        if item.get("center_of_mass_distance_mm") is not None
    ]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "registration_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_center_distance_mm": float(mean(center_distances)) if center_distances else None,
        "max_center_distance_mm": float(max(center_distances)) if center_distances else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "registration_qc_summary.json"
    report_path = report_out / "registration_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Registration QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean center distance mm: {summary['mean_center_distance_mm']}")
    lines.append(f"- Max center distance mm: {summary['max_center_distance_mm']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Center Distance mm | Affine Translation Distance mm |")
    lines.append("|---|---|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('registration_qc_status')} | "
            f"{item.get('center_of_mass_distance_mm')} | "
            f"{item.get('affine_translation_distance_mm')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative registration QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "registration_qc_dataset_report",
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

## 5. 创建 backend/app/tools/spm_coregister_runner.py

创建文件：

```text
backend/app/tools/spm_coregister_runner.py
```

目标：Python 调用 MATLAB SPM coregistration wrapper。

提供函数：

```python
run_spm_coregister_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    subject_record: dict,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict
```

实现要求：

1. approved=false 时安全失败，不启动 MATLAB。
2. 只允许 synthetic BIDS-like T1w 输入：
   - 路径必须包含 `examples/synthetic_bids/rawdata`
3. reference image 必须来自：
   - `derivatives/rsfmri_preproc/{subject_id}/func/mean*.nii`
4. 将 T1w 复制或转换为：

```text
derivatives/rsfmri_preproc/{subject_id}/anat/{subject_id}_T1w.nii
```

5. 如果 T1w 是 `.nii.gz`，使用 nibabel 转成 `.nii`。
6. 不修改原始 input。
7. 调用 `spm_coregister_wrapper.m`。
8. 调用 `compute_registration_qc_for_subject`。
9. 输出：
   - `coreg_{subject_id}_T1w.nii`
   - `spm_coregistration_result.json`
   - `registration_qc.json`
   - stdout / stderr logs
10. 不使用 shell=True。
11. 不调用 DPABI。
12. 不调用 DPARSF_run / DPARSFA_run。

参考实现：

```python
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from backend.app.tools.registration_qc import compute_registration_qc_for_subject


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _find_subject_t1w(subject_record: dict[str, Any]) -> str | None:
    for session in subject_record.get("sessions", []):
        anat = session.get("anat", {})
        if isinstance(anat, dict) and anat.get("t1w"):
            return anat.get("t1w")

        if isinstance(anat, list):
            for item in anat:
                if item.get("t1w"):
                    return item.get("t1w")

    if subject_record.get("anat"):
        anat = subject_record.get("anat")
        if isinstance(anat, dict) and anat.get("t1w"):
            return anat.get("t1w")

    return None


def _find_mean_functional(subject_id: str, derivatives_dir: str) -> str | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    candidates = sorted(func_dir.glob("mean*.nii"))
    return str(candidates[0]) if candidates else None


def _is_safe_synthetic_t1w(path: str) -> bool:
    normalized = str(path).replace("\\", "/")
    return "examples/synthetic_bids/rawdata" in normalized and (
        normalized.endswith(".nii") or normalized.endswith(".nii.gz")
    )


def _prepare_t1w_input(input_t1w: str, subject_id: str, derivatives_dir: str) -> str:
    input_path = Path(input_t1w)
    out_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "anat"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / f"{subject_id}_T1w.nii"

    if input_path.name.endswith(".nii"):
        shutil.copyfile(input_path, output_path)
        return str(output_path)

    if input_path.name.endswith(".nii.gz"):
        try:
            import nibabel as nib
        except ImportError as exc:
            raise RuntimeError("Missing dependency: nibabel. Install with: pip install nibabel") from exc

        img = nib.load(str(input_path))
        nib.save(img, str(output_path))
        return str(output_path)

    raise RuntimeError(f"Unsupported T1w input extension: {input_path}")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_spm_coregister_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    subject_record: dict[str, Any],
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_coregister_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM coregistration requires approved=true."],
        }

    input_t1w = _find_subject_t1w(subject_record)
    if not input_t1w:
        return {
            "ok": False,
            "node_id": "spm_coregister_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["No T1w input found for subject."],
        }

    if not _is_safe_synthetic_t1w(input_t1w):
        return {
            "ok": False,
            "node_id": "spm_coregister_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                "Refusing to run SPM coregistration on non-synthetic T1w input.",
                f"Input was: {input_t1w}",
            ],
        }

    reference_nii = _find_mean_functional(subject_id, derivatives_dir)
    if not reference_nii:
        return {
            "ok": False,
            "node_id": "spm_coregister_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                "Mean functional reference image not found.",
                f"Expected under derivatives/rsfmri_preproc/{subject_id}/func/mean*.nii",
            ],
        }

    anat_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "anat"
    anat_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_coregister_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_coregister_stderr.log"
    result_json = anat_dir / "spm_coregistration_result.json"

    try:
        prepared_t1w = _prepare_t1w_input(
            input_t1w=input_t1w,
            subject_id=subject_id,
            derivatives_dir=derivatives_dir,
        )
    except Exception as exc:
        return {
            "ok": False,
            "node_id": "spm_coregister_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [str(exc)],
        }

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_coregister_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(Path(reference_nii).resolve()))}', "
        f"'{_matlab_quote(str(Path(prepared_t1w).resolve()))}', "
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
        "errors": ["SPM coregistration did not produce result JSON."],
    }

    data["node_id"] = "spm_coregister_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["reference_nii"] = reference_nii
    data["prepared_t1w"] = prepared_t1w
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    coregistered = data.get("coregistered_file")

    qc_outputs = []
    if coregistered:
        qc = compute_registration_qc_for_subject(
            subject_id=subject_id,
            reference_nii=reference_nii,
            source_nii=prepared_t1w,
            coregistered_nii=coregistered,
            derivatives_dir=derivatives_dir,
        )
        data["registration_qc"] = qc
        qc_outputs = qc.get("outputs", [])

    outputs = []
    if coregistered:
        outputs.append(coregistered)
    outputs.extend(qc_outputs)
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
```

---

## 6. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
spm_coregister_subject
registration_qc_dataset_report
```

新增导入：

```python
from backend.app.tools.spm_coregister_runner import run_spm_coregister_subject
from backend.app.tools.registration_qc import write_registration_qc_dataset_report
```

新增 runner：

```python
def run_spm_coregister_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    if not context.subject_id or not context.subject_record:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id or subject_record in context."],
        }

    result = run_spm_coregister_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=context.subject_id,
        subject_record=context.subject_record,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        matlab_script_dir="./matlab",
    )

    result["node_id"] = node.id
    return result


def run_registration_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_registration_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"spm_coregister_subject": run_spm_coregister_subject_node,
"registration_qc_dataset_report": run_registration_qc_dataset_report_node,
```

---

## 7. 创建 examples/pipeline_rsfmri_coregistration_qc.yaml

创建文件：

```text
examples/pipeline_rsfmri_coregistration_qc.yaml
```

内容：

```yaml
pipeline_id: rsfmri_coregistration_qc_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run approved SPM coregistration using mean functional image and synthetic T1w, then compute registration QC."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_coregistration_qc_001"
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
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。

---

## 8. 创建 backend/app/tools/run_rsfmri_coregistration_qc_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_coregistration_qc_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_coregistration_qc.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("work/rsfmri/approved_pipeline_coregistration_qc.yaml"),
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
class RsfmriCoregistrationQcRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_coregistration_qc.yaml")
    approved: bool = Field(default=False)
```

---

## 10. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/coregistration-qc/run
GET  /api/rsfmri/coregistration-qc
```

新增导入：

```python
from backend.app.api.models import RsfmriCoregistrationQcRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_coregistration_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
        }:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target
```

新增路由：

```python
@router.post("/api/rsfmri/coregistration-qc/run")
def api_run_rsfmri_coregistration_qc(
    request: RsfmriCoregistrationQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM coregistration QC pipeline requires approved=true.",
        )

    try:
        approved_pipeline = _make_coregistration_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_coregistration_qc.yaml"),
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


@router.get("/api/rsfmri/coregistration-qc")
def api_get_rsfmri_coregistration_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_registration_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/registration_qc.json")):
        subject_registration_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "registration_qc_summary": _read_json_if_exists(report_base / "registration_qc_summary.json"),
        "registration_qc_report": _read_text_if_exists(report_base / "registration_qc_report.md"),
        "subject_registration_qc": subject_registration_qc,
    }
```

---

## 11. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriCoregistrationQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/coregistration-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriCoregistrationQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/coregistration-qc"
  );
}
```

---

## 12. 创建 frontend/src/components/RsfmriCoregistrationQcPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriCoregistrationQcPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriCoregistrationQc,
  runRsfmriCoregistrationQc
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriCoregistrationQcPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 SPM Coregistration + Registration QC？这只处理 synthetic BIDS 数据，不会修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriCoregistrationQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_coregistration_qc.yaml",
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
      const response = await getRsfmriCoregistrationQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.registration_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Coregistration + Registration QC
        </button>
        <button onClick={handleLoad}>加载 Registration QC 结果</button>
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
          <span>Mean Center Distance</span>
          <strong>
            {summary?.mean_center_distance_mm == null
              ? "-"
              : Number(summary.mean_center_distance_mm).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Registration QC Summary</h3>
      <JsonBlock value={loaded?.registration_qc_summary} emptyText="暂无 registration QC summary" />

      <h3>Subject Registration QC</h3>
      <JsonBlock value={loaded?.subject_registration_qc} emptyText="暂无 subject registration QC" />

      <h3>Registration QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.registration_qc_report === "string"
            ? loaded.registration_qc_report
            : null
        }
        emptyText="暂无 registration QC report"
      />
    </div>
  );
}
```

---

## 13. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriCoregistrationQcPanel } from "./components/RsfmriCoregistrationQcPanel";
```

在 `rs-fMRI Slice Timing → Realignment → Motion QC` 后新增 Section：

```tsx
<Section
  title="rs-fMRI SPM Coregistration + Registration QC"
  description="使用 mean functional image 和 synthetic T1w 执行 SPM coregistration，并生成 registration QC。"
>
  <RsfmriCoregistrationQcPanel baseUrl={baseUrl} />
</Section>
```

---

## 14. 新增轻量测试

创建文件：

```text
tests/unit/test_registration_qc.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.registration_qc import compute_registration_qc_for_subject


def test_registration_qc_computes_header_metrics(tmp_path: Path):
    derivatives = tmp_path / "derivatives"

    ref = tmp_path / "mean_func.nii"
    src = tmp_path / "sub-001_T1w.nii"
    coreg = tmp_path / "coreg_sub-001_T1w.nii"

    data_ref = np.zeros((4, 4, 4), dtype=np.float32)
    data_src = np.zeros((8, 8, 8), dtype=np.float32)

    ref_affine = np.eye(4)
    src_affine = np.eye(4)
    coreg_affine = np.eye(4)
    coreg_affine[:3, 3] = [1, 2, 3]

    nib.save(nib.Nifti1Image(data_ref, ref_affine), str(ref))
    nib.save(nib.Nifti1Image(data_src, src_affine), str(src))
    nib.save(nib.Nifti1Image(data_src, coreg_affine), str(coreg))

    result = compute_registration_qc_for_subject(
        subject_id="sub-001",
        reference_nii=str(ref),
        source_nii=str(src),
        coregistered_nii=str(coreg),
        derivatives_dir=str(derivatives),
        center_distance_warning_mm=100.0,
    )

    assert result["ok"] is True
    assert result["registration_qc_status"] == "PASS"
    assert result["affine_translation_distance_mm"] > 0

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "registration_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
```

---

## 15. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/coregistration-qc")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 16. 更新 README.md

追加第三十八步说明：

```markdown
## Step 38: SPM Coregistration and Registration QC

This step implements SPM coregistration between the mean functional image and synthetic T1w anatomical image.

It supports:

- approved SPM coregistration
- synthetic BIDS-like input only
- mean functional derivative as reference
- T1w derivative workspace copy as source
- registration QC metrics
- subject-level registration QC
- dataset-level registration QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_coregistration_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_coregistration_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_coregistration_qc.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_preproc/sub-001/anat/sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/spm_coregistration_result.json
derivatives/rsfmri_qc/sub-001/registration_qc.json
derivatives/rsfmri_qc/sub-001/registration_qc.md
reports/rsfmri/registration_qc_summary.json
reports/rsfmri/registration_qc_report.md
work/pipeline_runs/run_rsfmri_coregistration_qc_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/coregistration-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/coregistration-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_coregistration_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI SPM Coregistration + Registration QC
```

### Safety

This step:

- requires approved=true
- only processes synthetic BIDS-like input
- uses derivative mean functional reference
- copies T1w into derivatives before coregistration
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing
```

---

## 17. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/spm_coregistration_qc_spec.md
matlab/spm_coregister_wrapper.m
backend/app/tools/registration_qc.py
backend/app/tools/spm_coregister_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_coregistration_qc.yaml
backend/app/tools/run_rsfmri_coregistration_qc_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriCoregistrationQcPanel.tsx
frontend/src/App.tsx
tests/unit/test_registration_qc.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_coregistration_qc_cli
```

应该安全失败，不应启动 SPM coregistration。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_coregistration_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_coregistration_qc.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_preproc/sub-001/anat/coreg_sub-001_T1w.nii
derivatives/rsfmri_preproc/sub-001/anat/spm_coregistration_result.json
derivatives/rsfmri_qc/sub-001/registration_qc.json
reports/rsfmri/registration_qc_summary.json
reports/rsfmri/registration_qc_report.md
```

registration QC JSON 必须包含：

```json
{
  "node_id": "registration_qc_subject",
  "subject_id": "sub-001",
  "registration_qc_status": "PASS",
  "reference_shape": [],
  "source_shape": [],
  "coregistered_shape": [],
  "center_of_mass_distance_mm": 0
}
```

实际数值根据 synthetic 数据和 SPM 输出决定。

运行测试：

```bash
python -m pytest tests/unit/test_registration_qc.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/coregistration-qc

curl -X POST http://127.0.0.1:8000/api/rsfmri/coregistration-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/coregistration-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI SPM Coregistration + Registration QC 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 registration QC 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean center distance。
8. 显示 registration QC summary JSON。
9. 显示 subject registration QC JSON。
10. 显示 registration QC Markdown report。
11. 不修改 rawdata。
12. 不运行 DPABI。
13. 不调用 DPARSF_run / DPARSFA_run。
14. 不执行完整 preprocessing。

---

## 18. 重要限制

本步骤只做 SPM coregistration + registration QC。

不要实现：

- segmentation
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
3. SPM coregistration wrapper 如何工作
4. reference 和 source 如何选择
5. registration QC 如何计算
6. 输出哪些 derivatives 和 reports
7. 为什么本步骤仍然不是完整 preprocessing
8. 下一步如何实现 Segmentation + Tissue QC

'''
这一步给预处理流水线加上了功能像和结构像之间的配准环节。
写了 SPM coregistration wrapper。 spm_coregister_wrapper.m 把 realignment 产出的 mean functional image 作为参考图像、T1w 结构像拷贝到 derivatives 后作为源图像，调用 SPM 的 coreg.estimate（用 NMI 做代价函数）估算刚体变换，把结果写到 T1w 的 header 里。整个过程不碰 rawdata。
写了 registration QC 模块。 registration_qc.py 只读 NIfTI header 不读体素数据，计算两个指标：源图像与配准后图像之间的 affine 平移距离，以及参考图像与配准后图像之间的质心距离。质心距离超过 30mm 标 WARNING，文件缺失标 FAIL。
补了 synthetic T1w 的 sidecar JSON。 之前 synthetic_bids.py 生成 T1w 但没有 JSON 侧车，现在补上了 *_T1w.json。
接入了全栈。 node_registry 新增两个节点，pipeline 从 slice timing → realignment → motion QC → coregistration → registration QC 形成 7 节点链路，API 暴露了 run 和 get 端点，前端新增面板显示配准 QC 指标（PASS/WARNING/FAIL、平均质心距离）。
现在预处理链是：synthetic BOLD → slice timing → realignment → motion QC → coregistration → registration QC，从时序校正到头动校正再到结构-功能配准都串起来了。
'''