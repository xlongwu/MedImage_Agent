你是我的工程搭建助手。前三十四步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- SPM smoothing 最小闭环
- DPABI wrapper 探测与 sandbox
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- rs-fMRI core preprocessing plan

现在开始第三十五步。

第三十五步目标：实现 “SPM Realignment + Motion QC 核心 wrapper 闭环”。

这是 rs-fMRI preprocessing 的第一个真正核心执行步骤。

本步骤要实现：

1. SPM realignment wrapper。
2. 对 synthetic BIDS-like BOLD 数据执行 realign。
3. 输出 realigned BOLD、mean functional image、motion parameter file。
4. 计算 motion QC：
   - framewise displacement
   - mean FD
   - max FD
   - high-motion frame count
   - high-motion fraction
   - motion parameter summary
5. 生成 subject-level motion QC JSON / Markdown。
6. 生成 dataset-level motion QC summary / Markdown report。
7. 将 `spm_realign_subject` 和 `motion_qc_subject` 接入 pipeline runtime。
8. 后端 API 暴露 realignment + motion QC 结果。
9. 前端新增 rs-fMRI SPM Realignment + Motion QC 面板。
10. 增加轻量 unit test。

本步骤允许调用 SPM，但必须满足：

- 只处理 synthetic BIDS-like 数据。
- 必须 approved=true 才执行 SPM realignment。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- slice timing
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

本步骤只做：SPM realignment + motion QC。

---

## 1. 创建 specs/spm_realign_motion_qc_spec.md

创建文件：

```text
specs/spm_realign_motion_qc_spec.md

内容：

# SPM Realignment and Motion QC Specification

This document defines the MVP SPM realignment and motion QC stage for rs-fMRI preprocessing.

## Goals

The goal is to execute a real SPM realignment wrapper on synthetic rs-fMRI BOLD data and compute motion QC metrics.

This is the first core preprocessing execution step after the rs-fMRI protocol and step registry.

## Scope

Supported in this step:

- synthetic BIDS-like input only
- approved SPM realignment
- 4D NIfTI input preparation
- SPM realign estimate and reslice
- motion parameter extraction
- framewise displacement calculation
- subject-level motion QC JSON / Markdown
- dataset-level motion QC summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- slice timing correction
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
work/dataset_index/dataset_index.json
examples/project_config_dataset.yaml
Outputs
derivatives/rsfmri_preproc/{subject_id}/func/r{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/mean{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/rp_{subject_id}_bold.txt
derivatives/rsfmri_qc/{subject_id}/motion_qc.json
derivatives/rsfmri_qc/{subject_id}/motion_qc.md
reports/rsfmri/motion_qc_summary.json
reports/rsfmri/motion_qc_report.md
Motion QC Metrics
frames_total
mean_fd
max_fd
median_fd
high_motion_frame_count
high_motion_fraction
fd_threshold
translation_max_abs_mm
rotation_max_abs_rad
motion_qc_status
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

## 2. 创建 matlab/spm_realign_wrapper.m

创建文件：

```text
matlab/spm_realign_wrapper.m

功能要求：

接收参数：
spm_dir
input_nii
output_json
要求 input_nii 是已经复制到 derivatives 或 work workspace 的 NIfTI，不直接处理 rawdata。
添加 SPM 路径。
使用 SPM realign estimate and reslice。
支持 4D NIfTI。
输出 JSON，记录：
ok
input_nii
output_dir
realigned_files
mean_file
motion_parameter_file
frames_total
errors
warnings
不调用 DPABI。
不调用 DPARSF_run / DPARSFA_run。
不修改 rawdata。
不删除文件。

参考实现：

