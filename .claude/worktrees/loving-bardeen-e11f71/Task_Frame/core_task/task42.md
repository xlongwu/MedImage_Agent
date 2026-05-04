# 第四十二步 Prompt：Nuisance Regression 参数计划 + Confound Matrix + Python/DPABI 双后端设计闭环

```text
你是我的工程搭建助手。前四十一步已经完成：

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

现在开始第四十二步。

第四十二步目标：实现 “Nuisance Regression 参数计划 + Confound Matrix + Python/DPABI 双后端设计闭环”。

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

但还缺少 rs-fMRI 后处理中的关键步骤：nuisance regression。  
本步骤要把 motion parameters、tissue maps、linear trend 等 confounds 组织成可审查的 regression design，并先实现一个安全的 Python 后端 MVP，同时保留 DPABI 后端 contract，但本步骤不要真正执行 DPABI。

本步骤要实现：

1. nuisance regression specification。
2. nuisance regression 参数 schema。
3. confound matrix builder：
   - motion 6 parameters
   - Friston 24 motion model
   - linear trend
   - optional intercept
   - tissue regressors 占位设计
   - optional global signal 开关，但默认 false
4. confound matrix QC：
   - shape
   - rank
   - condition number
   - NaN / Inf 检查
   - column summary
   - regressors count
5. Python nuisance regression backend：
   - 输入 smoothed normalized functional `swr*.nii`
   - 输入 confound matrix TSV / JSON
   - 对每个 voxel time series 做 OLS residualization
   - 输出 regressed functional `resid_swr*.nii`
   - 保留 affine/header
   - 输出 regression result JSON
6. DPABI backend contract：
   - 仅生成 contract / plan
   - 不执行 DPABI
   - 不调用 DPARSF_run / DPARSFA_run
   - 不调用 DPABI GUI
7. subject-level nuisance regression QC：
   - residual output exists
   - input/output shape consistency
   - finite fraction
   - residual mean/std
   - variance ratio
   - confound rank
   - regression_qc_status
8. dataset-level nuisance regression QC summary / Markdown report。
9. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC → Normalization → Normalization QC → Smoothing → Smoothing QC → Confound Matrix → Python Nuisance Regression → Regression QC
10. 后端 API 暴露 nuisance regression 结果。
11. 前端新增 rs-fMRI Nuisance Regression 面板。
12. 增加轻量 unit test。
13. 更新 README。

本步骤允许执行 Python nuisance regression，但必须满足：

- 只处理 synthetic BIDS-like derivative 数据。
- nuisance regression 输入必须来自 derivatives 中的 smoothed normalized output。
- motion 参数必须来自 derivatives 中的 realignment output。
- tissue maps 必须来自 derivatives 中的 segmentation output。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不修改 SPM / DPABI 源码。
- 不删除文件。

本步骤不要实现：

- temporal filtering
- ALFF / fALFF / ReHo
- 真实 DPABI nuisance regression 执行
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：nuisance regression 参数计划、confound matrix、Python backend MVP、DPABI backend contract。

---

## 1. 创建 specs/nuisance_regression_spec.md

创建文件：

```text
specs/nuisance_regression_spec.md
```

内容：

```markdown
# Nuisance Regression Specification

This document defines the MVP nuisance regression stage for rs-fMRI preprocessing.

## Goals

The goal is to build an auditable nuisance regression design, generate a confound matrix, execute a safe Python nuisance regression backend on synthetic derivatives, and define a future DPABI backend contract.

This step prepares cleaned rs-fMRI data for temporal filtering and ALFF/fALFF/ReHo computation.

## Scope

Supported in this step:

- synthetic derivative input only
- confound matrix generation
- motion 6 regressors
- Friston 24 motion model
- intercept and linear trend
- optional tissue regressor placeholders
- optional global signal flag default false
- Python OLS residualization backend
- DPABI backend contract generation without execution
- subject-level regression QC JSON / Markdown
- dataset-level regression QC summary / report
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- temporal filtering
- ALFF / fALFF / ReHo
- rawdata modification
- source modification in SPM / DPABI
- file deletion

## Inputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/swr*.nii
derivatives/rsfmri_preproc/{subject_id}/func/rp_*.txt
derivatives/rsfmri_preproc/{subject_id}/anat/c1coreg_{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/c2coreg_{subject_id}_T1w.nii
derivatives/rsfmri_preproc/{subject_id}/anat/c3coreg_{subject_id}_T1w.nii
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_confounds/{subject_id}/confounds.tsv
derivatives/rsfmri_confounds/{subject_id}/confounds.json
derivatives/rsfmri_confounds/{subject_id}/confound_qc.json
derivatives/rsfmri_preproc/{subject_id}/func/resid_swr*.nii
derivatives/rsfmri_preproc/{subject_id}/func/nuisance_regression_result.json
derivatives/rsfmri_qc/{subject_id}/nuisance_regression_qc.json
derivatives/rsfmri_qc/{subject_id}/nuisance_regression_qc.md
reports/rsfmri/nuisance_regression_qc_summary.json
reports/rsfmri/nuisance_regression_qc_report.md
work/dpabi/contracts/nuisance_regression_backend_contract.json
```

## Regressor Families

Supported in MVP:

- intercept
- linear_trend
- motion_6
- motion_derivatives
- motion_squared
- motion_derivatives_squared

Deferred:

- WM mean signal
- CSF mean signal
- global signal
- scrubbing regressors
- CompCor
- ICA-AROMA

## Backend Modes

### python

Runs OLS residualization directly in Python.

### dpabi_contract

Generates a DPABI backend contract and execution plan only. Does not execute DPABI.

## QC Metrics

- input_exists
- output_exists
- input_shape
- output_shape
- confound_shape
- confound_rank
- confound_condition_number
- finite_fraction
- residual_mean
- residual_std
- variance_ratio
- regression_qc_status

## Safety Rules

- Only derivative smoothed normalized functional input is allowed.
- Only derivative motion parameter input is allowed.
- Do not modify rawdata.
- Do not delete files.
- Do not execute DPABI in this step.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Write outputs only under derivatives, work, reports, and logs.
```

---

## 2. 创建 backend/app/tools/confound_matrix.py

创建文件：

```text
backend/app/tools/confound_matrix.py
```

目标：从 SPM motion parameters 和配置生成 nuisance regression confound matrix。

提供函数：

```python
build_confound_matrix_for_subject(
    subject_id: str,
    motion_parameter_file: str,
    output_dir: str,
    model: str = "friston24",
    include_intercept: bool = True,
    include_linear_trend: bool = True,
    include_global_signal: bool = False,
) -> dict
```

输出：

```text
derivatives/rsfmri_confounds/{subject_id}/confounds.tsv
derivatives/rsfmri_confounds/{subject_id}/confounds.json
derivatives/rsfmri_confounds/{subject_id}/confound_qc.json
```

实现要求：

1. 支持 SPM rp_*.txt 6列 motion params。
2. `model="motion6"`：
   - 6列 motion
3. `model="friston24"`：
   - motion 6
   - derivatives 6
   - motion squared 6
   - derivatives squared 6
4. 第一帧 derivatives 为 0。
5. include_intercept=true 时加入 intercept。
6. include_linear_trend=true 时加入 linear_trend，范围 -1 到 1。
7. include_global_signal=true 时不要真正计算 global signal，本步骤只记录 warning：
   - "global_signal requested but not implemented in Step 42"
8. 生成 TSV 和 JSON。
9. 计算 QC：
   - rows
   - columns
   - rank
   - condition_number
   - has_nan
   - has_inf
   - column_names
10. 不读取 functional data。
11. 不修改 rawdata。

参考实现：

```python
from __future__ import annotations

import csv
import json
from pathlib import Path
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


def _diff_rows(rows: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for i, row in enumerate(rows):
        if i == 0:
            out.append([0.0] * len(row))
        else:
            prev = rows[i - 1]
            out.append([float(row[j] - prev[j]) for j in range(len(row))])
    return out


def _square_rows(rows: list[list[float]]) -> list[list[float]]:
    return [[float(value * value) for value in row] for row in rows]


def _transpose_columns(rows: list[list[float]], names: list[str]) -> list[dict[str, float]]:
    out = []
    for row in rows:
        out.append({name: float(value) for name, value in zip(names, row)})
    return out


def _matrix_qc(matrix: list[list[float]]) -> dict[str, Any]:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: numpy is required.") from exc

    arr = np.asarray(matrix, dtype=float)

    has_nan = bool(np.isnan(arr).any())
    has_inf = bool(np.isinf(arr).any())

    if arr.size == 0:
        rank = 0
        condition_number = None
    else:
        rank = int(np.linalg.matrix_rank(arr))
        try:
            condition_number = float(np.linalg.cond(arr))
        except Exception:
            condition_number = None

    return {
        "rows": int(arr.shape[0]) if arr.ndim == 2 else 0,
        "columns": int(arr.shape[1]) if arr.ndim == 2 else 0,
        "rank": rank,
        "condition_number": condition_number,
        "has_nan": has_nan,
        "has_inf": has_inf,
    }


def build_confound_matrix_for_subject(
    subject_id: str,
    motion_parameter_file: str,
    output_dir: str,
    model: str = "friston24",
    include_intercept: bool = True,
    include_linear_trend: bool = True,
    include_global_signal: bool = False,
) -> dict[str, Any]:
    out_dir = Path(output_dir) / "rsfmri_confounds" / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    confounds_tsv = out_dir / "confounds.tsv"
    confounds_json = out_dir / "confounds.json"
    confound_qc_json = out_dir / "confound_qc.json"

    warnings: list[str] = []
    errors: list[str] = []

    motion_path = Path(motion_parameter_file)

    if not motion_path.exists():
        result = {
            "ok": False,
            "node_id": "confound_matrix_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "outputs": [],
            "warnings": warnings,
            "errors": [f"Motion parameter file not found: {motion_path}"],
        }
        confound_qc_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        motion = _read_motion_params(motion_path)
        n_tp = len(motion)

        base_names = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]
        motion_derivatives = _diff_rows(motion)

        columns: list[str] = []
        matrix_columns: list[list[float]] = []

        def add_family(names: list[str], rows: list[list[float]]) -> None:
            columns.extend(names)
            for col_idx in range(len(names)):
                matrix_columns.append([float(row[col_idx]) for row in rows])

        if include_intercept:
            columns.append("intercept")
            matrix_columns.append([1.0] * n_tp)

        if include_linear_trend:
            columns.append("linear_trend")
            if n_tp == 1:
                matrix_columns.append([0.0])
            else:
                matrix_columns.append([-1.0 + 2.0 * i / (n_tp - 1) for i in range(n_tp)])

        if model == "motion6":
            add_family(base_names, motion)
        elif model == "friston24":
            add_family(base_names, motion)
            add_family([f"{name}_derivative" for name in base_names], motion_derivatives)
            add_family([f"{name}_power2" for name in base_names], _square_rows(motion))
            add_family([f"{name}_derivative_power2" for name in base_names], _square_rows(motion_derivatives))
        else:
            raise ValueError(f"Unsupported nuisance model: {model}")

        if include_global_signal:
            warnings.append("global_signal requested but not implemented in Step 42.")

        matrix = [
            [matrix_columns[col_idx][row_idx] for col_idx in range(len(matrix_columns))]
            for row_idx in range(n_tp)
        ]

        qc = _matrix_qc(matrix)
        qc["column_names"] = columns

        with confounds_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(columns)
            writer.writerows(matrix)

        payload = {
            "subject_id": subject_id,
            "model": model,
            "include_intercept": include_intercept,
            "include_linear_trend": include_linear_trend,
            "include_global_signal": include_global_signal,
            "motion_parameter_file": str(motion_path),
            "confounds_tsv": str(confounds_tsv),
            "columns": columns,
            "qc": qc,
            "warnings": warnings,
            "errors": errors,
        }

        confounds_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        result = {
            "ok": not qc["has_nan"] and not qc["has_inf"],
            "node_id": "confound_matrix_subject",
            "backend": "python",
            "subject_id": subject_id,
            "model": model,
            "confounds_tsv": str(confounds_tsv),
            "confounds_json": str(confounds_json),
            "confound_qc_json": str(confound_qc_json),
            "qc": qc,
            "outputs": [str(confounds_tsv), str(confounds_json), str(confound_qc_json)],
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        result = {
            "ok": False,
            "node_id": "confound_matrix_subject",
            "backend": "python",
            "subject_id": subject_id,
            "motion_parameter_file": str(motion_path),
            "outputs": [str(confound_qc_json)],
            "warnings": warnings,
            "errors": [str(exc)],
        }

    confound_qc_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
```

---

## 3. 创建 backend/app/tools/nuisance_regression.py

创建文件：

```text
backend/app/tools/nuisance_regression.py
```

目标：实现 Python OLS nuisance regression 和 QC。

提供函数：

```python
run_python_nuisance_regression_subject(
    subject_id: str,
    input_nii: str,
    confounds_tsv: str,
    derivatives_dir: str,
) -> dict

write_nuisance_regression_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. 输入必须是 derivatives 中的 `swr*.nii`。
2. 输出为同目录 `resid_{input_name}.nii`。
3. 使用 confounds.tsv 做 OLS：
   - Y: timepoints × voxels
   - X: timepoints × regressors
   - beta = pinv(X) @ Y
   - residual = Y - X @ beta
4. 保留 4D shape、affine、header。
5. 如果 input timepoints != confound rows，失败。
6. 生成：
   - `nuisance_regression_result.json`
   - `nuisance_regression_qc.json`
   - `nuisance_regression_qc.md`
7. QC：
   - finite fraction
   - input/output shape
   - residual mean/std
   - input std
   - variance ratio
   - confound rows/columns/rank
8. 不修改 input。
9. 不处理 rawdata。

参考实现：

```python
from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any


def _read_confounds(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)

    if not rows:
        raise ValueError("Confounds TSV is empty.")

    header = rows[0]
    matrix = [[float(value) for value in row] for row in rows[1:] if row]
    return header, matrix


def _matrix_rank(matrix: list[list[float]]) -> int:
    import numpy as np
    arr = np.asarray(matrix, dtype=float)
    return int(np.linalg.matrix_rank(arr))


def _safe_input_path(path: Path, subject_id: str, derivatives_dir: str) -> bool:
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

    return path.name.startswith("swr") and path.name.endswith(".nii")


def run_python_nuisance_regression_subject(
    subject_id: str,
    input_nii: str,
    confounds_tsv: str,
    derivatives_dir: str,
) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    input_path = Path(input_nii)
    confounds_path = Path(confounds_tsv)

    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    result_json = func_dir / "nuisance_regression_result.json"
    qc_json = qc_dir / "nuisance_regression_qc.json"
    qc_md = qc_dir / "nuisance_regression_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    if not input_path.exists():
        return _write_failure(subject_id, result_json, qc_json, qc_md, [f"Input NIfTI not found: {input_path}"])

    if not _safe_input_path(input_path, subject_id, derivatives_dir):
        return _write_failure(subject_id, result_json, qc_json, qc_md, [f"Unsafe nuisance regression input: {input_path}"])

    if not confounds_path.exists():
        return _write_failure(subject_id, result_json, qc_json, qc_md, [f"Confounds TSV not found: {confounds_path}"])

    try:
        columns, confounds = _read_confounds(confounds_path)
        X = np.asarray(confounds, dtype=np.float64)

        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")

        if data.ndim != 4:
            raise ValueError(f"Input NIfTI must be 4D. Shape was: {data.shape}")

        x, y, z, t = data.shape

        if X.shape[0] != t:
            raise ValueError(f"Confound rows {X.shape[0]} do not match timepoints {t}.")

        Y = data.reshape((-1, t)).T.astype(np.float64)

        beta = np.linalg.pinv(X) @ Y
        fitted = X @ beta
        residual = Y - fitted

        residual_4d = residual.T.reshape((x, y, z, t)).astype("float32")

        output_path = input_path.with_name(f"resid_{input_path.name}")
        out_img = nib.Nifti1Image(residual_4d, affine=img.affine, header=img.header)
        nib.save(out_img, str(output_path))

        finite_mask = np.isfinite(residual_4d)
        finite_fraction = float(np.count_nonzero(finite_mask) / residual_4d.size) if residual_4d.size else 0.0

        input_std = float(np.std(data))
        residual_std = float(np.std(residual_4d))
        variance_ratio = float(residual_std / input_std) if input_std > 0 else None

        rank = int(np.linalg.matrix_rank(X))

        status = "PASS"
        if finite_fraction < 0.95:
            status = "WARNING"
            warnings.append(f"Residual finite fraction {finite_fraction:.4f} below 0.95.")
        if variance_ratio is not None and variance_ratio > 1.2:
            status = "WARNING"
            warnings.append(f"Residual std larger than input std. Ratio={variance_ratio:.4f}.")

        qc = {
            "ok": True,
            "node_id": "nuisance_regression_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "output_nii": str(output_path),
            "confounds_tsv": str(confounds_path),
            "input_shape": list(data.shape),
            "output_shape": list(residual_4d.shape),
            "confound_rows": int(X.shape[0]),
            "confound_columns": int(X.shape[1]),
            "confound_rank": rank,
            "finite_fraction": finite_fraction,
            "input_intensity_std": input_std,
            "residual_mean": float(np.mean(residual_4d)),
            "residual_std": residual_std,
            "variance_ratio": variance_ratio,
            "regression_qc_status": status,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

        result = {
            "ok": True,
            "node_id": "python_nuisance_regression_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "output_nii": str(output_path),
            "confounds_tsv": str(confounds_path),
            "columns": columns,
            "qc": qc,
            "outputs": [str(output_path), str(result_json), str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        return _write_failure(subject_id, result_json, qc_json, qc_md, [str(exc)])

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_markdown(qc_md, qc)
    return result


def _write_failure(
    subject_id: str,
    result_json: Path,
    qc_json: Path,
    qc_md: Path,
    errors: list[str],
) -> dict[str, Any]:
    qc = {
        "ok": False,
        "node_id": "nuisance_regression_qc_subject",
        "backend": "python",
        "subject_id": subject_id,
        "regression_qc_status": "FAIL",
        "outputs": [str(qc_json), str(qc_md)],
        "warnings": [],
        "errors": errors,
    }

    result = {
        "ok": False,
        "node_id": "python_nuisance_regression_subject",
        "backend": "python",
        "subject_id": subject_id,
        "outputs": [str(result_json), str(qc_json), str(qc_md)],
        "warnings": [],
        "errors": errors,
    }

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_markdown(qc_md, qc)
    return result


def _write_qc_markdown(path: Path, qc: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# Nuisance Regression QC: {qc.get('subject_id')}")
    lines.append("")
    lines.append(f"- OK: {qc.get('ok')}")
    lines.append(f"- Status: {qc.get('regression_qc_status')}")
    lines.append(f"- Input: `{qc.get('input_nii')}`")
    lines.append(f"- Output: `{qc.get('output_nii')}`")
    lines.append(f"- Confounds: `{qc.get('confounds_tsv')}`")
    lines.append(f"- Confound shape: {qc.get('confound_rows')} x {qc.get('confound_columns')}")
    lines.append(f"- Confound rank: {qc.get('confound_rank')}")
    lines.append(f"- Finite fraction: {qc.get('finite_fraction')}")
    lines.append(f"- Residual std: {qc.get('residual_std')}")
    lines.append(f"- Variance ratio: {qc.get('variance_ratio')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Python nuisance regression reads derivative files only and does not modify rawdata.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_nuisance_regression_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/nuisance_regression_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid nuisance regression QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("regression_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("regression_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("regression_qc_status") == "FAIL")

    variance_ratios = [
        float(item["variance_ratio"])
        for item in subjects
        if item.get("variance_ratio") is not None
    ]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "nuisance_regression_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_variance_ratio": float(mean(variance_ratios)) if variance_ratios else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "nuisance_regression_qc_summary.json"
    report_path = report_out / "nuisance_regression_qc_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Nuisance Regression QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean variance ratio: {summary['mean_variance_ratio']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Confounds | Rank | Variance Ratio |")
    lines.append("|---|---|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('regression_qc_status')} | "
            f"{item.get('confound_columns')} | {item.get('confound_rank')} | "
            f"{item.get('variance_ratio')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative nuisance regression QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "nuisance_regression_qc_dataset_report",
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

## 4. 创建 backend/app/tools/dpabi_nuisance_contract.py

创建文件：

```text
backend/app/tools/dpabi_nuisance_contract.py
```

目标：生成 DPABI nuisance regression backend contract，但不执行 DPABI。

提供函数：

```python
write_dpabi_nuisance_regression_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/dpabi/contracts/nuisance_regression_backend_contract.json
```

内容要求：

- backend_id: `dpabi_nuisance_regression`
- status: `CONTRACT_ONLY`
- execution_allowed: false
- blocked_functions:
  - DPARSF_run
  - DPARSFA_run
- required_approval: true
- planned_inputs:
  - smoothed normalized functional
  - motion params
  - tissue masks
- planned_outputs:
  - nuisance-regressed functional
  - regression logs
- safety flags:
  - dpabi_executed=false
  - dparsf_run_executed=false
  - dparsfa_run_executed=false
  - dpabi_gui_called=false

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_dpabi_nuisance_regression_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "nuisance_regression_backend_contract.json"

    payload = {
        "ok": True,
        "node_id": "dpabi_nuisance_regression_contract",
        "backend": "python",
        "backend_id": "dpabi_nuisance_regression",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "required_approval": True,
        "description": "DPABI nuisance regression backend contract. This step does not execute DPABI.",
        "planned_inputs": [
            "derivatives/rsfmri_preproc/{subject_id}/func/swr*.nii",
            "derivatives/rsfmri_preproc/{subject_id}/func/rp_*.txt",
            "derivatives/rsfmri_preproc/{subject_id}/anat/c1*.nii",
            "derivatives/rsfmri_preproc/{subject_id}/anat/c2*.nii",
            "derivatives/rsfmri_preproc/{subject_id}/anat/c3*.nii"
        ],
        "planned_outputs": [
            "derivatives/rsfmri_preproc/{subject_id}/func/dpabi_regressed_swr*.nii",
            "logs/{subject_id}_dpabi_nuisance_regression.log"
        ],
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
            "This is a contract only. DPABI nuisance regression execution is intentionally not implemented in Step 42."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 5. 创建 backend/app/tools/nuisance_regression_runner.py

创建文件：

```text
backend/app/tools/nuisance_regression_runner.py
```

目标：将 confound matrix 和 Python nuisance regression 连接起来。

提供函数：

```python
run_nuisance_regression_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    model: str = "friston24",
    include_intercept: bool = True,
    include_linear_trend: bool = True,
    include_global_signal: bool = False,
) -> dict
```

实现要求：

1. backend 支持：
   - `python`
   - `dpabi_contract`
2. `python`：
   - 查找 `swr*.nii`
   - 查找 `rp_*.txt`
   - 生成 confounds
   - 执行 Python nuisance regression
3. `dpabi_contract`：
   - 只返回 contract，不执行 DPABI
4. 输入安全：
   - `swr*.nii` 必须在 derivatives/rsfmri_preproc/{subject_id}/func
   - `rp_*.txt` 必须在同一 func 目录
5. 不修改 rawdata。

参考实现：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.tools.confound_matrix import build_confound_matrix_for_subject
from backend.app.tools.dpabi_nuisance_contract import write_dpabi_nuisance_regression_contract
from backend.app.tools.nuisance_regression import run_python_nuisance_regression_subject


def _find_smoothed_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    preferred = func_dir / f"swra{subject_id}_bold.nii"
    if preferred.exists():
        return preferred

    candidates = sorted(func_dir.glob("swr*.nii"))
    return candidates[0] if candidates else None


def _find_motion_params(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    candidates = sorted(func_dir.glob("rp_*.txt"))
    return candidates[0] if candidates else None


def _is_safe_subject_func_path(path: Path, subject_id: str, derivatives_dir: str) -> bool:
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

    return True


def run_nuisance_regression_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    model: str = "friston24",
    include_intercept: bool = True,
    include_linear_trend: bool = True,
    include_global_signal: bool = False,
) -> dict[str, Any]:
    if backend == "dpabi_contract":
        contract = write_dpabi_nuisance_regression_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend != "python":
        return {
            "ok": False,
            "node_id": "nuisance_regression_subject",
            "backend": backend,
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsupported nuisance regression backend: {backend}"],
        }

    input_func = _find_smoothed_functional(subject_id, derivatives_dir)
    if not input_func:
        return {
            "ok": False,
            "node_id": "nuisance_regression_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"No smoothed functional input found for subject {subject_id}."],
        }

    if not _is_safe_subject_func_path(input_func, subject_id, derivatives_dir) or not input_func.name.startswith("swr"):
        return {
            "ok": False,
            "node_id": "nuisance_regression_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsafe smoothed functional input: {input_func}"],
        }

    motion = _find_motion_params(subject_id, derivatives_dir)
    if not motion:
        return {
            "ok": False,
            "node_id": "nuisance_regression_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"No motion parameter file found for subject {subject_id}."],
        }

    if not _is_safe_subject_func_path(motion, subject_id, derivatives_dir):
        return {
            "ok": False,
            "node_id": "nuisance_regression_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsafe motion parameter input: {motion}"],
        }

    confounds = build_confound_matrix_for_subject(
        subject_id=subject_id,
        motion_parameter_file=str(motion),
        output_dir=derivatives_dir,
        model=model,
        include_intercept=include_intercept,
        include_linear_trend=include_linear_trend,
        include_global_signal=include_global_signal,
    )

    if not confounds.get("ok"):
        confounds["node_id"] = "nuisance_regression_subject"
        return confounds

    regression = run_python_nuisance_regression_subject(
        subject_id=subject_id,
        input_nii=str(input_func),
        confounds_tsv=confounds["confounds_tsv"],
        derivatives_dir=derivatives_dir,
    )

    outputs = []
    outputs.extend(confounds.get("outputs", []))
    outputs.extend(regression.get("outputs", []))

    return {
        "ok": bool(regression.get("ok")),
        "node_id": "nuisance_regression_subject",
        "backend": "python",
        "subject_id": subject_id,
        "input_nii": str(input_func),
        "motion_parameter_file": str(motion),
        "confounds": confounds,
        "regression": regression,
        "outputs": sorted(set(outputs)),
        "warnings": confounds.get("warnings", []) + regression.get("warnings", []),
        "errors": confounds.get("errors", []) + regression.get("errors", []),
    }
```

---

## 6. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
nuisance_regression_subject
nuisance_regression_qc_dataset_report
dpabi_nuisance_regression_contract
```

新增导入：

```python
from backend.app.tools.nuisance_regression_runner import run_nuisance_regression_subject
from backend.app.tools.nuisance_regression import write_nuisance_regression_dataset_report
from backend.app.tools.dpabi_nuisance_contract import write_dpabi_nuisance_regression_contract
```

新增 runner：

```python
def run_nuisance_regression_subject_node(
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

    result = run_nuisance_regression_subject(
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        backend=node.params.get("backend", "python"),
        model=node.params.get("model", "friston24"),
        include_intercept=bool(node.params.get("include_intercept", True)),
        include_linear_trend=bool(node.params.get("include_linear_trend", True)),
        include_global_signal=bool(node.params.get("include_global_signal", False)),
    )

    result["node_id"] = node.id
    return result


def run_nuisance_regression_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_nuisance_regression_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_dpabi_nuisance_regression_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_nuisance_regression_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"nuisance_regression_subject": run_nuisance_regression_subject_node,
"nuisance_regression_qc_dataset_report": run_nuisance_regression_qc_dataset_report_node,
"dpabi_nuisance_regression_contract": run_dpabi_nuisance_regression_contract_node,
```

---

## 7. 创建 examples/pipeline_rsfmri_nuisance_regression.yaml

创建文件：

```text
examples/pipeline_rsfmri_nuisance_regression.yaml
```

内容：

```yaml
pipeline_id: rsfmri_nuisance_regression_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run Python nuisance regression on smoothed normalized synthetic derivatives and generate DPABI backend contract."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_nuisance_regression_001"
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

  - id: dpabi_nuisance_regression_contract
    name: DPABI Nuisance Regression Backend Contract
    agent: contract-runner
    backend: python
    depends_on:
      - nuisance_regression_subject
    inputs: []
    outputs:
      - "./work/dpabi/contracts/nuisance_regression_backend_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: nuisance_regression_qc_dataset_report
    name: Nuisance Regression QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - nuisance_regression_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/nuisance_regression_qc_summary.json"
      - "./reports/rsfmri/nuisance_regression_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。  
Python nuisance regression 本身不需要 MATLAB approval，但它依赖前面的 SPM derivative 输出。

---

## 8. 创建 backend/app/tools/run_rsfmri_nuisance_regression_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_nuisance_regression_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_nuisance_regression.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("work/rsfmri/approved_pipeline_nuisance_regression.yaml"),
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
class RsfmriNuisanceRegressionRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_nuisance_regression.yaml")
    approved: bool = Field(default=False)
```

---

## 10. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/nuisance-regression/run
GET  /api/rsfmri/nuisance-regression
```

新增导入：

```python
from backend.app.api.models import RsfmriNuisanceRegressionRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_nuisance_regression_approved_copy(source: Path, target: Path) -> Path:
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
@router.post("/api/rsfmri/nuisance-regression/run")
def api_run_rsfmri_nuisance_regression(
    request: RsfmriNuisanceRegressionRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="Nuisance regression pipeline requires approved=true because it depends on approved SPM preprocessing derivatives.",
        )

    try:
        approved_pipeline = _make_nuisance_regression_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_nuisance_regression.yaml"),
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


@router.get("/api/rsfmri/nuisance-regression")
def api_get_rsfmri_nuisance_regression() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")
    work_base = Path("work") / "dpabi" / "contracts"

    subject_regression_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/nuisance_regression_qc.json")):
        subject_regression_qc.append(_read_json_if_exists(path))

    subject_confounds = []
    for path in sorted((derivatives_base / "rsfmri_confounds").glob("*/confound_qc.json")):
        subject_confounds.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "nuisance_regression_qc_summary": _read_json_if_exists(report_base / "nuisance_regression_qc_summary.json"),
        "nuisance_regression_qc_report": _read_text_if_exists(report_base / "nuisance_regression_qc_report.md"),
        "subject_nuisance_regression_qc": subject_regression_qc,
        "subject_confound_qc": subject_confounds,
        "dpabi_backend_contract": _read_json_if_exists(work_base / "nuisance_regression_backend_contract.json"),
    }
```

---

## 11. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriNuisanceRegression(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/nuisance-regression/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriNuisanceRegression(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/nuisance-regression"
  );
}
```

---

## 12. 创建 frontend/src/components/RsfmriNuisanceRegressionPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriNuisanceRegressionPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriNuisanceRegression,
  runRsfmriNuisanceRegression
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriNuisanceRegressionPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 Python Nuisance Regression？这只处理 synthetic derivatives，不会修改 rawdata，也不会执行 DPABI。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriNuisanceRegression(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_nuisance_regression.yaml",
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
      const response = await getRsfmriNuisanceRegression(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.nuisance_regression_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Python Nuisance Regression
        </button>
        <button onClick={handleLoad}>加载 Nuisance Regression 结果</button>
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

      <h3>Nuisance Regression QC Summary</h3>
      <JsonBlock value={loaded?.nuisance_regression_qc_summary} emptyText="暂无 nuisance regression QC summary" />

      <h3>Subject Nuisance Regression QC</h3>
      <JsonBlock value={loaded?.subject_nuisance_regression_qc} emptyText="暂无 subject nuisance regression QC" />

      <h3>Subject Confound QC</h3>
      <JsonBlock value={loaded?.subject_confound_qc} emptyText="暂无 subject confound QC" />

      <h3>DPABI Backend Contract</h3>
      <JsonBlock value={loaded?.dpabi_backend_contract} emptyText="暂无 DPABI backend contract" />

      <h3>Nuisance Regression QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.nuisance_regression_qc_report === "string"
            ? loaded.nuisance_regression_qc_report
            : null
        }
        emptyText="暂无 nuisance regression QC report"
      />
    </div>
  );
}
```

---

## 13. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriNuisanceRegressionPanel } from "./components/RsfmriNuisanceRegressionPanel";
```

在 `rs-fMRI SPM Smoothing + Smoothing QC` 后新增 Section：

```tsx
<Section
  title="rs-fMRI Nuisance Regression"
  description="构建 Friston24 confound matrix，执行 Python nuisance regression，并生成 DPABI 后端 contract。"
>
  <RsfmriNuisanceRegressionPanel baseUrl={baseUrl} />
</Section>
```

---

## 14. 新增轻量测试

创建文件：

```text
tests/unit/test_confound_matrix.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.confound_matrix import build_confound_matrix_for_subject


def test_confound_matrix_friston24_has_expected_columns(tmp_path: Path):
    motion_file = tmp_path / "rp_test.txt"
    motion_file.write_text(
        "\n".join([
            "0 0 0 0 0 0",
            "1 0 0 0 0 0",
            "1 1 0 0 0.01 0",
            "1 1 1 0 0.01 0.02",
        ]),
        encoding="utf-8",
    )

    result = build_confound_matrix_for_subject(
        subject_id="sub-001",
        motion_parameter_file=str(motion_file),
        output_dir=str(tmp_path),
        model="friston24",
        include_intercept=True,
        include_linear_trend=True,
    )

    assert result["ok"] is True
    assert result["qc"]["rows"] == 4
    assert result["qc"]["columns"] == 26
    assert "intercept" in result["qc"]["column_names"]
    assert "linear_trend" in result["qc"]["column_names"]

    confound_qc = Path(result["confound_qc_json"])
    assert confound_qc.exists()

    payload = json.loads(confound_qc.read_text(encoding="utf-8"))
    assert payload["subject_id"] == "sub-001"
```

---

## 15. 新增轻量测试

创建文件：

```text
tests/unit/test_nuisance_regression.py
```

内容：

```python
from __future__ import annotations

import csv
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.nuisance_regression import run_python_nuisance_regression_subject


def test_python_nuisance_regression_outputs_residual_nifti(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    func_dir.mkdir(parents=True)

    input_nii = func_dir / "swrasub-001_bold.nii"
    confounds = tmp_path / "confounds.tsv"

    rng = np.random.default_rng(42)
    data = rng.normal(size=(4, 4, 4, 6)).astype(np.float32)
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))

    with confounds.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["intercept", "linear_trend"])
        for i in range(6):
            writer.writerow([1.0, -1.0 + 2.0 * i / 5.0])

    result = run_python_nuisance_regression_subject(
        subject_id=subject_id,
        input_nii=str(input_nii),
        confounds_tsv=str(confounds),
        derivatives_dir=str(derivatives),
    )

    assert result["ok"] is True

    output_nii = func_dir / "resid_swrasub-001_bold.nii"
    assert output_nii.exists()

    qc_path = derivatives / "rsfmri_qc" / subject_id / "nuisance_regression_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == subject_id
    assert payload["regression_qc_status"] in {"PASS", "WARNING"}
```

---

## 16. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/nuisance-regression")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 17. 更新 README.md

追加第四十二步说明：

```markdown
## Step 42: Nuisance Regression, Confound Matrix, and DPABI Backend Contract

This step implements nuisance regression design and a Python backend MVP.

It supports:

- Friston24 confound matrix
- motion6 confound matrix
- intercept and linear trend
- Python OLS residualization
- subject-level nuisance regression QC
- dataset-level nuisance regression QC report
- DPABI backend contract generation without execution
- frontend visualization

It does not execute DPABI.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_nuisance_regression_cli
```

This should fail safely because upstream SPM steps are not approved.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_nuisance_regression_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_nuisance_regression.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_confounds/sub-001/confounds.tsv
derivatives/rsfmri_confounds/sub-001/confounds.json
derivatives/rsfmri_confounds/sub-001/confound_qc.json
derivatives/rsfmri_preproc/sub-001/func/resid_swrasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/nuisance_regression_result.json
derivatives/rsfmri_qc/sub-001/nuisance_regression_qc.json
derivatives/rsfmri_qc/sub-001/nuisance_regression_qc.md
reports/rsfmri/nuisance_regression_qc_summary.json
reports/rsfmri/nuisance_regression_qc_report.md
work/dpabi/contracts/nuisance_regression_backend_contract.json
work/pipeline_runs/run_rsfmri_nuisance_regression_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/nuisance-regression
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/nuisance-regression/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_nuisance_regression.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI Nuisance Regression
```

### Safety

This step:

- only processes derivative smoothed normalized functional input
- does not modify rawdata
- does not run DPABI
- only creates a DPABI backend contract
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing
```

---

## 18. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/nuisance_regression_spec.md
backend/app/tools/confound_matrix.py
backend/app/tools/nuisance_regression.py
backend/app/tools/dpabi_nuisance_contract.py
backend/app/tools/nuisance_regression_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_nuisance_regression.yaml
backend/app/tools/run_rsfmri_nuisance_regression_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriNuisanceRegressionPanel.tsx
frontend/src/App.tsx
tests/unit/test_confound_matrix.py
tests/unit/test_nuisance_regression.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_nuisance_regression_cli
```

应该安全失败，不应启动 SPM / DPABI。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_nuisance_regression_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_nuisance_regression.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_confounds/sub-001/confounds.tsv
derivatives/rsfmri_preproc/sub-001/func/resid_swrasub-001_bold.nii
derivatives/rsfmri_qc/sub-001/nuisance_regression_qc.json
reports/rsfmri/nuisance_regression_qc_summary.json
work/dpabi/contracts/nuisance_regression_backend_contract.json
```

nuisance regression QC JSON 必须包含：

```json
{
  "node_id": "nuisance_regression_qc_subject",
  "subject_id": "sub-001",
  "regression_qc_status": "PASS",
  "confound_rows": 0,
  "confound_columns": 0,
  "confound_rank": 0,
  "finite_fraction": 1.0
}
```

实际数值根据 synthetic 数据和 confound matrix 决定。

运行测试：

```bash
python -m pytest tests/unit/test_confound_matrix.py tests/unit/test_nuisance_regression.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/nuisance-regression

curl -X POST http://127.0.0.1:8000/api/rsfmri/nuisance-regression/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/nuisance-regression/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI Nuisance Regression 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 nuisance regression 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean variance ratio。
8. 显示 nuisance regression QC summary JSON。
9. 显示 subject nuisance regression QC JSON。
10. 显示 subject confound QC JSON。
11. 显示 DPABI backend contract。
12. 显示 nuisance regression QC Markdown report。
13. 不修改 rawdata。
14. 不运行 DPABI。
15. 不调用 DPARSF_run / DPARSFA_run。
16. 不执行完整 preprocessing。

---

## 19. 重要限制

本步骤只做 nuisance regression 参数计划、confound matrix、Python backend MVP、DPABI backend contract。

不要实现：

- temporal filtering
- ALFF / fALFF / ReHo
- 真实 DPABI nuisance regression 执行
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
3. confound matrix 如何生成
4. Friston24 包含哪些 regressors
5. Python nuisance regression 如何执行
6. DPABI backend contract 为什么只生成不执行
7. 输出哪些 derivatives 和 reports
8. 为什么本步骤仍然不是完整 preprocessing
9. 下一步如何实现 temporal filtering + Filtering QC，并把 resid_swr*.nii 接入 filtering

```
这一步做了三件事，全是纯 Python，没有调 MATLAB。

**写了 confound matrix 生成器。** `confound_matrix.py` 从 SPM realignment 产出的 `rp_*.txt`（6列头动参数）构建 Friston24 模型：6个原始参数 + 6个一阶差分 + 6个平方项 + 6个差分平方项，加上 intercept 和 linear_trend，共 26 列。同时计算矩阵 QC——rank、condition number、有无 NaN/Inf。输出 TSV 和 JSON 两种格式。

**写了 Python OLS nuisance regression。** `nuisance_regression.py` 读 smoothed normalized 功能像（`swr*.nii`）和 confound matrix，用 `pinv(X) @ Y` 做最小二乘拟合，把拟合值从原始信号里减掉，残差写成 `resid_*.nii`，保留原 header 和 affine。QC 检查 finite fraction、残差标准差相对于输入的变化比率。

**写了 DPABI 后端 contract。** `dpabi_nuisance_contract.py` 生成一份 JSON contract，标明 `status: CONTRACT_ONLY`、`execution_allowed: false`，记录了计划输入输出、blocked functions（DPARSF_run/DPARSFA_run）和安全状态。这是为将来实现 DPABI 单函数 wrapper 预留的接口占位，现在不执行任何 DPABI 代码。

整个 runner 把三者串起来：先找到 `swr*.nii` 和 `rp_*.txt` → 生成 confounds → 执行 Python 回归 → 输出 residual 和 QC。pipeline 现在是 6 个 SPM 节点 + 1 个 Python 回归节点，data flow 从原始 BOLD 一直走到了 nuisance-regressed 残差。
```
