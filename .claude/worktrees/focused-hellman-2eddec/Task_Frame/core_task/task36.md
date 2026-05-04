你是我的工程搭建助手。前三十五步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- SPM Realignment + Motion QC 核心 wrapper

现在开始第三十六步。

第三十六步目标：实现 “SPM Slice Timing Correction + Acquisition Metadata QC 闭环”。

这是 rs-fMRI preprocessing 的第二个核心执行步骤。

本步骤要实现：

1. SPM slice timing correction wrapper。
2. 对 synthetic BIDS-like BOLD 数据执行 slice timing correction。
3. 从 BIDS sidecar JSON 读取：
   - RepetitionTime
   - SliceTiming
   - NumberOfSlices 或通过 NIfTI shape 推断
4. 自动把 BIDS SliceTiming 转成 SPM slice order。
5. 支持用户参数 fallback：
   - tr
   - slice_order
   - reference_slice
6. 输出 slice-timing-corrected BOLD。
7. 生成 subject-level acquisition metadata QC。
8. 生成 dataset-level slice timing QC summary/report。
9. 将 `spm_slice_timing_subject` 和 `slice_timing_qc_dataset_report` 接入 pipeline runtime。
10. 后端 API 暴露 slice timing 结果。
11. 前端新增 rs-fMRI SPM Slice Timing + Metadata QC 面板。
12. 增加轻量 unit test。

本步骤允许调用 SPM，但必须满足：

- 只处理 synthetic BIDS-like 数据。
- 必须 approved=true 才执行 SPM slice timing。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- coregistration
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

本步骤只做：SPM slice timing correction + acquisition metadata QC。

---

## 1. 创建 specs/spm_slice_timing_spec.md

创建文件：

