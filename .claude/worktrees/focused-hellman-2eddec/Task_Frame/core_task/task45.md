# 第四十五步 Prompt：ReHo 计算 + ReHo QC + GPU/DPABI Backend Contract 闭环

```text
你是我的工程搭建助手。前四十四步已经完成：

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
- ALFF / fALFF 计算 + QC + GPU Candidate Backend 设计

现在开始第四十五步。

第四十五步目标：实现 “ReHo 计算 + ReHo QC + GPU/DPABI Backend Contract 闭环”。

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
→ Python ALFF/fALFF
→ ALFF/fALFF QC

但还缺少 rs-fMRI 局部同步性指标 ReHo。  
本步骤要继续深入 rs-fMRI 后处理，实现：

filtered residual functional image
→ voxel-wise ReHo / Kendall's coefficient of concordance
→ ReHo map
→ ReHo QC
→ subject-level ReHo report
→ dataset-level ReHo report

本步骤还要生成 GPU candidate backend contract 和 DPABI ReHo backend contract，但本步骤不要真正执行 GPU 或 DPABI。

本步骤要实现：

1. ReHo specification。
2. Python NumPy backend：
   - 输入 `filt_resid_swr*.nii`
   - 计算 voxel-wise ReHo。
   - 默认 neighborhood = 27。
   - 支持 neighborhood = 7 / 19 / 27。
   - 输出 ReHo map。
3. ReHo 计算：
   - 使用 Kendall's coefficient of concordance，KCC。
   - 对每个 voxel 取邻域 voxel 的 time series。
   - 每个 timepoint 内对邻域 voxel values 排名。
   - 根据 KCC 公式计算 ReHo。
   - 对边界 voxel 可跳过或使用有效邻居，但需要记录策略。
4. 可选 mask：
   - 如果 GM map 存在，可生成简单 mask 占位，但默认不用 mask 强制限制。
   - 本步骤不要复杂脑 mask。
5. ReHo QC：
   - input exists
   - output exists
   - input shape
   - output shape
   - timepoints
   - neighborhood
   - valid voxel count
   - finite fraction
   - ReHo mean/std/min/max
   - ReHo range sanity
   - skipped voxel count
   - reho_qc_status
6. 输出 subject-level ReHo QC JSON / Markdown。
7. 输出 dataset-level ReHo QC summary / Markdown report。
8. GPU candidate backend contract：
   - 记录未来可用 CuPy / Torch / MATLAB GPU 的 ReHo 并行化方向。
   - 本步骤只生成 contract，不执行 GPU。
   - 明确 `gpu_executed=false`。
9. DPABI ReHo backend contract：
   - 本步骤只生成 contract，不执行 DPABI。
   - 不调用 DPARSF_run / DPARSFA_run。
   - 不调用 DPABI GUI。
10. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC → Normalization → Normalization QC → Smoothing → Smoothing QC → Confound Matrix → Python Nuisance Regression → Regression QC → Temporal Filtering → Filtering QC → ReHo → ReHo QC
11. 后端 API 暴露 ReHo 结果。
12. 前端新增 rs-fMRI ReHo 面板。
13. 增加轻量 unit test。
14. 更新 README。

本步骤允许执行 Python NumPy ReHo，但必须满足：

- 只处理 synthetic BIDS-like derivative 数据。
- ReHo 输入必须来自 derivatives 中的 temporal filtering 输出。
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

- functional connectivity
- graph metrics
- group-level statistics
- 真实 DPABI ReHo 执行
- 真实 GPU 执行
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：Python NumPy ReHo、ReHo QC、GPU candidate contract、DPABI ReHo backend contract。

---

## 1. 创建 specs/reho_qc_spec.md

创建文件：

```text
specs/reho_qc_spec.md
```

内容：

```markdown
# ReHo and ReHo QC Specification

This document defines the MVP ReHo computation stage for rs-fMRI post-processing.

## Goals

The goal is to compute Regional Homogeneity (ReHo) maps from temporally filtered synthetic rs-fMRI derivatives using Kendall's coefficient of concordance, then generate lightweight QC reports.

This step prepares subject-level local synchronization maps for later reporting, visualization, and group-level analysis.

## Scope

Supported in this step:

- synthetic derivative input only
- Python NumPy ReHo backend
- neighborhood size 7 / 19 / 27
- voxel-wise Kendall's coefficient of concordance
- subject-level ReHo QC JSON / Markdown
- dataset-level ReHo QC summary / report
- GPU candidate backend contract generation without GPU execution
- DPABI ReHo backend contract generation without DPABI execution
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- GPU execution
- functional connectivity
- graph metrics
- group-level statistics
- rawdata modification
- source modification in SPM / DPABI
- file deletion

## Inputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii
derivatives/rsfmri_preproc/{subject_id}/anat/c1coreg_{subject_id}_T1w.nii
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_metrics/{subject_id}/reho.nii
derivatives/rsfmri_metrics/{subject_id}/reho_result.json
derivatives/rsfmri_qc/{subject_id}/reho_qc.json
derivatives/rsfmri_qc/{subject_id}/reho_qc.md
reports/rsfmri/reho_qc_summary.json
reports/rsfmri/reho_qc_report.md
work/gpu/contracts/reho_gpu_candidate_contract.json
work/dpabi/contracts/reho_backend_contract.json
```

## ReHo Definition for MVP

ReHo is computed using Kendall's coefficient of concordance across a voxel neighborhood.

For a center voxel:

- Collect K neighboring voxel time series.
- Rank the K voxel values at each timepoint.
- Let R_i be the sum of ranks for voxel i across all timepoints.
- Let R_bar be the mean of R_i.
- ReHo/KCC is:

```text
W = 12 * sum_i((R_i - R_bar)^2) / (T^2 * (K^3 - K))
```

where:

- K = number of voxels in neighborhood
- T = number of timepoints

## Neighborhoods

Supported neighborhoods:

- 7: center + 6 face-connected neighbors
- 19: center + face-connected + edge-connected neighbors
- 27: full 3x3x3 neighborhood

Default:

```text
neighborhood = 27
```

## Boundary Strategy

For MVP, boundary voxels are skipped unless a full neighborhood is available.

## QC Metrics

- input_exists
- reho_exists
- input_shape
- output_shape
- timepoints
- neighborhood
- valid_voxel_count
- skipped_voxel_count
- finite_fraction
- reho_mean
- reho_std
- reho_min
- reho_max
- reho_qc_status

## Safety Rules

- Only derivative filtered residual functional input is allowed.
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

## 2. 创建 backend/app/tools/reho.py

创建文件：

```text
backend/app/tools/reho.py
```

目标：实现 Python NumPy ReHo 计算和 QC。

提供函数：

```python
run_python_reho_subject(
    subject_id: str,
    derivatives_dir: str,
    neighborhood: int = 27,
    use_gm_mask: bool = False,
) -> dict

write_reho_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. input 必须是：

```text
derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii
```

2. 输出：

```text
derivatives/rsfmri_metrics/{subject_id}/reho.nii
```

3. 支持 neighborhood：
   - 7
   - 19
   - 27
4. 默认跳过边界 voxel。
5. 如果 use_gm_mask=true 且 GM map 存在，可以只在 GM > 0.2 的 voxel 计算；如果 GM map 不存在，warning 并回退到全体内部 voxel。
6. 对 synthetic 数据可直接三层 for-loop；后续再优化。
7. 输出 result JSON、QC JSON、QC Markdown。
8. 不修改 input。
9. 不处理 rawdata。

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


def _find_filtered_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists():
        return None

    preferred = func_dir / f"filt_resid_swra{subject_id}_bold.nii"
    if preferred.exists():
        return preferred

    candidates = sorted(func_dir.glob("filt_resid_swr*.nii"))
    return candidates[0] if candidates else None


def _safe_filtered_path(path: Path, subject_id: str, derivatives_dir: str) -> bool:
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

    return path.name.startswith("filt_resid_swr") and path.name.endswith(".nii")


def _find_gm_map(subject_id: str, derivatives_dir: str) -> Path | None:
    anat_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "anat"
    if not anat_dir.exists():
        return None

    preferred = anat_dir / f"c1coreg_{subject_id}_T1w.nii"
    if preferred.exists():
        return preferred

    candidates = sorted(anat_dir.glob("c1*.nii"))
    return candidates[0] if candidates else None


def _neighbor_offsets(neighborhood: int) -> list[tuple[int, int, int]]:
    offsets: list[tuple[int, int, int]] = []

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                manhattan = abs(dx) + abs(dy) + abs(dz)

                if neighborhood == 7:
                    if manhattan <= 1:
                        offsets.append((dx, dy, dz))
                elif neighborhood == 19:
                    if manhattan <= 2:
                        offsets.append((dx, dy, dz))
                elif neighborhood == 27:
                    offsets.append((dx, dy, dz))
                else:
                    raise ValueError("neighborhood must be one of 7, 19, or 27.")

    return offsets