function spm_realign_wrapper(spm_dir, input_nii, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_realign_wrapper';
    result.backend = 'matlab-spm';
    result.input_nii = input_nii;
    result.output_dir = fileparts(input_nii);
    result.realigned_files = {};
    result.mean_file = '';
    result.motion_parameter_file = '';
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

        vols = spm_vol(input_nii);
        n_frames = numel(vols);
        result.frames_total = n_frames;

        if n_frames < 2
            error('SPM realignment requires at least 2 frames.');
        end

        scans = cell(n_frames, 1);
        for i = 1:n_frames
            scans{i} = [input_nii, ',', num2str(i)];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.realign.estwrite.data = {scans};
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.quality = 0.9;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.sep = 4;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.fwhm = 5;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.rtm = 1;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.interp = 2;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.wrap = [0 0 0];
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.weight = '';
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.which = [2 1];
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.interp = 4;
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.wrap = [0 0 0];
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.mask = 1;
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.prefix = 'r';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);

        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        realigned_file = fullfile(input_dir, ['r', input_name, '.nii']);
        mean_file = fullfile(input_dir, ['mean', input_name, '.nii']);
        motion_file = fullfile(input_dir, ['rp_', input_name, '.txt']);

        if exist(realigned_file, 'file')
            result.realigned_files{end+1} = realigned_file;
        else
            result.warnings{end+1} = ['Expected realigned file not found: ', realigned_file];
        end

        if exist(mean_file, 'file')
            result.mean_file = mean_file;
        else
            result.warnings{end+1} = ['Expected mean file not found: ', mean_file];
        end

        if exist(motion_file, 'file')
            result.motion_parameter_file = motion_file;
        else
            result.warnings{end+1} = ['Expected motion parameter file not found: ', motion_file];
        end

        if isempty(result.realigned_files)
            error('SPM realign did not produce realigned output.');
        end

        if isempty(result.motion_parameter_file)
            error('SPM realign did not produce motion parameter file.');
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
3. 创建 backend/app/tools/spm_realign_runner.py

创建文件：

backend/app/tools/spm_realign_runner.py

目标：Python 调用 MATLAB SPM realignment wrapper。

提供函数：

run_spm_realign_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
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
调用 spm_realign_wrapper.m。
输出：
spm_realign_result.json
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


def run_spm_realign_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "spm_realign_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": ["SPM realignment requires approved=true."],
        }

    normalized_input = str(input_bold).replace("\\", "/")
    if "examples/synthetic_bids/rawdata" not in normalized_input:
        return {
            "ok": False,
            "node_id": "spm_realign_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [
                "Refusing to run SPM realignment on non-synthetic input.",
                f"Input was: {input_bold}",
            ],
        }

    out_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_realign_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_realign_stderr.log"
    result_json = out_dir / "spm_realign_result.json"

    try:
        prepared_input = _prepare_bold_input(
            input_bold=input_bold,
            subject_id=subject_id,
            derivatives_dir=derivatives_dir,
        )
    except Exception as exc:
        return {
            "ok": False,
            "node_id": "spm_realign_subject",
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
        f"spm_realign_wrapper('{_matlab_quote(str(Path(spm_dir).resolve()))}', "
        f"'{_matlab_quote(str(Path(prepared_input).resolve()))}', "
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
        "errors": ["SPM realignment did not produce result JSON."],
    }

    data["node_id"] = "spm_realign_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["returncode"] = completed.returncode
    data["prepared_input"] = prepared_input
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    outputs = list(data.get("realigned_files", []))
    if data.get("mean_file"):
        outputs.append(data["mean_file"])
    if data.get("motion_parameter_file"):
        outputs.append(data["motion_parameter_file"])
    outputs.extend([str(result_json), str(stdout_log), str(stderr_log)])

    data["outputs"] = sorted(set(outputs))
    return data
4. 创建 backend/app/tools/motion_qc.py

创建文件：

backend/app/tools/motion_qc.py

目标：根据 SPM rp_*.txt 计算 motion QC。

提供函数：

compute_motion_qc_for_subject(
    subject_id: str,
    motion_parameter_file: str,
    derivatives_dir: str,
    fd_threshold: float = 0.5,
    head_radius_mm: float = 50.0,
) -> dict

write_motion_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict

计算规则：

SPM motion params 6列：
x, y, z translations in mm
pitch, roll, yaw rotations in radians
FD 使用 Power-style approximation：
diff translations absolute sum
diff rotations absolute sum * head_radius_mm
第一帧 FD = 0

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median
from typing import Any