```text
specs/spm_slice_timing_spec.md

内容：

# SPM Slice Timing Correction Specification

This document defines the MVP SPM slice timing correction and acquisition metadata QC stage for rs-fMRI preprocessing.

## Goals

The goal is to execute SPM slice timing correction on synthetic rs-fMRI BOLD data and validate acquisition timing metadata.

This step prepares corrected functional time series for later realignment and downstream preprocessing.

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM slice timing correction
- BIDS sidecar metadata parsing
- RepetitionTime validation
- SliceTiming validation
- conversion from BIDS SliceTiming to SPM slice order
- fallback user parameters
- subject-level metadata QC JSON / Markdown
- dataset-level slice timing summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- realignment
- coregistration
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
- source code modification in SPM / DPABI
- file deletion

## Inputs

```text
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.nii or *.nii.gz
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.json
work/dataset_index/dataset_index.json
examples/project_config_dataset.yaml
Outputs
derivatives/rsfmri_preproc/{subject_id}/func/{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/a{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/spm_slice_timing_result.json
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.md
reports/rsfmri/slice_timing_qc_summary.json
reports/rsfmri/slice_timing_qc_report.md
QC Metrics
metadata_found
repetition_time
num_slices
slice_timing_count
slice_order
reference_slice
acquisition_duration
tr_consistency
slice_timing_status
Safety Rules
Execution requires approved=true.
Only synthetic BIDS-like input is allowed.
Do not modify rawdata.
Do not delete files.
Do not call DPABI.
Do not call DPARSF_run.
Do not call DPARSFA_run.
Do not call DPABI GUI.
Write outputs only under derivatives, work, reports, and logs.

---

## 2. 确保 synthetic BIDS sidecar JSON 包含 SliceTiming

找到当前生成 synthetic BIDS 的工具文件，可能类似：

```text
backend/app/tools/synthetic_bids.py
backend/app/tools/create_synthetic_bids.py
backend/app/tools/synthetic_dataset.py

不要新建重复工具。修改现有 synthetic BIDS 生成逻辑，使每个 BOLD sidecar JSON 至少包含：

{
  "TaskName": "rest",
  "RepetitionTime": 2.0,
  "SliceTiming": [0.0, 1.0, 0.1, 1.1, 0.2, 1.2],
  "PhaseEncodingDirection": "j",
  "Manufacturer": "Synthetic"
}

要求：

SliceTiming 长度必须等于 synthetic NIfTI 的 z 维切片数。
如果 synthetic 数据 shape 是 [x, y, z, t]，则 SliceTiming 长度为 z。
可以使用 interleaved timing 生成方式。
不改变 rawdata 以外的生成逻辑。
只影响项目自动生成的 synthetic BIDS 数据。

如果当前 synthetic BIDS 生成器已经有 sidecar JSON，只补充字段，不破坏已有字段。

3. 创建 matlab/spm_slice_timing_wrapper.m

创建文件：

matlab/spm_slice_timing_wrapper.m

功能要求：

接收参数：
spm_dir
input_nii
nslices
tr
ta
slice_order_json
reference_slice
output_json
input_nii 必须是已经复制到 derivatives 或 work workspace 的 NIfTI，不直接处理 rawdata。
添加 SPM 路径。
使用 SPM slice timing。
支持 4D NIfTI。
输出 JSON，记录：
ok
input_nii
output_dir
corrected_file
nslices
tr
ta
slice_order
reference_slice
frames_total
errors
warnings
不调用 DPABI。
不调用 DPARSF_run / DPARSFA_run。
不修改 rawdata。
不删除文件。

参考实现：

function spm_slice_timing_wrapper(spm_dir, input_nii, nslices, tr, ta, slice_order_json, reference_slice, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_slice_timing_wrapper';
    result.backend = 'matlab-spm';
    result.input_nii = input_nii;
    result.output_dir = fileparts(input_nii);
    result.corrected_file = '';
    result.nslices = str2double(nslices);
    result.tr = str2double(tr);
    result.ta = str2double(ta);
    result.reference_slice = str2double(reference_slice);
    result.slice_order = [];
    result.frames_total = 0;
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_nii, 'file')
            error(['Input NIfTI not found: ', input_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        slice_order = jsondecode(slice_order_json);
        slice_order = double(slice_order(:)');
        result.slice_order = slice_order;

        if numel(slice_order) ~= result.nslices
            error('slice_order length must equal nslices.');
        end

        vols = spm_vol(input_nii);
        n_frames = numel(vols);
        result.frames_total = n_frames;

        if n_frames < 2
            error('SPM slice timing requires at least 2 frames.');
        end

        scans = cell(n_frames, 1);
        for i = 1:n_frames
            scans{i} = [input_nii, ',', num2str(i)];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.temporal.st.scans = {scans};
        matlabbatch{1}.spm.temporal.st.nslices = result.nslices;
        matlabbatch{1}.spm.temporal.st.tr = result.tr;
        matlabbatch{1}.spm.temporal.st.ta = result.ta;
        matlabbatch{1}.spm.temporal.st.so = slice_order;
        matlabbatch{1}.spm.temporal.st.refslice = result.reference_slice;
        matlabbatch{1}.spm.temporal.st.prefix = 'a';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);

        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        corrected_file = fullfile(input_dir, ['a', input_name, '.nii']);

        if exist(corrected_file, 'file')
            result.corrected_file = corrected_file;
        else
            error(['Expected slice timing output not found: ', corrected_file]);
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
4. 创建 backend/app/tools/slice_timing_qc.py

创建文件：

backend/app/tools/slice_timing_qc.py

目标：读取 BIDS sidecar，校验 SliceTiming，并构建 SPM 参数。

提供函数：

find_bids_sidecar_for_bold(input_bold: str) -> str | None

build_slice_timing_parameters(
    input_bold: str,
    prepared_nii: str,
    tr: float | None = None,
    slice_order: list[int] | None = None,
    reference_slice: int | None = None,
) -> dict

write_slice_timing_qc_for_subject(
    subject_id: str,
    parameters: dict,
    derivatives_dir: str,
) -> dict

write_slice_timing_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict

实现要求：

BIDS sidecar 查找：
*_bold.nii.gz → *_bold.json
*_bold.nii → *_bold.json
build_slice_timing_parameters：
优先读取 JSON sidecar 的 RepetitionTime 和 SliceTiming
如果 SliceTiming 存在，转换成 SPM slice order：
按 acquisition time 从小到大排序
slice index 使用 1-based
如果 SliceTiming 不存在，但传入 slice_order，则使用传入值
如果 RepetitionTime 不存在，但传入 tr，则使用传入值
如果仍缺失关键参数，返回 ok=false
nslices 从 NIfTI shape[2] 推断
ta = tr - tr / nslices
reference_slice 默认取 slice_order 中间位置
写 subject-level QC JSON / Markdown。
写 dataset-level summary/report。

参考实现：

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


def find_bids_sidecar_for_bold(input_bold: str) -> str | None:
    path = Path(input_bold)

    name = path.name
    if name.endswith(".nii.gz"):
        sidecar = path.with_name(name[:-7] + ".json")
    elif name.endswith(".nii"):
        sidecar = path.with_suffix(".json")
    else:
        sidecar = path.with_suffix(".json")

    return str(sidecar) if sidecar.exists() else None


def _get_nifti_shape(path: str) -> list[int]:
    try:
        import nibabel as nib
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel. Install with: pip install nibabel") from exc

    img = nib.load(path)
    return list(img.shape)


def _slice_timing_to_order(slice_timing: list[float]) -> list[int]:
    indexed = list(enumerate(slice_timing, start=1))
    indexed = sorted(indexed, key=lambda item: (float(item[1]), item[0]))
    return [item[0] for item in indexed]


def _validate_positive_number(value: Any, name: str, errors: list[str]) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        errors.append(f"{name} must be numeric.")
        return None

    if parsed <= 0:
        errors.append(f"{name} must be positive.")
        return None

    return parsed


def build_slice_timing_parameters(
    input_bold: str,
    prepared_nii: str,
    tr: float | None = None,
    slice_order: list[int] | None = None,
    reference_slice: int | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    sidecar_path = find_bids_sidecar_for_bold(input_bold)
    metadata = _read_json(Path(sidecar_path)) if sidecar_path else None

    if not metadata:
        warnings.append("BIDS sidecar JSON not found or unreadable.")

    try:
        shape = _get_nifti_shape(prepared_nii)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [str(exc)],
            "warnings": warnings,
        }

    if len(shape) < 4:
        errors.append(f"BOLD NIfTI must be 4D. Shape was: {shape}")

    nslices = int(shape[2]) if len(shape) >= 3 else None

    metadata_tr = metadata.get("RepetitionTime") if metadata else None
    final_tr = _validate_positive_number(
        tr if tr is not None else metadata_tr,
        "RepetitionTime",
        errors,
    )

    metadata_slice_timing = metadata.get("SliceTiming") if metadata else None

    final_slice_order = None
    if metadata_slice_timing:
        if not isinstance(metadata_slice_timing, list):
            errors.append("SliceTiming must be a list.")
        elif nslices is not None and len(metadata_slice_timing) != nslices:
            errors.append(
                f"SliceTiming length {len(metadata_slice_timing)} does not match nslices {nslices}."
            )
        else:
            try:
                final_slice_order = _slice_timing_to_order([float(x) for x in metadata_slice_timing])
            except Exception as exc:
                errors.append(f"Invalid SliceTiming values: {exc}")
    elif slice_order:
        final_slice_order = [int(x) for x in slice_order]
        warnings.append("Using user-provided slice_order fallback.")
    else:
        errors.append("Missing SliceTiming metadata and no slice_order fallback provided.")

    if nslices is not None and final_slice_order and len(final_slice_order) != nslices:
        errors.append("slice_order length must equal nslices.")

    if final_slice_order:
        invalid = [x for x in final_slice_order if x < 1 or nslices is not None and x > nslices]
        if invalid:
            errors.append(f"slice_order contains invalid slice indices: {invalid}")

    if reference_slice is None and final_slice_order:
        reference_slice = final_slice_order[len(final_slice_order) // 2]

    if reference_slice is not None and nslices is not None:
        reference_slice = int(reference_slice)
        if reference_slice < 1 or reference_slice > nslices:
            errors.append("reference_slice must be between 1 and nslices.")

    ta = None
    if final_tr is not None and nslices:
        ta = final_tr - final_tr / nslices

    acquisition_duration = None
    if metadata_slice_timing:
        try:
            acquisition_duration = max(float(x) for x in metadata_slice_timing)
        except Exception:
            acquisition_duration = None

    return {
        "ok": len(errors) == 0,
        "input_bold": input_bold,
        "prepared_nii": prepared_nii,
        "sidecar_path": sidecar_path,
        "metadata_found": metadata is not None,
        "shape": shape,
        "nslices": nslices,
        "frames_total": shape[3] if len(shape) >= 4 else None,
        "tr": final_tr,
        "ta": ta,
        "slice_timing_count": len(metadata_slice_timing) if isinstance(metadata_slice_timing, list) else None,
        "slice_order": final_slice_order,
        "reference_slice": reference_slice,
        "acquisition_duration": acquisition_duration,
        "slice_timing_status": "PASS" if len(errors) == 0 else "FAIL",
        "warnings": warnings,
        "errors": errors,
    }


def write_slice_timing_qc_for_subject(
    subject_id: str,
    parameters: dict[str, Any],
    derivatives_dir: str,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "slice_timing_qc.json"
    qc_md = out_dir / "slice_timing_qc.md"

    result = {
        "ok": bool(parameters.get("ok")),
        "node_id": "slice_timing_qc_subject",
        "backend": "python",
        "subject_id": subject_id,
        "metadata_found": parameters.get("metadata_found"),
        "sidecar_path": parameters.get("sidecar_path"),
        "shape": parameters.get("shape"),
        "nslices": parameters.get("nslices"),
        "frames_total": parameters.get("frames_total"),
        "tr": parameters.get("tr"),
        "ta": parameters.get("ta"),
        "slice_timing_count": parameters.get("slice_timing_count"),
        "slice_order": parameters.get("slice_order"),
        "reference_slice": parameters.get("reference_slice"),
        "acquisition_duration": parameters.get("acquisition_duration"),
        "slice_timing_status": parameters.get("slice_timing_status"),
        "outputs": [str(qc_json), str(qc_md)],
        "warnings": parameters.get("warnings", []),
        "errors": parameters.get("errors", []),
    }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Slice Timing QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('slice_timing_status')}")
    lines.append(f"- Metadata found: {result.get('metadata_found')}")
    lines.append(f"- TR: {result.get('tr')}")
    lines.append(f"- Number of slices: {result.get('nslices')}")
    lines.append(f"- Frames total: {result.get('frames_total')}")
    lines.append(f"- Reference slice: {result.get('reference_slice')}")
    lines.append(f"- SliceTiming count: {result.get('slice_timing_count')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Slice timing QC reads metadata and derivative files only. It does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result


def write_slice_timing_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/slice_timing_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid slice timing QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("slice_timing_status") == "PASS")
    fail_count = sum(1 for item in subjects if item.get("slice_timing_status") == "FAIL")
    trs = [float(item["tr"]) for item in subjects if item.get("tr") is not None]

    summary = {
        "ok": fail_count == 0 and subjects_total > 0,
        "node_id": "slice_timing_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_fail": fail_count,
        "mean_tr": float(mean(trs)) if trs else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "slice_timing_qc_summary.json"
    report_path = report_out / "slice_timing_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Slice Timing QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean TR: {summary['mean_tr']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | TR | Slices | Frames | Reference Slice |")
    lines.append("|---|---|---:|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('slice_timing_status')} | "
            f"{item.get('tr')} | {item.get('nslices')} | "
            f"{item.get('frames_total')} | {item.get('reference_slice')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes slice timing metadata and derivative outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "slice_timing_qc_dataset_report",
        "backend": "python",
        "outputs": [str(summary_path), str(report_path)],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_pass": pass_count,
            "subjects_fail": fail_count,
        },
        "warnings": warnings,
        "errors": errors,
    }
5. 创建 backend/app/tools/spm_slice_timing_runner.py

创建文件：

backend/app/tools/spm_slice_timing_runner.py

目标：Python 调用 MATLAB SPM slice timing wrapper。

提供函数：

run_spm_slice_timing_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    tr: float | None = None,
    slice_order: list[int] | None = None,
    reference_slice: int | None = None,
    matlab_script_dir: str = "./matlab",
) -> dict

实现要求：

approved=false 时安全失败，不启动 MATLAB。
只允许 synthetic BIDS-like 输入：
路径必须包含 examples/synthetic_bids/rawdata
将 input BOLD 复制或转换为：
derivatives/rsfmri_preproc/{subject_id}/func/{subject_id}_bold.nii
如果输入是 .nii.gz，使用 nibabel 转成 .nii。
不修改原始 input。
调用 build_slice_timing_parameters。
如果参数 QC 失败，不启动 MATLAB，直接返回错误并写 QC。
调用 spm_slice_timing_wrapper.m。
输出：
a{subject_id}_bold.nii
spm_slice_timing_result.json
slice_timing_qc.json
stdout / stderr logs
不使用 shell=True。
不调用 DPABI。
不调用 DPARSF_run / DPARSFA_run。

参考实现：

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from backend.app.tools.slice_timing_qc import (
    build_slice_timing_parameters,
    write_slice_timing_qc_for_subject,
)


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _prepare_bold_input(input_bold: str, subject_id: str, derivatives_dir: str) -> str:
    input_path = Path(input_bold)
    out_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / f"{subject_id}_bold.nii"

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

    raise RuntimeError(f"Unsupported BOLD input extension: {input_path}")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_spm_slice_timing_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    tr: float | None = None,
    slice_order: list[int] | None = None,
    reference_slice: int | None = None,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM slice timing requires approved=true."],
        }

    normalized_input = str(input_bold).replace("\\", "/")
    if "examples/synthetic_bids/rawdata" not in normalized_input:
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                "Refusing to run SPM slice timing on non-synthetic input.",
                f"Input was: {input_bold}",
            ],
        }

    out_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_slice_timing_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_slice_timing_stderr.log"
    result_json = out_dir / "spm_slice_timing_result.json"

    try:
        prepared_input = _prepare_bold_input(
            input_bold=input_bold,
            subject_id=subject_id,
            derivatives_dir=derivatives_dir,
        )
    except Exception as exc:
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [str(exc)],
        }

    params = build_slice_timing_parameters(
        input_bold=input_bold,
        prepared_nii=prepared_input,
        tr=tr,
        slice_order=slice_order,
        reference_slice=reference_slice,
    )

    qc = write_slice_timing_qc_for_subject(
        subject_id=subject_id,
        parameters=params,
        derivatives_dir=derivatives_dir,
    )

    if not params.get("ok"):
        return {
            "ok": False,
            "node_id": "spm_slice_timing_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "prepared_input": prepared_input,
            "slice_timing_parameters": params,
            "outputs": qc.get("outputs", []),
            "warnings": params.get("warnings", []),
            "errors": params.get("errors", []),
        }

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_slice_timing_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(Path(prepared_input).resolve()))}', "
        f"'{int(params['nslices'])}', "
        f"'{float(params['tr'])}', "
        f"'{float(params['ta'])}', "
        f"'{_matlab_quote(json.dumps(params['slice_order']))}', "
        f"'{int(params['reference_slice'])}', "
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
        "errors": ["SPM slice timing did not produce result JSON."],
    }

    data["node_id"] = "spm_slice_timing_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["prepared_input"] = prepared_input
    data["slice_timing_parameters"] = params
    data["slice_timing_qc"] = qc
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    outputs = []
    if data.get("corrected_file"):
        outputs.append(data["corrected_file"])
    outputs.extend(qc.get("outputs", []))
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
6. 修改 backend/app/runtime/node_registry.py

新增节点：

spm_slice_timing_subject
slice_timing_qc_dataset_report

新增导入：

from backend.app.tools.spm_slice_timing_runner import run_spm_slice_timing_subject
from backend.app.tools.slice_timing_qc import write_slice_timing_dataset_report

新增 runner：

def run_spm_slice_timing_subject_node(
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

    bold = _find_subject_bold(context.subject_record)
    if not bold:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "subject_id": context.subject_id,
            "outputs": [],
            "errors": ["No BOLD input found for subject."],
        }

    result = run_spm_slice_timing_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=context.subject_id,
        input_bold=bold,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        tr=node.params.get("tr"),
        slice_order=node.params.get("slice_order"),
        reference_slice=node.params.get("reference_slice"),
        matlab_script_dir="./matlab",
    )

    result["node_id"] = node.id
    return result


def run_slice_timing_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_slice_timing_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result

如果 _find_subject_bold 已经在 Step 35 加过，复用它，不要重复定义。
如果没有，则添加：

def _find_subject_bold(subject_record: dict[str, Any]) -> str | None:
    for session in subject_record.get("sessions", []):
        for func in session.get("func", []):
            if func.get("bold"):
                return func.get("bold")
    return None

更新 NODE_REGISTRY：

"spm_slice_timing_subject": run_spm_slice_timing_subject_node,
"slice_timing_qc_dataset_report": run_slice_timing_qc_dataset_report_node,
7. 创建 examples/pipeline_rsfmri_spm_slice_timing.yaml

创建文件：

examples/pipeline_rsfmri_spm_slice_timing.yaml

内容：

pipeline_id: rsfmri_spm_slice_timing_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run approved SPM slice timing correction on synthetic rs-fMRI data and validate acquisition metadata."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_spm_slice_timing_001"
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

  - id: slice_timing_qc_dataset_report
    name: Slice Timing QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - spm_slice_timing_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/slice_timing_qc_summary.json"
      - "./reports/rsfmri/slice_timing_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

注意：默认 approved: false，直接运行应该安全失败。真正执行必须通过 CLI/API 显式 approval。

8. 创建 backend/app/tools/run_rsfmri_spm_slice_timing_cli.py

创建文件：

backend/app/tools/run_rsfmri_spm_slice_timing_cli.py

内容：

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
        if node.get("id") == "spm_slice_timing_subject":
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_spm_slice_timing.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("work/rsfmri/approved_pipeline_spm_slice_timing.yaml"),
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
9. 修改 backend/app/api/models.py

新增 request model：

class RsfmriSpmSliceTimingRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_spm_slice_timing.yaml")
    approved: bool = Field(default=False)
10. 修改 backend/app/api/routes.py

新增 API：

POST /api/rsfmri/spm-slice-timing/run
GET  /api/rsfmri/spm-slice-timing

新增导入：

from backend.app.api.models import RsfmriSpmSliceTimingRequest
from backend.app.runtime.pipeline_executor import run_pipeline

新增辅助函数：

def _make_spm_slice_timing_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") == "spm_slice_timing_subject":
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target

新增路由：

@router.post("/api/rsfmri/spm-slice-timing/run")
def api_run_rsfmri_spm_slice_timing(
    request: RsfmriSpmSliceTimingRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM slice timing requires approved=true.",
        )

    try:
        approved_pipeline = _make_spm_slice_timing_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_spm_slice_timing.yaml"),
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


@router.get("/api/rsfmri/spm-slice-timing")
def api_get_rsfmri_spm_slice_timing() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/slice_timing_qc.json")):
        subject_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "slice_timing_qc_summary": _read_json_if_exists(report_base / "slice_timing_qc_summary.json"),
        "slice_timing_qc_report": _read_text_if_exists(report_base / "slice_timing_qc_report.md"),
        "subject_slice_timing_qc": subject_qc,
    }
11. 修改 frontend/src/api.ts

新增：

export async function runRsfmriSpmSliceTiming(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-slice-timing/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriSpmSliceTiming(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-slice-timing"
  );
}
12. 创建 frontend/src/components/RsfmriSliceTimingPanel.tsx

创建文件：

frontend/src/components/RsfmriSliceTimingPanel.tsx

内容：

import { useState } from "react";
import {
  getRsfmriSpmSliceTiming,
  runRsfmriSpmSliceTiming
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriSliceTimingPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 SPM slice timing correction？这只处理 synthetic BIDS 数据，不会修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriSpmSliceTiming(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_spm_slice_timing.yaml",
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
      const response = await getRsfmriSpmSliceTiming(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.slice_timing_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 SPM Slice Timing
        </button>
        <button onClick={handleLoad}>加载 Slice Timing 结果</button>
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
          <span>FAIL</span>
          <strong>{String(summary?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Mean TR</span>
          <strong>
            {summary?.mean_tr == null
              ? "-"
              : Number(summary.mean_tr).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Slice Timing QC Summary</h3>
      <JsonBlock value={loaded?.slice_timing_qc_summary} emptyText="暂无 slice timing QC summary" />

      <h3>Subject Slice Timing QC</h3>
      <JsonBlock value={loaded?.subject_slice_timing_qc} emptyText="暂无 subject slice timing QC" />

      <h3>Slice Timing QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.slice_timing_qc_report === "string"
            ? loaded.slice_timing_qc_report
            : null
        }
        emptyText="暂无 slice timing QC report"
      />
    </div>
  );
}
13. 修改 frontend/src/App.tsx

新增导入：

import { RsfmriSliceTimingPanel } from "./components/RsfmriSliceTimingPanel";

在 rs-fMRI Core Preprocessing Plan 后，或者在 rs-fMRI SPM Realignment + Motion QC 前，新增 Section：

<Section
  title="rs-fMRI SPM Slice Timing + Metadata QC"
  description="对 synthetic rs-fMRI BOLD 执行 SPM slice timing correction，并校验 TR、SliceTiming 和 slice order。"
>
  <RsfmriSliceTimingPanel baseUrl={baseUrl} />
</Section>
14. 新增轻量测试

创建文件：

tests/unit/test_slice_timing_qc.py

内容：

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.slice_timing_qc import (
    build_slice_timing_parameters,
    find_bids_sidecar_for_bold,
)


def test_find_bids_sidecar_for_bold(tmp_path: Path):
    bold = tmp_path / "sub-001_task-rest_bold.nii.gz"
    sidecar = tmp_path / "sub-001_task-rest_bold.json"

    bold.write_bytes(b"fake")
    sidecar.write_text("{}", encoding="utf-8")

    assert find_bids_sidecar_for_bold(str(bold)) == str(sidecar)


def test_build_slice_timing_parameters_from_bids_sidecar(tmp_path: Path):
    raw = tmp_path / "examples" / "synthetic_bids" / "rawdata" / "sub-001" / "func"
    raw.mkdir(parents=True)

    bold = raw / "sub-001_task-rest_bold.nii.gz"
    sidecar = raw / "sub-001_task-rest_bold.json"
    prepared = tmp_path / "derivatives" / "rsfmri_preproc" / "sub-001" / "func" / "sub-001_bold.nii"
    prepared.parent.mkdir(parents=True)

    data = np.zeros((4, 4, 4, 5), dtype=np.float32)
    img = nib.Nifti1Image(data, affine=np.eye(4))
    nib.save(img, str(prepared))
    nib.save(img, str(bold))

    sidecar.write_text(
        json.dumps({
            "TaskName": "rest",
            "RepetitionTime": 2.0,
            "SliceTiming": [0.0, 1.0, 0.5, 1.5],
        }),
        encoding="utf-8",
    )

    params = build_slice_timing_parameters(
        input_bold=str(bold),
        prepared_nii=str(prepared),
    )

    assert params["ok"] is True
    assert params["nslices"] == 4
    assert params["frames_total"] == 5
    assert params["tr"] == 2.0
    assert params["slice_order"] == [1, 3, 2, 4]
    assert params["reference_slice"] in {2, 3}
15. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/rsfmri/spm-slice-timing")

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

16. 更新 README.md

追加第三十六步说明：

## Step 36: SPM Slice Timing Correction and Metadata QC

This step implements SPM slice timing correction for synthetic rs-fMRI data.

It supports:

- approved SPM slice timing correction
- synthetic BIDS-like input only
- BIDS sidecar metadata parsing
- RepetitionTime validation
- SliceTiming validation
- conversion from BIDS SliceTiming to SPM slice order
- subject-level slice timing QC
- dataset-level slice timing QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_spm_slice_timing_cli

This should fail safely because approval is missing.

Run with approval
python -m backend.app.tools.run_rsfmri_spm_slice_timing_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_spm_slice_timing.yaml --approve

Expected outputs:

derivatives/rsfmri_preproc/sub-001/func/sub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/asub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/spm_slice_timing_result.json
derivatives/rsfmri_qc/sub-001/slice_timing_qc.json
derivatives/rsfmri_qc/sub-001/slice_timing_qc.md
reports/rsfmri/slice_timing_qc_summary.json
reports/rsfmri/slice_timing_qc_report.md
work/pipeline_runs/run_rsfmri_spm_slice_timing_001/summary.json
API
curl http://127.0.0.1:8000/api/rsfmri/spm-slice-timing

Run approved:

curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-slice-timing/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_spm_slice_timing.yaml",
    "approved": true
  }'
Frontend

Use:

rs-fMRI SPM Slice Timing + Metadata QC
Safety

This step:

requires approved=true
only processes synthetic BIDS-like input
does not modify rawdata
does not run DPABI
does not call DPARSF_run
does not call DPARSFA_run
does not call DPABI GUI
does not execute full preprocessing

---

## 17. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/spm_slice_timing_spec.md
matlab/spm_slice_timing_wrapper.m
backend/app/tools/slice_timing_qc.py
backend/app/tools/spm_slice_timing_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_spm_slice_timing.yaml
backend/app/tools/run_rsfmri_spm_slice_timing_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriSliceTimingPanel.tsx
frontend/src/App.tsx
tests/unit/test_slice_timing_qc.py
backend/app/tools/api_smoke_test.py
README.md

先运行不带 approval：

python -m backend.app.tools.run_rsfmri_spm_slice_timing_cli

应该安全失败，不应启动 SPM slice timing。

然后运行 approved：

python -m backend.app.tools.run_rsfmri_spm_slice_timing_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_spm_slice_timing.yaml --approve

如果本地 MATLAB + SPM 可用，应生成：

derivatives/rsfmri_preproc/sub-001/func/asub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/spm_slice_timing_result.json
derivatives/rsfmri_qc/sub-001/slice_timing_qc.json
reports/rsfmri/slice_timing_qc_summary.json
reports/rsfmri/slice_timing_qc_report.md

slice timing QC JSON 必须包含：

{
  "node_id": "slice_timing_qc_subject",
  "subject_id": "sub-001",
  "metadata_found": true,
  "tr": 2.0,
  "nslices": 4,
  "slice_order": [1, 3, 2, 4],
  "slice_timing_status": "PASS"
}

实际 nslices / slice_order 根据 synthetic 数据 shape 和 sidecar 决定。

运行测试：

python -m pytest tests/unit/test_slice_timing_qc.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/rsfmri/spm-slice-timing

curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-slice-timing/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'

未批准 POST 必须返回 403。

批准 POST 可运行：

curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-slice-timing/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 rs-fMRI SPM Slice Timing + Metadata QC 区域。
可以点击批准并运行。
点击运行前有 confirm 弹窗。
可以加载 slice timing QC 结果。
显示 subject 数量。
显示 PASS / FAIL 数量。
显示 mean TR。
显示 slice timing QC summary JSON。
显示 subject slice timing QC JSON。
显示 slice timing QC Markdown report。
不修改 rawdata。
不运行 DPABI。
不调用 DPARSF_run / DPARSFA_run。
不执行完整 preprocessing。
18. 重要限制

本步骤只做 SPM slice timing correction + metadata QC。

不要实现：

realignment 链式输入切换
coregistration
segmentation
normalization
smoothing
nuisance regression
temporal filtering
ALFF / fALFF / ReHo
真实医学影像处理
DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
rawdata 修改
文件删除

完成后请总结：

新增了哪些文件
修改了哪些文件
SPM slice timing wrapper 如何工作
BIDS SliceTiming 如何转换为 SPM slice order
输出哪些 derivatives
输出哪些 QC report
为什么本步骤仍然不是完整 preprocessing
下一步如何把 slice timing 输出接入 realignment，形成 Slice Timing → Realignment → Motion QC 链式核心 pipeline

'''
这一步做了三件事，把 rs-fMRI 预处理流水线里 slice timing correction 这个环节跑通了。
第一，修好了合成数据的 BIDS sidecar。 之前 synthetic_bids.py 生成的 SliceTiming 只有 2 个值，但 NIfTI 实际有 16 层切片，导致 SliceTiming 长度对不上。现在改成生成 16 个值的 interleaved 时序（偶数层 0/2/4... 在前，奇数层 1/3/5... 在后，间隔 125ms），同时加了 PhaseEncodingDirection 字段。
第二，写了一套 SliceTiming 参数解析和 QC 模块。 slice_timing_qc.py 能从 BIDS sidecar JSON 里读出 RepetitionTime 和 SliceTiming，校验 TR 是否为正数、SliceTiming 长度是否等于切片数，然后把 BIDS 格式的 SliceTiming（按切片编号排列、值是采集时刻）转成 SPM 需要的 slice order（按采集时间排序的切片序号列表）。比如 [0.0, 1.0, 0.5, 1.5] → [1, 3, 2, 4]。参数不过关就直接阻断，不启动 MATLAB。
第三，写了 SPM slice timing wrapper 并接入全栈。 spm_slice_timing_wrapper.m 调用 SPM 的 spm.temporal.st 做层间时间校正，输出前缀 a 的校正文件。Python 侧的 spm_slice_timing_runner.py 负责安全检查——approved=true、路径必须包含 synthetic_bids/rawdata。在 node_registry 注册了两个新节点，API 暴露了 GET 和 POST（未批准返回 403），前端新增了面板可以运行并查看 TR、slice order、PASS/FAIL 等 QC 指标。
简单说，这一步让 pipeline 现在可以从 BIDS sidecar 自动读懂扫描时序参数，调 SPM 做 slice timing correction，并对参数本身做质检——为下一步把 slice timing 的输出接到 realignment 形成完整链条做好了准备。
'''