def _rank_columns(values):
    # values shape: T x K
    import numpy as np

    ranks = np.zeros_like(values, dtype=np.float64)

    for t in range(values.shape[0]):
        row = values[t, :]
        order = np.argsort(row, kind="mergesort")
        sorted_values = row[order]
        row_ranks = np.empty_like(row, dtype=np.float64)

        start = 0
        while start < len(sorted_values):
            end = start + 1
            while end < len(sorted_values) and sorted_values[end] == sorted_values[start]:
                end += 1

            # Average rank, 1-based.
            avg_rank = (start + 1 + end) / 2.0
            row_ranks[order[start:end]] = avg_rank
            start = end

        ranks[t, :] = row_ranks

    return ranks


def _kcc(time_by_voxel):
    import numpy as np

    # time_by_voxel shape: T x K
    T, K = time_by_voxel.shape
    if T < 2 or K < 2:
        return 0.0

    ranks = _rank_columns(time_by_voxel)
    rank_sums = np.sum(ranks, axis=0)
    rank_mean = np.mean(rank_sums)

    numerator = 12.0 * np.sum((rank_sums - rank_mean) ** 2)
    denominator = (T ** 2) * (K ** 3 - K)

    if denominator == 0:
        return 0.0

    return float(numerator / denominator)


def _write_qc_markdown(path: Path, qc: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# ReHo QC: {qc.get('subject_id')}")
    lines.append("")
    lines.append(f"- OK: {qc.get('ok')}")
    lines.append(f"- Status: {qc.get('reho_qc_status')}")
    lines.append(f"- Input: `{qc.get('input_nii')}`")
    lines.append(f"- ReHo: `{qc.get('reho_file')}`")
    lines.append(f"- Neighborhood: {qc.get('neighborhood')}")
    lines.append(f"- Timepoints: {qc.get('timepoints')}")
    lines.append(f"- Valid voxel count: {qc.get('valid_voxel_count')}")
    lines.append(f"- Skipped voxel count: {qc.get('skipped_voxel_count')}")
    lines.append(f"- Finite fraction: {qc.get('finite_fraction')}")
    lines.append(f"- ReHo mean/std: {qc.get('reho_mean')} / {qc.get('reho_std')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("ReHo computation reads derivative files only and does not modify rawdata.")
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
        "node_id": "reho_qc_subject",
        "backend": "python",
        "subject_id": subject_id,
        "reho_qc_status": "FAIL",
        "outputs": [str(qc_json), str(qc_md)],
        "warnings": warnings,
        "errors": errors,
    }

    result = {
        "ok": False,
        "node_id": "python_reho_subject",
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


def run_python_reho_subject(
    subject_id: str,
    derivatives_dir: str,
    neighborhood: int = 27,
    use_gm_mask: bool = False,
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

    result_json = metrics_dir / "reho_result.json"
    qc_json = qc_dir / "reho_qc.json"
    qc_md = qc_dir / "reho_qc.md"

    warnings: list[str] = []
    errors: list[str] = []

    input_path = _find_filtered_functional(subject_id, derivatives_dir)
    if not input_path:
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"No filtered residual functional input found for subject {subject_id}."],
        )

    if not _safe_filtered_path(input_path, subject_id, derivatives_dir):
        return _failure(
            subject_id,
            result_json,
            qc_json,
            qc_md,
            [f"Unsafe filtered residual input: {input_path}"],
        )

    try:
        neighborhood = int(neighborhood)
        offsets = _neighbor_offsets(neighborhood)

        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")

        if data.ndim != 4:
            raise ValueError(f"Filtered functional input must be 4D. Shape was: {data.shape}")

        nx, ny, nz, nt = data.shape
        if nt < 2:
            raise ValueError(f"ReHo requires at least 2 timepoints. Got {nt}.")

        gm_mask = None
        gm_map_used = None

        if use_gm_mask:
            gm_path = _find_gm_map(subject_id, derivatives_dir)
            if gm_path:
                gm_img = nib.load(str(gm_path))
                gm_data = gm_img.get_fdata(dtype="float32")
                if list(gm_data.shape[:3]) == [nx, ny, nz]:
                    gm_mask = gm_data > 0.2
                    gm_map_used = str(gm_path)
                else:
                    warnings.append(
                        f"GM map shape {list(gm_data.shape)} does not match functional spatial shape {[nx, ny, nz]}; ignoring GM mask."
                    )
            else:
                warnings.append("use_gm_mask=true but GM map not found; computing ReHo on internal voxels.")

        reho_map = np.zeros((nx, ny, nz), dtype=np.float32)
        valid_voxel_count = 0
        skipped_voxel_count = 0

        for x in range(1, nx - 1):
            for y in range(1, ny - 1):
                for z in range(1, nz - 1):
                    if gm_mask is not None and not bool(gm_mask[x, y, z]):
                        skipped_voxel_count += 1
                        continue

                    series = []
                    full_neighborhood_available = True

                    for dx, dy, dz in offsets:
                        xx = x + dx
                        yy = y + dy
                        zz = z + dz

                        if xx < 0 or yy < 0 or zz < 0 or xx >= nx or yy >= ny or zz >= nz:
                            full_neighborhood_available = False
                            break

                        series.append(data[xx, yy, zz, :])

                    if not full_neighborhood_available:
                        skipped_voxel_count += 1
                        continue

                    mat = np.stack(series, axis=1)  # T x K
                    if not np.isfinite(mat).all():
                        skipped_voxel_count += 1
                        continue

                    reho_map[x, y, z] = _kcc(mat)
                    valid_voxel_count += 1

        boundary_count = nx * ny * nz - max(nx - 2, 0) * max(ny - 2, 0) * max(nz - 2, 0)
        skipped_voxel_count += int(boundary_count)

        reho_file = metrics_dir / "reho.nii"

        header_3d = img.header.copy()
        try:
            header_3d.set_data_shape(reho_map.shape)
        except Exception:
            pass

        nib.save(nib.Nifti1Image(reho_map, affine=img.affine, header=header_3d), str(reho_file))

        finite_mask = np.isfinite(reho_map)
        finite_fraction = float(np.count_nonzero(finite_mask) / reho_map.size) if reho_map.size else 0.0

        nonzero = reho_map[reho_map != 0]
        if nonzero.size > 0:
            reho_mean = float(np.mean(nonzero))
            reho_std = float(np.std(nonzero))
            reho_min = float(np.min(nonzero))
            reho_max = float(np.max(nonzero))
        else:
            reho_mean = 0.0
            reho_std = 0.0
            reho_min = 0.0
            reho_max = 0.0

        status = "PASS"
        if valid_voxel_count == 0:
            status = "FAIL"
            errors.append("No valid voxels were computed for ReHo.")
        elif finite_fraction < 0.95:
            status = "WARNING"
            warnings.append("ReHo finite fraction below 0.95.")
        elif reho_min < -1e-6 or reho_max > 1.000001:
            status = "WARNING"
            warnings.append(f"ReHo values out of expected [0, 1] range: min={reho_min}, max={reho_max}")

        qc = {
            "ok": status != "FAIL",
            "node_id": "reho_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "reho_file": str(reho_file),
            "gm_map_used": gm_map_used,
            "input_shape": list(data.shape),
            "output_shape": list(reho_map.shape),
            "timepoints": int(nt),
            "neighborhood": neighborhood,
            "neighbor_count": len(offsets),
            "boundary_strategy": "skip_boundary_full_neighborhood_required",
            "valid_voxel_count": int(valid_voxel_count),
            "skipped_voxel_count": int(skipped_voxel_count),
            "finite_fraction": finite_fraction,
            "reho_mean": reho_mean,
            "reho_std": reho_std,
            "reho_min": reho_min,
            "reho_max": reho_max,
            "reho_qc_status": status,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

        result = {
            "ok": status != "FAIL",
            "node_id": "python_reho_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "reho_file": str(reho_file),
            "qc": qc,
            "outputs": [str(reho_file), str(result_json), str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        return _failure(subject_id, result_json, qc_json, qc_md, [str(exc)], warnings)

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_markdown(qc_md, qc)
    return result


def write_reho_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/reho_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid ReHo QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("reho_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("reho_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("reho_qc_status") == "FAIL")

    reho_means = [float(item["reho_mean"]) for item in subjects if item.get("reho_mean") is not None]
    valid_counts = [float(item["valid_voxel_count"]) for item in subjects if item.get("valid_voxel_count") is not None]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "reho_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_reho_mean": float(mean(reho_means)) if reho_means else None,
        "mean_valid_voxel_count": float(mean(valid_counts)) if valid_counts else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "reho_qc_summary.json"
    report_path = report_out / "reho_qc_report.md"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# rs-fMRI ReHo QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean ReHo mean: {summary['mean_reho_mean']}")
    lines.append(f"- Mean valid voxel count: {summary['mean_valid_voxel_count']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | Neighborhood | Valid Voxels | ReHo Mean | ReHo Max |")
    lines.append("|---|---|---:|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('reho_qc_status')} | "
            f"{item.get('neighborhood')} | {item.get('valid_voxel_count')} | "
            f"{item.get('reho_mean')} | {item.get('reho_max')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative ReHo QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "reho_qc_dataset_report",
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

## 3. 创建 backend/app/tools/gpu_reho_contract.py

创建文件：

```text
backend/app/tools/gpu_reho_contract.py
```

目标：生成 GPU ReHo candidate backend contract，但不执行 GPU。

提供函数：

```python
write_reho_gpu_candidate_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/gpu/contracts/reho_gpu_candidate_contract.json
```

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_reho_gpu_candidate_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "gpu" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "reho_gpu_candidate_contract.json"

    payload = {
        "ok": True,
        "node_id": "reho_gpu_candidate_contract",
        "backend": "python",
        "backend_id": "gpu_candidate_reho",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "gpu_executed": False,
        "required_approval": True,
        "description": "GPU candidate contract for future ReHo acceleration. This step does not execute GPU code.",
        "candidate_backends": [
            {
                "name": "cupy_rank_kcc",
                "language": "python",
                "requirement": "cupy",
                "notes": "Potential CuPy implementation for neighborhood extraction and batched KCC."
            },
            {
                "name": "torch_unfold_rank",
                "language": "python",
                "requirement": "torch with CUDA",
                "notes": "Potential torch unfold/im2col-style neighborhood extraction with GPU ranking."
            },
            {
                "name": "matlab_gpuarray_reho",
                "language": "matlab",
                "requirement": "Parallel Computing Toolbox",
                "notes": "Potential MATLAB GPU backend for ReHo neighborhood KCC."
            }
        ],
        "planned_inputs": [
            "derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii"
        ],
        "planned_outputs": [
            "derivatives/rsfmri_metrics/{subject_id}/reho_gpu.nii"
        ],
        "parallelization_notes": [
            "Voxel neighborhoods are embarrassingly parallel.",
            "Rank computation per timepoint/neighborhood is the main bottleneck.",
            "Chunking over z-slices or voxel blocks is recommended for memory control."
        ],
        "safety": {
            "gpu_executed": False,
            "rawdata_modified": False,
            "files_deleted": False
        },
        "outputs": [str(path)],
        "warnings": [
            "This is a contract only. GPU execution is intentionally not implemented in Step 45."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 4. 创建 backend/app/tools/dpabi_reho_contract.py

创建文件：

```text
backend/app/tools/dpabi_reho_contract.py
```

目标：生成 DPABI ReHo backend contract，但不执行 DPABI。

提供函数：

```python
write_dpabi_reho_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/dpabi/contracts/reho_backend_contract.json
```

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_dpabi_reho_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "reho_backend_contract.json"

    payload = {
        "ok": True,
        "node_id": "dpabi_reho_contract",
        "backend": "python",
        "backend_id": "dpabi_reho",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "required_approval": True,
        "description": "DPABI ReHo backend contract. This step does not execute DPABI.",
        "planned_inputs": [
            "derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii"
        ],
        "planned_outputs": [
            "derivatives/rsfmri_metrics/{subject_id}/dpabi_reho.nii",
            "logs/{subject_id}_dpabi_reho.log"
        ],
        "parameters": {
            "neighborhood": 27,
            "mask_source": "optional_gm_or_brain_mask"
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
            "This is a contract only. DPABI ReHo execution is intentionally not implemented in Step 45."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 5. 创建 backend/app/tools/reho_runner.py

创建文件：

```text
backend/app/tools/reho_runner.py
```

目标：包装 Python ReHo、GPU contract 和 DPABI contract mode。

提供函数：

```python
run_reho_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    neighborhood: int = 27,
    use_gm_mask: bool = False,
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

from backend.app.tools.reho import run_python_reho_subject
from backend.app.tools.gpu_reho_contract import write_reho_gpu_candidate_contract
from backend.app.tools.dpabi_reho_contract import write_dpabi_reho_contract


def run_reho_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    neighborhood: int = 27,
    use_gm_mask: bool = False,
) -> dict[str, Any]:
    if backend == "gpu_contract":
        contract = write_reho_gpu_candidate_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend == "dpabi_contract":
        contract = write_dpabi_reho_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend != "python":
        return {
            "ok": False,
            "node_id": "reho_subject",
            "backend": backend,
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsupported ReHo backend: {backend}"],
        }

    result = run_python_reho_subject(
        subject_id=subject_id,
        derivatives_dir=derivatives_dir,
        neighborhood=neighborhood,
        use_gm_mask=use_gm_mask,
    )

    result["node_id"] = "reho_subject"
    return result
```

---

## 6. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
reho_subject
reho_qc_dataset_report
reho_gpu_candidate_contract
dpabi_reho_contract
```

新增导入：

```python
from backend.app.tools.reho_runner import run_reho_subject
from backend.app.tools.reho import write_reho_dataset_report
from backend.app.tools.gpu_reho_contract import write_reho_gpu_candidate_contract
from backend.app.tools.dpabi_reho_contract import write_dpabi_reho_contract
```

新增 runner：

```python
def run_reho_subject_node(
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

    result = run_reho_subject(
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        backend=node.params.get("backend", "python"),
        neighborhood=int(node.params.get("neighborhood", 27)),
        use_gm_mask=bool(node.params.get("use_gm_mask", False)),
    )

    result["node_id"] = node.id
    return result


def run_reho_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_reho_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_reho_gpu_candidate_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_reho_gpu_candidate_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_reho_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_reho_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"reho_subject": run_reho_subject_node,
"reho_qc_dataset_report": run_reho_qc_dataset_report_node,
"reho_gpu_candidate_contract": run_reho_gpu_candidate_contract_node,
"dpabi_reho_contract": run_dpabi_reho_contract_node,
```

---

## 7. 创建 examples/pipeline_rsfmri_reho.yaml

创建文件：

```text
examples/pipeline_rsfmri_reho.yaml
```

内容：

```yaml
pipeline_id: rsfmri_reho_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run Python ReHo on filtered synthetic derivatives and generate GPU/DPABI backend contracts."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_reho_001"
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

  - id: reho_subject
    name: Python ReHo
    agent: metrics-runner
    backend: python
    depends_on:
      - temporal_filtering_subject
    inputs: []
    outputs: []
    params:
      backend: python
      neighborhood: 27
      use_gm_mask: false
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: reho_gpu_candidate_contract
    name: ReHo GPU Candidate Contract
    agent: contract-runner
    backend: python
    depends_on:
      - reho_subject
    inputs: []
    outputs:
      - "./work/gpu/contracts/reho_gpu_candidate_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_reho_contract
    name: DPABI ReHo Backend Contract
    agent: contract-runner
    backend: python
    depends_on:
      - reho_subject
    inputs: []
    outputs:
      - "./work/dpabi/contracts/reho_backend_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: reho_qc_dataset_report
    name: ReHo QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - reho_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/reho_qc_summary.json"
      - "./reports/rsfmri/reho_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。  
Python ReHo 本身不需要 MATLAB approval，但它依赖前面的 SPM derivative 输出。

---

## 8. 创建 backend/app/tools/run_rsfmri_reho_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_reho_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_reho.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("work/rsfmri/approved_pipeline_reho.yaml"),
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
class RsfmriRehoRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_reho.yaml")
    approved: bool = Field(default=False)
```

---

## 10. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/reho/run
GET  /api/rsfmri/reho
```

新增导入：

```python
from backend.app.api.models import RsfmriRehoRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_reho_approved_copy(source: Path, target: Path) -> Path:
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
@router.post("/api/rsfmri/reho/run")
def api_run_rsfmri_reho(
    request: RsfmriRehoRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="ReHo pipeline requires approved=true because it depends on approved SPM preprocessing derivatives.",
        )

    try:
        approved_pipeline = _make_reho_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_reho.yaml"),
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


@router.get("/api/rsfmri/reho")
def api_get_rsfmri_reho() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")
    gpu_contract_base = Path("work") / "gpu" / "contracts"
    dpabi_contract_base = Path("work") / "dpabi" / "contracts"

    subject_reho_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/reho_qc.json")):
        subject_reho_qc.append(_read_json_if_exists(path))

    subject_results = []
    for path in sorted((derivatives_base / "rsfmri_metrics").glob("*/reho_result.json")):
        subject_results.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "reho_qc_summary": _read_json_if_exists(report_base / "reho_qc_summary.json"),
        "reho_qc_report": _read_text_if_exists(report_base / "reho_qc_report.md"),
        "subject_reho_qc": subject_reho_qc,
        "subject_reho_results": subject_results,
        "gpu_candidate_contract": _read_json_if_exists(gpu_contract_base / "reho_gpu_candidate_contract.json"),
        "dpabi_backend_contract": _read_json_if_exists(dpabi_contract_base / "reho_backend_contract.json"),
    }
```

---

## 11. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriReho(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/reho/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriReho(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/reho"
  );
}
```

---

## 12. 创建 frontend/src/components/RsfmriRehoPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriRehoPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriReho,
  runRsfmriReho
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriRehoPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 Python ReHo？这只处理 synthetic derivatives，不会修改 rawdata，不会执行 DPABI 或 GPU。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriReho(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_reho.yaml",
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
      const response = await getRsfmriReho(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.reho_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Python ReHo
        </button>
        <button onClick={handleLoad}>加载 ReHo 结果</button>
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
          <span>Mean ReHo</span>
          <strong>
            {summary?.mean_reho_mean == null
              ? "-"
              : Number(summary.mean_reho_mean).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>ReHo QC Summary</h3>
      <JsonBlock value={loaded?.reho_qc_summary} emptyText="暂无 ReHo QC summary" />

      <h3>Subject ReHo QC</h3>
      <JsonBlock value={loaded?.subject_reho_qc} emptyText="暂无 subject ReHo QC" />

      <h3>Subject ReHo Results</h3>
      <JsonBlock value={loaded?.subject_reho_results} emptyText="暂无 subject ReHo results" />

      <h3>GPU Candidate Contract</h3>
      <JsonBlock value={loaded?.gpu_candidate_contract} emptyText="暂无 GPU candidate contract" />

      <h3>DPABI Backend Contract</h3>
      <JsonBlock value={loaded?.dpabi_backend_contract} emptyText="暂无 DPABI backend contract" />

      <h3>ReHo QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.reho_qc_report === "string"
            ? loaded.reho_qc_report
            : null
        }
        emptyText="暂无 ReHo QC report"
      />
    </div>
  );
}
```

---

## 13. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriRehoPanel } from "./components/RsfmriRehoPanel";
```

在 `rs-fMRI ALFF / fALFF` 后新增 Section：

```tsx
<Section
  title="rs-fMRI ReHo"
  description="计算 ReHo/KCC 局部同步性指标图，并生成 GPU candidate 与 DPABI 后端 contract。"
>
  <RsfmriRehoPanel baseUrl={baseUrl} />
</Section>
```

---

## 14. 新增轻量测试

创建文件：

```text
tests/unit/test_reho.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.reho import run_python_reho_subject


def test_python_reho_outputs_metric_map(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    func_dir.mkdir(parents=True)

    input_nii = func_dir / "filt_resid_swrasub-001_bold.nii"

    n_time = 8
    base = np.linspace(0, 1, n_time, dtype=np.float32)

    data = np.zeros((5, 5, 5, n_time), dtype=np.float32)

    # Make a highly synchronized central region.
    for x in range(1, 4):
        for y in range(1, 4):
            for z in range(1, 4):
                data[x, y, z, :] = base

    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))

    result = run_python_reho_subject(
        subject_id=subject_id,
        derivatives_dir=str(derivatives),
        neighborhood=27,
        use_gm_mask=False,
    )

    assert result["ok"] is True

    reho = derivatives / "rsfmri_metrics" / subject_id / "reho.nii"
    assert reho.exists()

    qc_path = derivatives / "rsfmri_qc" / subject_id / "reho_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == subject_id
    assert payload["reho_qc_status"] in {"PASS", "WARNING"}
    assert payload["valid_voxel_count"] > 0
    assert 0 <= payload["reho_mean"] <= 1
```

---

## 15. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/reho")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 16. 更新 README.md

追加第四十五步说明：

```markdown
## Step 45: ReHo and ReHo QC

This step implements Python NumPy ReHo computation using Kendall's coefficient of concordance.

It supports:

- derivative filtered residual functional input
- neighborhood 7 / 19 / 27
- ReHo map output
- subject-level ReHo QC
- dataset-level ReHo QC report
- GPU candidate backend contract without GPU execution
- DPABI backend contract without DPABI execution
- frontend visualization

It does not execute DPABI or GPU code.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_reho_cli
```

This should fail safely because upstream SPM steps are not approved.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_reho_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_reho.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_metrics/sub-001/reho.nii
derivatives/rsfmri_metrics/sub-001/reho_result.json
derivatives/rsfmri_qc/sub-001/reho_qc.json
derivatives/rsfmri_qc/sub-001/reho_qc.md
reports/rsfmri/reho_qc_summary.json
reports/rsfmri/reho_qc_report.md
work/gpu/contracts/reho_gpu_candidate_contract.json
work/dpabi/contracts/reho_backend_contract.json
work/pipeline_runs/run_rsfmri_reho_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/reho
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/reho/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_reho.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI ReHo
```

### Safety

This step:

- only processes derivative filtered residual functional input
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
specs/reho_qc_spec.md
backend/app/tools/reho.py
backend/app/tools/gpu_reho_contract.py
backend/app/tools/dpabi_reho_contract.py
backend/app/tools/reho_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_reho.yaml
backend/app/tools/run_rsfmri_reho_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriRehoPanel.tsx
frontend/src/App.tsx
tests/unit/test_reho.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_reho_cli
```

应该安全失败，不应启动 SPM / DPABI / GPU。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_reho_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_reho.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_metrics/sub-001/reho.nii
derivatives/rsfmri_metrics/sub-001/reho_result.json
derivatives/rsfmri_qc/sub-001/reho_qc.json
reports/rsfmri/reho_qc_summary.json
work/gpu/contracts/reho_gpu_candidate_contract.json
work/dpabi/contracts/reho_backend_contract.json
```

ReHo QC JSON 必须包含：

```json
{
  "node_id": "reho_qc_subject",
  "subject_id": "sub-001",
  "reho_qc_status": "PASS",
  "neighborhood": 27,
  "valid_voxel_count": 0,
  "finite_fraction": 1.0,
  "reho_mean": 0
}
```

实际数值根据 synthetic 数据、shape 和 neighborhood 决定。

运行测试：

```bash
python -m pytest tests/unit/test_reho.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/reho

curl -X POST http://127.0.0.1:8000/api/rsfmri/reho/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/reho/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI ReHo 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 ReHo 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean ReHo。
8. 显示 ReHo QC summary JSON。
9. 显示 subject ReHo QC JSON。
10. 显示 subject ReHo result JSON。
11. 显示 GPU candidate contract。
12. 显示 DPABI backend contract。
13. 显示 ReHo QC Markdown report。
14. 不修改 rawdata。
15. 不运行 DPABI。
16. 不运行 GPU。
17. 不调用 DPARSF_run / DPARSFA_run。
18. 不执行完整 preprocessing。

---

## 18. 重要限制

本步骤只做 Python NumPy ReHo、ReHo QC、GPU candidate contract、DPABI ReHo backend contract。

不要实现：

- functional connectivity
- graph metrics
- group-level statistics
- 真实 DPABI ReHo 执行
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
3. ReHo / KCC 如何计算
4. neighborhood 7 / 19 / 27 如何定义
5. ReHo QC 如何计算
6. GPU candidate backend contract 为什么只生成不执行
7. DPABI ReHo backend contract 为什么只生成不执行
8. 输出哪些 derivatives、metrics 和 reports
9. 为什么本步骤仍然不是完整 preprocessing
10. 下一步如何实现 Functional Connectivity 种子/ROI 相关分析与 QC

```
这一步给 rs-fMRI 后处理加了最后一个指标——ReHo（Regional Homogeneity，局部一致性）。

**核心计算是 KCC。** `reho.py` 对 `filt_resid_swr*.nii` 逐体素取 27 邻域的时间序列，每个时间点内对邻域体素值排名，按 Kendall's coefficient of concordance 公式 `W = 12 * Σ(R_i - R̄)² / (T² * (K³ - K))` 算出 ReHo 值。边界体素邻域不全就跳过。支持 neighborhood=7/19/27 三种邻域大小，可选 GM mask 过滤。

**QC 检查有效体素数、finite fraction、ReHo 值是否在 [0,1] 范围内。** 同时生成了 GPU candidate contract（记录 CuPy/Torch/MATLAB GPU 的 KCC 并行化方向）和 DPABI ReHo contract，都不执行。
```