def _read_motion_params(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        values = [float(item) for item in line.split()]
        if len(values) < 6:
            raise ValueError(f"Motion parameter row has fewer than 6 columns: {line}")
        rows.append(values[:6])

    if not rows:
        raise ValueError("Motion parameter file is empty.")

    return rows


def _framewise_displacement(
    rows: list[list[float]],
    head_radius_mm: float,
) -> list[float]:
    fd = [0.0]

    for i in range(1, len(rows)):
        prev = rows[i - 1]
        curr = rows[i]

        trans = sum(abs(curr[j] - prev[j]) for j in range(3))
        rot = sum(abs(curr[j] - prev[j]) for j in range(3, 6)) * head_radius_mm

        fd.append(float(trans + rot))

    return fd


def compute_motion_qc_for_subject(
    subject_id: str,
    motion_parameter_file: str,
    derivatives_dir: str,
    fd_threshold: float = 0.5,
    head_radius_mm: float = 50.0,
) -> dict[str, Any]:
    out_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "motion_qc.json"
    qc_md = out_dir / "motion_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    motion_path = Path(motion_parameter_file)

    if not motion_path.exists():
        result = {
            "ok": False,
            "node_id": "motion_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": motion_parameter_file,
            "outputs": [],
            "warnings": warnings,
            "errors": [f"Motion parameter file not found: {motion_path}"],
        }
        qc_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        rows = _read_motion_params(motion_path)
        fd = _framewise_displacement(rows, head_radius_mm=head_radius_mm)

        high_motion = [value for value in fd if value > fd_threshold]
        translations = [[row[0], row[1], row[2]] for row in rows]
        rotations = [[row[3], row[4], row[5]] for row in rows]

        translation_max_abs_mm = max(abs(value) for row in translations for value in row)
        rotation_max_abs_rad = max(abs(value) for row in rotations for value in row)

        mean_fd = float(mean(fd))
        median_fd = float(median(fd))
        max_fd = float(max(fd))
        high_motion_frame_count = len(high_motion)
        high_motion_fraction = high_motion_frame_count / len(fd)

        if high_motion_fraction >= 0.2:
            motion_qc_status = "FAIL"
        elif high_motion_frame_count > 0:
            motion_qc_status = "WARNING"
        else:
            motion_qc_status = "PASS"

        result = {
            "ok": True,
            "node_id": "motion_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "frames_total": len(fd),
            "fd": fd,
            "fd_threshold": fd_threshold,
            "head_radius_mm": head_radius_mm,
            "mean_fd": mean_fd,
            "median_fd": median_fd,
            "max_fd": max_fd,
            "high_motion_frame_count": high_motion_frame_count,
            "high_motion_fraction": high_motion_fraction,
            "translation_max_abs_mm": float(translation_max_abs_mm),
            "rotation_max_abs_rad": float(rotation_max_abs_rad),
            "motion_qc_status": motion_qc_status,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        result = {
            "ok": False,
            "node_id": "motion_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": [str(exc)],
        }

    qc_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"# Motion QC: {subject_id}")
    lines.append("")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Status: {result.get('motion_qc_status')}")
    lines.append(f"- Frames total: {result.get('frames_total')}")
    lines.append(f"- Mean FD: {result.get('mean_fd')}")
    lines.append(f"- Median FD: {result.get('median_fd')}")
    lines.append(f"- Max FD: {result.get('max_fd')}")
    lines.append(f"- FD threshold: {result.get('fd_threshold')}")
    lines.append(f"- High-motion frames: {result.get('high_motion_frame_count')}")
    lines.append(f"- High-motion fraction: {result.get('high_motion_fraction')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Motion QC reads derivative motion parameters only and does not modify rawdata.")

    qc_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_motion_qc_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/motion_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("motion_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("motion_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("motion_qc_status") == "FAIL")

    mean_fds = [float(item.get("mean_fd")) for item in subjects if item.get("mean_fd") is not None]
    max_fds = [float(item.get("max_fd")) for item in subjects if item.get("max_fd") is not None]

    summary = {
        "ok": fail_count == 0 and subjects_total > 0,
        "node_id": "motion_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "group_mean_fd": float(mean(mean_fds)) if mean_fds else None,
        "group_max_fd": float(max(max_fds)) if max_fds else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "motion_qc_summary.json"
    report_path = report_out / "motion_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Motion QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Group mean FD: {summary['group_mean_fd']}")
    lines.append(f"- Group max FD: {summary['group_max_fd']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Mean FD | Max FD | High-motion frames |")
    lines.append("|---|---|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('motion_qc_status')} | "
            f"{item.get('mean_fd')} | {item.get('max_fd')} | "
            f"{item.get('high_motion_frame_count')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative motion QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "motion_qc_dataset_report",
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
5. 修改 backend/app/runtime/node_registry.py

新增节点：

spm_realign_subject
motion_qc_subject
motion_qc_dataset_report

新增导入：

from backend.app.tools.spm_realign_runner import run_spm_realign_subject
from backend.app.tools.motion_qc import (
    compute_motion_qc_for_subject,
    write_motion_qc_dataset_report,
)

新增 runner：

def _find_subject_bold(subject_record: dict[str, Any]) -> str | None:
    for session in subject_record.get("sessions", []):
        for func in session.get("func", []):
            if func.get("bold"):
                return func.get("bold")
    return None


def run_spm_realign_subject_node(
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

    result = run_spm_realign_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_id=context.subject_id,
        input_bold=bold,
        derivatives_dir=context.derivatives_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=bool(node.params.get("approved", False)),
        matlab_script_dir="./matlab",
    )

    result["node_id"] = node.id
    return result


def run_motion_qc_subject_node(
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

    motion_file = (
        Path(context.derivatives_dir)
        / "rsfmri_preproc"
        / context.subject_id
        / "func"
        / f"rp_{context.subject_id}_bold.txt"
    )

    result = compute_motion_qc_for_subject(
        subject_id=context.subject_id,
        motion_parameter_file=str(motion_file),
        derivatives_dir=context.derivatives_dir,
        fd_threshold=float(node.params.get("fd_threshold", 0.5)),
        head_radius_mm=float(node.params.get("head_radius_mm", 50.0)),
    )

    result["node_id"] = node.id
    return result


def run_motion_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_motion_qc_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result

如果 Path / Any 没有导入，请在文件顶部加入：

from pathlib import Path
from typing import Any

更新 NODE_REGISTRY：

"spm_realign_subject": run_spm_realign_subject_node,
"motion_qc_subject": run_motion_qc_subject_node,
"motion_qc_dataset_report": run_motion_qc_dataset_report_node,
6. 创建 examples/pipeline_rsfmri_spm_realign_motion_qc.yaml

创建文件：

examples/pipeline_rsfmri_spm_realign_motion_qc.yaml

内容：

pipeline_id: rsfmri_spm_realign_motion_qc_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run approved SPM realignment on synthetic rs-fMRI data and compute motion QC."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_spm_realign_motion_qc_001"
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

  - id: spm_realign_subject
    name: Approved SPM Realignment
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

  - id: motion_qc_dataset_report
    name: Motion QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - motion_qc_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/motion_qc_summary.json"
      - "./reports/rsfmri/motion_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

注意：默认 approved: false，直接运行应该安全失败。真正执行必须通过 CLI/API 显式 approval。

7. 创建 backend/app/tools/run_rsfmri_spm_realign_motion_qc_cli.py

创建文件：

backend/app/tools/run_rsfmri_spm_realign_motion_qc_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_rsfmri_spm_realign_motion_qc.yaml
默认不 approved。
如果传入 --approve，生成 approved pipeline 副本：
work/rsfmri/approved_pipeline_spm_realign_motion_qc.yaml

并把：

spm_realign_subject.params.approved = true

参考实现：

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
        if node.get("id") == "spm_realign_subject":
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_spm_realign_motion_qc.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("work/rsfmri/approved_pipeline_spm_realign_motion_qc.yaml"),
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
8. 修改 backend/app/api/models.py

新增 request model：

class RsfmriSpmRealignMotionQcRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_spm_realign_motion_qc.yaml")
    approved: bool = Field(default=False)
9. 修改 backend/app/api/routes.py

新增 API：

POST /api/rsfmri/spm-realign-motion-qc/run
GET  /api/rsfmri/spm-realign-motion-qc

新增导入：

from backend.app.api.models import RsfmriSpmRealignMotionQcRequest
from backend.app.runtime.pipeline_executor import run_pipeline

新增辅助函数：

def _make_spm_realign_motion_qc_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") == "spm_realign_subject":
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target

新增路由：

@router.post("/api/rsfmri/spm-realign-motion-qc/run")
def api_run_rsfmri_spm_realign_motion_qc(
    request: RsfmriSpmRealignMotionQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="SPM realignment requires approved=true.",
        )

    try:
        approved_pipeline = _make_spm_realign_motion_qc_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_spm_realign_motion_qc.yaml"),
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


@router.get("/api/rsfmri/spm-realign-motion-qc")
def api_get_rsfmri_spm_realign_motion_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/motion_qc.json")):
        subject_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "motion_qc_summary": _read_json_if_exists(report_base / "motion_qc_summary.json"),
        "motion_qc_report": _read_text_if_exists(report_base / "motion_qc_report.md"),
        "subject_motion_qc": subject_qc,
    }
10. 修改 frontend/src/api.ts

新增：

export async function runRsfmriSpmRealignMotionQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-realign-motion-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriSpmRealignMotionQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-realign-motion-qc"
  );
}
11. 创建 frontend/src/components/RsfmriMotionQcPanel.tsx

创建文件：

frontend/src/components/RsfmriMotionQcPanel.tsx

内容：

import { useState } from "react";
import {
  getRsfmriSpmRealignMotionQc,
  runRsfmriSpmRealignMotionQc
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriMotionQcPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 SPM realignment + motion QC？这只处理 synthetic BIDS 数据，不会修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriSpmRealignMotionQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_spm_realign_motion_qc.yaml",
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
      const response = await getRsfmriSpmRealignMotionQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.motion_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 SPM Realign + Motion QC
        </button>
        <button onClick={handleLoad}>加载 Motion QC 结果</button>
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
          <span>Group Mean FD</span>
          <strong>
            {summary?.group_mean_fd == null
              ? "-"
              : Number(summary.group_mean_fd).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Motion QC Summary</h3>
      <JsonBlock value={loaded?.motion_qc_summary} emptyText="暂无 motion QC summary" />

      <h3>Subject Motion QC</h3>
      <JsonBlock value={loaded?.subject_motion_qc} emptyText="暂无 subject motion QC" />

      <h3>Motion QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.motion_qc_report === "string"
            ? loaded.motion_qc_report
            : null
        }
        emptyText="暂无 motion QC report"
      />
    </div>
  );
}
12. 修改 frontend/src/App.tsx

新增导入：

import { RsfmriMotionQcPanel } from "./components/RsfmriMotionQcPanel";

在 rs-fMRI Core Preprocessing Plan 后新增 Section：

<Section
  title="rs-fMRI SPM Realignment + Motion QC"
  description="对 synthetic rs-fMRI BOLD 执行 SPM realign，并计算 FD 等运动质控指标。"
>
  <RsfmriMotionQcPanel baseUrl={baseUrl} />
</Section>
13. 新增轻量测试

创建文件：

tests/unit/test_motion_qc.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.motion_qc import compute_motion_qc_for_subject


def test_motion_qc_computes_fd(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    motion_file = tmp_path / "rp_test.txt"

    motion_file.write_text(
        "\n".join([
            "0 0 0 0 0 0",
            "1 0 0 0 0 0",
            "1 1 0 0 0.01 0",
        ]),
        encoding="utf-8",
    )

    result = compute_motion_qc_for_subject(
        subject_id="sub-001",
        motion_parameter_file=str(motion_file),
        derivatives_dir=str(derivatives),
        fd_threshold=0.5,
        head_radius_mm=50.0,
    )

    assert result["ok"] is True
    assert result["frames_total"] == 3
    assert result["fd"][0] == 0.0
    assert result["fd"][1] == 1.0
    assert result["fd"][2] == 1.5
    assert result["high_motion_frame_count"] == 2

    qc_path = derivatives / "rsfmri_qc" / "sub-001" / "motion_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
14. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/rsfmri/spm-realign-motion-qc")

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

15. 更新 README.md

追加第三十五步说明：

## Step 35: SPM Realignment and Motion QC

This step implements the first real core rs-fMRI preprocessing wrapper.

It supports:

- approved SPM realignment
- synthetic BIDS-like input only
- realigned BOLD output
- mean functional image output
- motion parameter file output
- framewise displacement calculation
- subject-level motion QC
- dataset-level motion QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli

This should fail safely because approval is missing.

Run with approval
python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_spm_realign_motion_qc.yaml --approve

Expected outputs:

derivatives/rsfmri_preproc/sub-001/func/rsub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/meansub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/rp_sub-001_bold.txt
derivatives/rsfmri_preproc/sub-001/func/spm_realign_result.json
derivatives/rsfmri_qc/sub-001/motion_qc.json
derivatives/rsfmri_qc/sub-001/motion_qc.md
reports/rsfmri/motion_qc_summary.json
reports/rsfmri/motion_qc_report.md
work/pipeline_runs/run_rsfmri_spm_realign_motion_qc_001/summary.json
API
curl http://127.0.0.1:8000/api/rsfmri/spm-realign-motion-qc

Run approved:

curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_spm_realign_motion_qc.yaml",
    "approved": true
  }'
Frontend

Use:

rs-fMRI SPM Realignment + Motion QC
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

## 16. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/spm_realign_motion_qc_spec.md
matlab/spm_realign_wrapper.m
backend/app/tools/spm_realign_runner.py
backend/app/tools/motion_qc.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_spm_realign_motion_qc.yaml
backend/app/tools/run_rsfmri_spm_realign_motion_qc_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriMotionQcPanel.tsx
frontend/src/App.tsx
tests/unit/test_motion_qc.py
backend/app/tools/api_smoke_test.py
README.md

先运行不带 approval：

python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli

应该安全失败，不应启动 SPM realignment。

然后运行 approved：

python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_spm_realign_motion_qc.yaml --approve

如果本地 MATLAB + SPM 可用，应生成：

derivatives/rsfmri_preproc/sub-001/func/rsub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/meansub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/rp_sub-001_bold.txt
derivatives/rsfmri_qc/sub-001/motion_qc.json
reports/rsfmri/motion_qc_summary.json
reports/rsfmri/motion_qc_report.md

motion QC JSON 必须包含：

{
  "node_id": "motion_qc_subject",
  "subject_id": "sub-001",
  "frames_total": 0,
  "mean_fd": 0,
  "max_fd": 0,
  "high_motion_frame_count": 0,
  "motion_qc_status": "PASS"
}

实际数值根据 synthetic 数据和 SPM 输出决定。

运行测试：

python -m pytest tests/unit/test_motion_qc.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/rsfmri/spm-realign-motion-qc

curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'

未批准 POST 必须返回 403。

批准 POST 可运行：

curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 rs-fMRI SPM Realignment + Motion QC 区域。
可以点击批准并运行。
点击运行前有 confirm 弹窗。
可以加载 motion QC 结果。
显示 subject 数量。
显示 PASS / WARNING / FAIL 数量。
显示 group mean FD。
显示 motion QC summary JSON。
显示 subject motion QC JSON。
显示 motion QC Markdown report。
不修改 rawdata。
不运行 DPABI。
不调用 DPARSF_run / DPARSFA_run。
不执行完整 preprocessing。
17. 重要限制

本步骤只做 SPM realignment + motion QC。

不要实现：

slice timing
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
SPM realignment wrapper 如何工作
motion QC 如何计算 FD
输出哪些 derivatives
输出哪些 QC report
为什么本步骤仍然不是完整 preprocessing
下一步如何实现 Slice Timing Correction 或 Coregistration + Registration QC

'''
这一步做了三件事，把 rs-fMRI 预处理流水线里第一个真正执行计算的环节跑通了。

**第一，写了一个 MATLAB wrapper 让 SPM 真的跑起来。** 新建了 `matlab/spm_realign_wrapper.m`，它会接收一个 4D BOLD NIfTI，调用 SPM 的 `realign.estwrite` 做头动校正，输出三个产物：校正后的 BOLD（`r*.nii`）、平均功能像（`mean*.nii`）、以及 6 列头动参数文件（`rp_*.txt`）。同时 `spm_realign_runner.py` 作为 Python 侧调度器，负责安全检查——必须 `approved=true` 才会启动 MATLAB，而且只允许处理 `examples/synthetic_bids/rawdata` 下的合成数据，任何其他路径直接拒绝。

**第二，写了一个 motion QC 模块。** 新建了 `motion_qc.py`，它读取 SPM 产出的 rp_*.txt，用 Power 方法计算 framewise displacement：相邻帧之间 3 个平移参数的绝对差之和，加上 3 个旋转参数绝对差乘以头部半径 50mm。然后统计 mean FD、max FD、median FD、高运动帧数和比例，判定 PASS / WARNING / FAIL。每个 subject 输出一份 `motion_qc.json` 和 `motion_qc.md`，再汇总成 dataset 级别的报告。

**第三，把这套 SPM realign + motion QC 接入了全栈。** 在 node_registry 注册了三个新节点（`spm_realign_subject`、`motion_qc_subject`、`motion_qc_dataset_report`），创建了新的 pipeline YAML（6 个节点串起来，默认 approved=false 所以直接运行会安全失败），加了 CLI（`--approve` 才真正执行），API 暴露了 GET（查看结果）和 POST（带审批执行，未批准返回 403），前端新增了一个面板可以点击运行并查看 FD 指标和报告。

简单说，这一步从 "只有纸面协议和步骤注册表" 推进到了 "SPM 真正跑了一次合成数据的头动校正 + 计算出了可审查的 QC 指标"。
'''