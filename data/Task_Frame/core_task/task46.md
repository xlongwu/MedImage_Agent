# 第四十六步 Prompt：Functional Connectivity ROI/Seed 相关分析 + FC QC + GPU/DPABI Backend Contract 闭环

```text
你是我的工程搭建助手。前四十五步已经完成：

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
- ReHo 计算 + ReHo QC + GPU/DPABI Backend Contract

现在开始第四十六步。

第四十六步目标：实现 “Functional Connectivity ROI/Seed 相关分析 + FC QC + GPU/DPABI Backend Contract 闭环”。

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
→ Python ReHo
→ ReHo QC

但还缺少 rs-fMRI 连接分析中的核心步骤：功能连接 Functional Connectivity。  
本步骤要实现最小闭环的 ROI/seed-based FC：

filtered residual functional image
+ ROI/seed definitions
→ ROI time series extraction
→ ROI-to-ROI correlation matrix
→ Fisher-z matrix
→ optional seed-to-voxel correlation map
→ FC QC
→ subject-level FC report
→ dataset-level FC report

本步骤还要生成 GPU candidate backend contract 和 DPABI FC backend contract，但本步骤不要真正执行 GPU 或 DPABI。

本步骤要实现：

1. Functional Connectivity specification。
2. Synthetic ROI atlas / seed definition 生成器：
   - 默认生成 4 个 synthetic ROI。
   - ROI atlas 必须写入 derivatives 或 work。
   - atlas shape 必须与 filtered functional spatial shape 一致。
   - 不依赖真实脑 atlas。
3. Python NumPy backend：
   - 输入 `filt_resid_swr*.nii`
   - 输入 ROI atlas NIfTI 或 seed coordinate JSON
   - 提取 ROI mean time series
   - 计算 Pearson correlation matrix
   - 计算 Fisher-z matrix
   - 输出 ROI timeseries TSV
   - 输出 correlation matrix TSV/JSON
   - 输出 Fisher-z matrix TSV/JSON
4. Optional seed-to-voxel map：
   - 默认关闭。
   - 如果开启，只处理第一个 ROI/seed。
   - 输出 seed correlation map 和 Fisher-z map。
5. FC QC：
   - input exists
   - atlas exists
   - ROI count
   - timepoints
   - ROI voxel counts
   - empty ROI count
   - timeseries finite fraction
   - correlation matrix shape
   - diagonal sanity
   - correlation finite fraction
   - Fisher-z finite fraction
   - matrix symmetry check
   - fc_qc_status
6. 输出 subject-level FC QC JSON / Markdown。
7. 输出 dataset-level FC QC summary / Markdown report。
8. GPU candidate backend contract：
   - 记录未来可用 CuPy / Torch / MATLAB GPU 的 correlation matrix 并行化方向。
   - 本步骤只生成 contract，不执行 GPU。
   - 明确 `gpu_executed=false`。
9. DPABI FC backend contract：
   - 本步骤只生成 contract，不执行 DPABI。
   - 不调用 DPARSF_run / DPARSFA_run。
   - 不调用 DPABI GUI。
10. 新增 chained pipeline：
    Slice Timing → Realignment → Motion QC → Coregistration → Registration QC → Segmentation → Tissue QC → Normalization → Normalization QC → Smoothing → Smoothing QC → Confound Matrix → Python Nuisance Regression → Regression QC → Temporal Filtering → Filtering QC → Functional Connectivity → FC QC
11. 后端 API 暴露 FC 结果。
12. 前端新增 rs-fMRI Functional Connectivity 面板。
13. 增加轻量 unit test。
14. 更新 README。

本步骤允许执行 Python NumPy FC，但必须满足：

- 只处理 synthetic BIDS-like derivative 数据。
- FC 输入必须来自 derivatives 中的 temporal filtering 输出。
- ROI atlas 必须是 synthetic/generated atlas 或用户显式提供的 derivatives/work 内 atlas。
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

- group-level statistics
- graph theory metrics
- dynamic FC
- ICA
- 真实 DPABI FC 执行
- 真实 GPU 执行
- 完整 preprocessing pipeline
- 真实数据处理
- 自动参数优化
- Docker / release / CI 等外围功能

本步骤只做：Python NumPy ROI/seed FC、FC QC、GPU candidate contract、DPABI FC backend contract。

---

## 1. 创建 specs/functional_connectivity_qc_spec.md

创建文件：

```text
specs/functional_connectivity_qc_spec.md
```

内容：

```markdown
# Functional Connectivity and FC QC Specification

This document defines the MVP functional connectivity stage for rs-fMRI post-processing.

## Goals

The goal is to compute ROI/seed-based functional connectivity from temporally filtered synthetic rs-fMRI derivatives and generate lightweight QC reports.

This step prepares subject-level connectivity matrices and optional seed maps for reporting and later group-level analysis.

## Scope

Supported in this step:

- synthetic derivative input only
- generated synthetic ROI atlas
- ROI mean time series extraction
- ROI-to-ROI Pearson correlation matrix
- Fisher-z transformed matrix
- optional single-seed seed-to-voxel map
- subject-level FC QC JSON / Markdown
- dataset-level FC QC summary / report
- GPU candidate backend contract generation without GPU execution
- DPABI FC backend contract generation without DPABI execution
- API and frontend visibility
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- GPU execution
- group-level statistics
- graph theory metrics
- dynamic FC
- ICA
- rawdata modification
- source modification in SPM / DPABI
- file deletion

## Inputs

```text
derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii
derivatives/rsfmri_fc/{subject_id}/synthetic_roi_atlas.nii
work/dataset_index/dataset_index.json
```

## Outputs

```text
derivatives/rsfmri_fc/{subject_id}/synthetic_roi_atlas.nii
derivatives/rsfmri_fc/{subject_id}/roi_definitions.json
derivatives/rsfmri_fc/{subject_id}/roi_timeseries.tsv
derivatives/rsfmri_fc/{subject_id}/correlation_matrix.tsv
derivatives/rsfmri_fc/{subject_id}/correlation_matrix.json
derivatives/rsfmri_fc/{subject_id}/fisher_z_matrix.tsv
derivatives/rsfmri_fc/{subject_id}/fisher_z_matrix.json
derivatives/rsfmri_fc/{subject_id}/fc_result.json
derivatives/rsfmri_fc/{subject_id}/seed_correlation_map.nii
derivatives/rsfmri_fc/{subject_id}/seed_fisher_z_map.nii
derivatives/rsfmri_qc/{subject_id}/functional_connectivity_qc.json
derivatives/rsfmri_qc/{subject_id}/functional_connectivity_qc.md
reports/rsfmri/functional_connectivity_qc_summary.json
reports/rsfmri/functional_connectivity_qc_report.md
work/gpu/contracts/functional_connectivity_gpu_candidate_contract.json
work/dpabi/contracts/functional_connectivity_backend_contract.json
```

## MVP ROI Strategy

The default atlas is generated from the synthetic functional image shape.

Default:

- 4 non-overlapping cuboid ROIs
- labels: 1, 2, 3, 4
- ROI names: ROI_1, ROI_2, ROI_3, ROI_4

The atlas is not a real anatomical atlas and is only used for engineering validation.

## FC Definition for MVP

For each ROI:

- Extract voxel time series within ROI.
- Average across voxels to obtain ROI mean time series.
- Compute Pearson correlation across ROI time series.
- Apply Fisher-z transform:

```text
z = arctanh(r)
```

with clipping to avoid infinities.

## Seed-to-Voxel Mode

Optional and disabled by default.

When enabled:

- Use the first ROI time series as seed.
- Compute voxel-wise correlation.
- Output seed correlation and Fisher-z maps.

## QC Metrics

- input_exists
- atlas_exists
- input_shape
- atlas_shape
- timepoints
- roi_count
- roi_voxel_counts
- empty_roi_count
- timeseries_finite_fraction
- correlation_matrix_shape
- correlation_finite_fraction
- fisher_z_finite_fraction
- diagonal_mean
- symmetry_max_abs_diff
- seed_map_generated
- fc_qc_status

## Safety Rules

- Only derivative filtered residual functional input is allowed.
- Only generated synthetic atlas or derivatives/work atlas input is allowed.
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

## 2. 创建 backend/app/tools/functional_connectivity.py

创建文件：

```text
backend/app/tools/functional_connectivity.py
```

目标：实现 Python NumPy ROI/seed FC 计算和 QC。

提供函数：

```python
run_python_functional_connectivity_subject(
    subject_id: str,
    derivatives_dir: str,
    roi_count: int = 4,
    atlas_path: str | None = None,
    generate_seed_map: bool = False,
) -> dict

write_functional_connectivity_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict
```

实现要求：

1. input 必须是：

```text
derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii
```

2. 默认自动生成 synthetic ROI atlas：

```text
derivatives/rsfmri_fc/{subject_id}/synthetic_roi_atlas.nii
derivatives/rsfmri_fc/{subject_id}/roi_definitions.json
```

3. 如果 atlas_path 提供：
   - 必须存在。
   - 必须位于 derivatives 或 work 下。
   - shape 必须匹配 functional spatial shape。
4. ROI time series：
   - 对每个 ROI label > 0 计算 mean time series。
   - 空 ROI 允许，但要 warning，并输出全零 time series。
5. correlation matrix：
   - 使用 np.corrcoef。
   - 对 std=0 的 ROI 做安全处理，避免 NaN。
6. Fisher-z：
   - 对 r clip 到 [-0.999999, 0.999999] 后 arctanh。
   - diagonal 可设为 0 或保留 arctanh clipped value；本步骤建议 diagonal 设为 0，方便 QC。
7. seed-to-voxel：
   - generate_seed_map=false 默认不生成。
   - 如果 true，使用第一个非空 ROI time series。
   - 输出 correlation map / fisher-z map。
8. 输出 result JSON、QC JSON、QC Markdown。
9. 不修改 input。
10. 不处理 rawdata。

参考实现：

```python
from __future__ import annotations

import csv
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


def _safe_atlas_path(path: Path, derivatives_dir: str) -> bool:
    resolved = path.resolve()
    allowed_roots = [
        Path(derivatives_dir).resolve(),
        Path("work").resolve(),
    ]

    for root in allowed_roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue

    return False


def _write_tsv(path: Path, header: list[str], rows: list[list[float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows)


def _generate_synthetic_atlas(shape: tuple[int, int, int], roi_count: int):
    import numpy as np

    if roi_count < 1:
        raise ValueError("roi_count must be >= 1.")

    nx, ny, nz = shape
    atlas = np.zeros(shape, dtype=np.int16)

    # Split along x dimension into roi_count chunks.
    edges = np.linspace(0, nx, roi_count + 1).astype(int)

    roi_definitions = []
    for idx in range(roi_count):
        start = int(edges[idx])
        end = int(edges[idx + 1])

        if end <= start:
            continue

        label = idx + 1
        atlas[start:end, :, :] = label

        roi_definitions.append({
            "label": label,
            "name": f"ROI_{label}",
            "strategy": "synthetic_x_axis_chunk",
            "x_start": start,
            "x_end": end,
        })

    return atlas, roi_definitions


def _safe_corrcoef(timeseries):
    import numpy as np

    ts = np.asarray(timeseries, dtype=np.float64)
    n_roi = ts.shape[0]

    corr = np.eye(n_roi, dtype=np.float64)

    for i in range(n_roi):
        for j in range(i + 1, n_roi):
            a = ts[i]
            b = ts[j]

            a_std = float(np.std(a))
            b_std = float(np.std(b))

            if a_std == 0 or b_std == 0:
                value = 0.0
            else:
                value = float(np.corrcoef(a, b)[0, 1])
                if not np.isfinite(value):
                    value = 0.0

            corr[i, j] = value
            corr[j, i] = value

    return corr


def _fisher_z(corr):
    import numpy as np

    clipped = np.clip(corr, -0.999999, 0.999999)
    z = np.arctanh(clipped)
    np.fill_diagonal(z, 0.0)
    return z


def _seed_to_voxel_maps(data, seed_ts):
    import numpy as np

    nx, ny, nz, nt = data.shape
    flat = data.reshape((-1, nt)).astype(np.float64)

    seed = np.asarray(seed_ts, dtype=np.float64)
    seed_std = float(np.std(seed))

    corr = np.zeros(flat.shape[0], dtype=np.float32)

    if seed_std == 0:
        return corr.reshape((nx, ny, nz)), corr.reshape((nx, ny, nz))

    seed_centered = seed - np.mean(seed)

    for idx in range(flat.shape[0]):
        voxel = flat[idx]
        voxel_std = float(np.std(voxel))

        if voxel_std == 0:
            corr[idx] = 0.0
            continue

        voxel_centered = voxel - np.mean(voxel)
        denom = float((nt - 1) * seed_std * voxel_std)

        if denom == 0:
            corr[idx] = 0.0
        else:
            value = float(np.sum(seed_centered * voxel_centered) / denom)
            corr[idx] = value if np.isfinite(value) else 0.0

    corr_map = corr.reshape((nx, ny, nz))
    z_map = np.arctanh(np.clip(corr_map, -0.999999, 0.999999)).astype(np.float32)
    return corr_map.astype(np.float32), z_map


def _write_qc_markdown(path: Path, qc: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# Functional Connectivity QC: {qc.get('subject_id')}")
    lines.append("")
    lines.append(f"- OK: {qc.get('ok')}")
    lines.append(f"- Status: {qc.get('fc_qc_status')}")
    lines.append(f"- Input: `{qc.get('input_nii')}`")
    lines.append(f"- Atlas: `{qc.get('atlas_file')}`")
    lines.append(f"- ROI count: {qc.get('roi_count')}")
    lines.append(f"- Timepoints: {qc.get('timepoints')}")
    lines.append(f"- Empty ROI count: {qc.get('empty_roi_count')}")
    lines.append(f"- Timeseries finite fraction: {qc.get('timeseries_finite_fraction')}")
    lines.append(f"- Correlation finite fraction: {qc.get('correlation_finite_fraction')}")
    lines.append(f"- Symmetry max abs diff: {qc.get('symmetry_max_abs_diff')}")
    lines.append(f"- Seed map generated: {qc.get('seed_map_generated')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Functional connectivity computation reads derivative files only and does not modify rawdata.")
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
        "node_id": "functional_connectivity_qc_subject",
        "backend": "python",
        "subject_id": subject_id,
        "fc_qc_status": "FAIL",
        "outputs": [str(qc_json), str(qc_md)],
        "warnings": warnings,
        "errors": errors,
    }

    result = {
        "ok": False,
        "node_id": "python_functional_connectivity_subject",
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


def run_python_functional_connectivity_subject(
    subject_id: str,
    derivatives_dir: str,
    roi_count: int = 4,
    atlas_path: str | None = None,
    generate_seed_map: bool = False,
) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    fc_dir = Path(derivatives_dir) / "rsfmri_fc" / subject_id
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    fc_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    result_json = fc_dir / "fc_result.json"
    qc_json = qc_dir / "functional_connectivity_qc.json"
    qc_md = qc_dir / "functional_connectivity_qc.md"

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
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")

        if data.ndim != 4:
            raise ValueError(f"Filtered functional input must be 4D. Shape was: {data.shape}")

        nx, ny, nz, nt = data.shape

        roi_definitions = []
        if atlas_path:
            atlas_file = Path(atlas_path)
            if not atlas_file.exists():
                raise ValueError(f"Atlas not found: {atlas_file}")
            if not _safe_atlas_path(atlas_file, derivatives_dir):
                raise ValueError(f"Unsafe atlas path. Atlas must be under derivatives or work: {atlas_file}")

            atlas_img = nib.load(str(atlas_file))
            atlas_data = atlas_img.get_fdata().astype("int16")

            if list(atlas_data.shape[:3]) != [nx, ny, nz]:
                raise ValueError(
                    f"Atlas spatial shape {list(atlas_data.shape[:3])} does not match functional shape {[nx, ny, nz]}."
                )

            labels = sorted(int(x) for x in np.unique(atlas_data) if int(x) > 0)
            roi_definitions = [{"label": label, "name": f"ROI_{label}", "strategy": "provided_atlas"} for label in labels]
        else:
            atlas_data, roi_definitions = _generate_synthetic_atlas((nx, ny, nz), int(roi_count))
            atlas_file = fc_dir / "synthetic_roi_atlas.nii"

            atlas_header = img.header.copy()
            try:
                atlas_header.set_data_shape(atlas_data.shape)
            except Exception:
                pass

            nib.save(nib.Nifti1Image(atlas_data.astype("int16"), affine=img.affine, header=atlas_header), str(atlas_file))

        roi_definitions_path = fc_dir / "roi_definitions.json"
        roi_definitions_path.write_text(
            json.dumps(
                {
                    "subject_id": subject_id,
                    "atlas_file": str(atlas_file),
                    "roi_definitions": roi_definitions,
                    "synthetic": atlas_path is None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        labels = [int(item["label"]) for item in roi_definitions]
        names = [str(item.get("name", f"ROI_{label}")) for item, label in zip(roi_definitions, labels)]

        roi_timeseries = []
        roi_voxel_counts: dict[str, int] = {}
        empty_roi_count = 0

        for label in labels:
            mask = atlas_data == label
            voxel_count = int(np.count_nonzero(mask))
            roi_voxel_counts[str(label)] = voxel_count

            if voxel_count == 0:
                empty_roi_count += 1
                warnings.append(f"ROI {label} is empty.")
                ts = np.zeros((nt,), dtype=np.float64)
            else:
                ts = np.mean(data[mask, :], axis=0).astype(np.float64)

            if not np.isfinite(ts).all():
                warnings.append(f"ROI {label} time series contains non-finite values; replacing with zeros.")
                ts = np.where(np.isfinite(ts), ts, 0.0)

            roi_timeseries.append(ts)

        roi_ts_arr = np.vstack(roi_timeseries) if roi_timeseries else np.zeros((0, nt), dtype=np.float64)

        timeseries_tsv = fc_dir / "roi_timeseries.tsv"
        ts_rows = [[float(roi_ts_arr[roi_idx, t]) for roi_idx in range(len(labels))] for t in range(nt)]
        _write_tsv(timeseries_tsv, names, ts_rows)

        corr = _safe_corrcoef(roi_ts_arr)
        fisher_z = _fisher_z(corr)

        correlation_tsv = fc_dir / "correlation_matrix.tsv"
        fisher_z_tsv = fc_dir / "fisher_z_matrix.tsv"
        correlation_json = fc_dir / "correlation_matrix.json"
        fisher_z_json = fc_dir / "fisher_z_matrix.json"

        _write_tsv(correlation_tsv, ["roi"] + names, [[names[i]] + [float(x) for x in corr[i]] for i in range(len(names))])
        _write_tsv(fisher_z_tsv, ["roi"] + names, [[names[i]] + [float(x) for x in fisher_z[i]] for i in range(len(names))])

        correlation_json.write_text(
            json.dumps(
                {
                    "subject_id": subject_id,
                    "roi_names": names,
                    "matrix": corr.tolist(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        fisher_z_json.write_text(
            json.dumps(
                {
                    "subject_id": subject_id,
                    "roi_names": names,
                    "matrix": fisher_z.tolist(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        seed_corr_file = None
        seed_z_file = None
        seed_map_generated = False

        if generate_seed_map and len(labels) > 0:
            non_empty_indices = [
                idx for idx, label in enumerate(labels)
                if roi_voxel_counts.get(str(label), 0) > 0
            ]
            if non_empty_indices:
                seed_index = non_empty_indices[0]
                corr_map, z_map = _seed_to_voxel_maps(data, roi_ts_arr[seed_index])
                seed_corr_file = fc_dir / "seed_correlation_map.nii"
                seed_z_file = fc_dir / "seed_fisher_z_map.nii"

                map_header = img.header.copy()
                try:
                    map_header.set_data_shape(corr_map.shape)
                except Exception:
                    pass

                nib.save(nib.Nifti1Image(corr_map, affine=img.affine, header=map_header), str(seed_corr_file))
                nib.save(nib.Nifti1Image(z_map, affine=img.affine, header=map_header), str(seed_z_file))
                seed_map_generated = True
            else:
                warnings.append("Seed map requested but no non-empty ROI was available.")

        timeseries_finite_fraction = (
            float(np.count_nonzero(np.isfinite(roi_ts_arr)) / roi_ts_arr.size)
            if roi_ts_arr.size
            else 0.0
        )
        correlation_finite_fraction = (
            float(np.count_nonzero(np.isfinite(corr)) / corr.size)
            if corr.size
            else 0.0
        )
        fisher_z_finite_fraction = (
            float(np.count_nonzero(np.isfinite(fisher_z)) / fisher_z.size)
            if fisher_z.size
            else 0.0
        )

        diagonal_mean = float(np.mean(np.diag(corr))) if corr.size else None
        symmetry_max_abs_diff = float(np.max(np.abs(corr - corr.T))) if corr.size else None

        status = "PASS"

        if len(labels) == 0:
            status = "FAIL"
            errors.append("No ROI labels found.")
        elif empty_roi_count > 0:
            status = "WARNING"
            warnings.append(f"{empty_roi_count} empty ROI(s) found.")
        elif timeseries_finite_fraction < 1.0 or correlation_finite_fraction < 1.0 or fisher_z_finite_fraction < 1.0:
            status = "WARNING"
            warnings.append("Non-finite values detected in time series or FC matrices.")
        elif diagonal_mean is not None and abs(diagonal_mean - 1.0) > 1e-5:
            status = "WARNING"
            warnings.append(f"Correlation diagonal mean expected near 1.0 but got {diagonal_mean}.")
        elif symmetry_max_abs_diff is not None and symmetry_max_abs_diff > 1e-6:
            status = "WARNING"
            warnings.append(f"Correlation matrix symmetry difference is high: {symmetry_max_abs_diff}.")

        qc = {
            "ok": status != "FAIL",
            "node_id": "functional_connectivity_qc_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "atlas_file": str(atlas_file),
            "input_shape": list(data.shape),
            "atlas_shape": list(atlas_data.shape),
            "timepoints": int(nt),
            "roi_count": len(labels),
            "roi_names": names,
            "roi_voxel_counts": roi_voxel_counts,
            "empty_roi_count": int(empty_roi_count),
            "timeseries_finite_fraction": timeseries_finite_fraction,
            "correlation_matrix_shape": list(corr.shape),
            "correlation_finite_fraction": correlation_finite_fraction,
            "fisher_z_finite_fraction": fisher_z_finite_fraction,
            "diagonal_mean": diagonal_mean,
            "symmetry_max_abs_diff": symmetry_max_abs_diff,
            "seed_map_generated": seed_map_generated,
            "fc_qc_status": status,
            "outputs": [str(qc_json), str(qc_md)],
            "warnings": warnings,
            "errors": errors,
        }

        outputs = [
            str(atlas_file),
            str(roi_definitions_path),
            str(timeseries_tsv),
            str(correlation_tsv),
            str(correlation_json),
            str(fisher_z_tsv),
            str(fisher_z_json),
            str(result_json),
            str(qc_json),
            str(qc_md),
        ]

        if seed_corr_file:
            outputs.append(str(seed_corr_file))
        if seed_z_file:
            outputs.append(str(seed_z_file))

        result = {
            "ok": status != "FAIL",
            "node_id": "python_functional_connectivity_subject",
            "backend": "python",
            "subject_id": subject_id,
            "input_nii": str(input_path),
            "atlas_file": str(atlas_file),
            "roi_definitions": roi_definitions,
            "roi_timeseries_tsv": str(timeseries_tsv),
            "correlation_matrix_tsv": str(correlation_tsv),
            "correlation_matrix_json": str(correlation_json),
            "fisher_z_matrix_tsv": str(fisher_z_tsv),
            "fisher_z_matrix_json": str(fisher_z_json),
            "seed_correlation_map": str(seed_corr_file) if seed_corr_file else None,
            "seed_fisher_z_map": str(seed_z_file) if seed_z_file else None,
            "qc": qc,
            "outputs": outputs,
            "warnings": warnings,
            "errors": errors,
        }

    except Exception as exc:
        return _failure(subject_id, result_json, qc_json, qc_md, [str(exc)], warnings)

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_markdown(qc_md, qc)
    return result


def write_functional_connectivity_dataset_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/functional_connectivity_qc.json"))

    subjects = []
    warnings: list[str] = []
    errors: list[str] = []

    for path in qc_paths:
        payload = _read_json(path)
        if not payload:
            warnings.append(f"Invalid FC QC JSON: {path}")
            continue
        subjects.append(payload)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item.get("fc_qc_status") == "PASS")
    warning_count = sum(1 for item in subjects if item.get("fc_qc_status") == "WARNING")
    fail_count = sum(1 for item in subjects if item.get("fc_qc_status") == "FAIL")

    roi_counts = [float(item["roi_count"]) for item in subjects if item.get("roi_count") is not None]
    empty_counts = [float(item["empty_roi_count"]) for item in subjects if item.get("empty_roi_count") is not None]

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "functional_connectivity_qc_dataset_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "mean_roi_count": float(mean(roi_counts)) if roi_counts else None,
        "mean_empty_roi_count": float(mean(empty_counts)) if empty_counts else None,
        "subjects": subjects,
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "functional_connectivity_qc_summary.json"
    report_path = report_out / "functional_connectivity_qc_report.md"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# rs-fMRI Functional Connectivity QC Dataset Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- Mean ROI count: {summary['mean_roi_count']}")
    lines.append(f"- Mean empty ROI count: {summary['mean_empty_roi_count']}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Status | ROI Count | Empty ROIs | Timepoints | Symmetry Max Diff |")
    lines.append("|---|---|---:|---:|---:|---:|")

    for item in subjects:
        lines.append(
            f"| {item.get('subject_id')} | {item.get('fc_qc_status')} | "
            f"{item.get('roi_count')} | {item.get('empty_roi_count')} | "
            f"{item.get('timepoints')} | {item.get('symmetry_max_abs_diff')} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report summarizes derivative functional connectivity QC outputs only. It does not modify rawdata.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "functional_connectivity_qc_dataset_report",
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

## 3. 创建 backend/app/tools/gpu_fc_contract.py

创建文件：

```text
backend/app/tools/gpu_fc_contract.py
```

目标：生成 GPU FC candidate backend contract，但不执行 GPU。

提供函数：

```python
write_functional_connectivity_gpu_candidate_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/gpu/contracts/functional_connectivity_gpu_candidate_contract.json
```

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_functional_connectivity_gpu_candidate_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "gpu" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "functional_connectivity_gpu_candidate_contract.json"

    payload = {
        "ok": True,
        "node_id": "functional_connectivity_gpu_candidate_contract",
        "backend": "python",
        "backend_id": "gpu_candidate_functional_connectivity",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "gpu_executed": False,
        "required_approval": True,
        "description": "GPU candidate contract for future functional connectivity acceleration. This step does not execute GPU code.",
        "candidate_backends": [
            {
                "name": "cupy_corrcoef",
                "language": "python",
                "requirement": "cupy",
                "notes": "Potential GPU implementation for ROI/voxel correlation matrices."
            },
            {
                "name": "torch_matmul_corr",
                "language": "python",
                "requirement": "torch with CUDA",
                "notes": "Z-scored time series can be correlated using matrix multiplication."
            },
            {
                "name": "matlab_gpuarray_corr",
                "language": "matlab",
                "requirement": "Parallel Computing Toolbox",
                "notes": "Potential MATLAB GPU backend for seed-to-voxel correlation."
            }
        ],
        "planned_inputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii",
            "outputs/derivatives/rsfmri_fc/{subject_id}/synthetic_roi_atlas.nii"
        ],
        "planned_outputs": [
            "outputs/derivatives/rsfmri_fc/{subject_id}/gpu_correlation_matrix.tsv",
            "outputs/derivatives/rsfmri_fc/{subject_id}/gpu_seed_correlation_map.nii"
        ],
        "parallelization_notes": [
            "ROI-to-ROI FC is matrix multiplication after z-scoring.",
            "Seed-to-voxel correlation is embarrassingly parallel over voxels.",
            "Chunking over voxels is recommended for memory control."
        ],
        "safety": {
            "gpu_executed": False,
            "rawdata_modified": False,
            "files_deleted": False
        },
        "outputs": [str(path)],
        "warnings": [
            "This is a contract only. GPU execution is intentionally not implemented in Step 46."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 4. 创建 backend/app/tools/dpabi_fc_contract.py

创建文件：

```text
backend/app/tools/dpabi_fc_contract.py
```

目标：生成 DPABI FC backend contract，但不执行 DPABI。

提供函数：

```python
write_dpabi_functional_connectivity_contract(
    work_dir: str = "./work",
) -> dict
```

输出：

```text
work/dpabi/contracts/functional_connectivity_backend_contract.json
```

参考实现：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_dpabi_functional_connectivity_contract(
    work_dir: str = "./work",
) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "functional_connectivity_backend_contract.json"

    payload = {
        "ok": True,
        "node_id": "dpabi_functional_connectivity_contract",
        "backend": "python",
        "backend_id": "dpabi_functional_connectivity",
        "status": "CONTRACT_ONLY",
        "execution_allowed": False,
        "required_approval": True,
        "description": "DPABI functional connectivity backend contract. This step does not execute DPABI.",
        "planned_inputs": [
            "outputs/derivatives/rsfmri_preproc/{subject_id}/func/filt_resid_swr*.nii",
            "outputs/derivatives/rsfmri_fc/{subject_id}/synthetic_roi_atlas.nii"
        ],
        "planned_outputs": [
            "outputs/derivatives/rsfmri_fc/{subject_id}/dpabi_correlation_matrix.tsv",
            "outputs/logs/{subject_id}_dpabi_functional_connectivity.log"
        ],
        "parameters": {
            "mode": "roi_to_roi_and_seed_to_voxel",
            "fisher_z": True
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
            "This is a contract only. DPABI functional connectivity execution is intentionally not implemented in Step 46."
        ],
        "errors": [],
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
```

---

## 5. 创建 backend/app/tools/functional_connectivity_runner.py

创建文件：

```text
backend/app/tools/functional_connectivity_runner.py
```

目标：包装 Python FC、GPU contract 和 DPABI contract mode。

提供函数：

```python
run_functional_connectivity_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    roi_count: int = 4,
    atlas_path: str | None = None,
    generate_seed_map: bool = False,
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

from backend.app.tools.functional_connectivity import run_python_functional_connectivity_subject
from backend.app.tools.gpu_fc_contract import write_functional_connectivity_gpu_candidate_contract
from backend.app.tools.dpabi_fc_contract import write_dpabi_functional_connectivity_contract


def run_functional_connectivity_subject(
    subject_id: str,
    derivatives_dir: str,
    backend: str = "python",
    roi_count: int = 4,
    atlas_path: str | None = None,
    generate_seed_map: bool = False,
) -> dict[str, Any]:
    if backend == "gpu_contract":
        contract = write_functional_connectivity_gpu_candidate_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend == "dpabi_contract":
        contract = write_dpabi_functional_connectivity_contract(work_dir="./work")
        contract["subject_id"] = subject_id
        return contract

    if backend != "python":
        return {
            "ok": False,
            "node_id": "functional_connectivity_subject",
            "backend": backend,
            "subject_id": subject_id,
            "outputs": [],
            "warnings": [],
            "errors": [f"Unsupported functional connectivity backend: {backend}"],
        }

    result = run_python_functional_connectivity_subject(
        subject_id=subject_id,
        derivatives_dir=derivatives_dir,
        roi_count=roi_count,
        atlas_path=atlas_path,
        generate_seed_map=generate_seed_map,
    )

    result["node_id"] = "functional_connectivity_subject"
    return result
```

---

## 6. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
functional_connectivity_subject
functional_connectivity_qc_dataset_report
functional_connectivity_gpu_candidate_contract
dpabi_functional_connectivity_contract
```

新增导入：

```python
from backend.app.tools.functional_connectivity_runner import run_functional_connectivity_subject
from backend.app.tools.functional_connectivity import write_functional_connectivity_dataset_report
from backend.app.tools.gpu_fc_contract import write_functional_connectivity_gpu_candidate_contract
from backend.app.tools.dpabi_fc_contract import write_dpabi_functional_connectivity_contract
```

新增 runner：

```python
def run_functional_connectivity_subject_node(
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

    result = run_functional_connectivity_subject(
        subject_id=context.subject_id,
        derivatives_dir=context.derivatives_dir,
        backend=node.params.get("backend", "python"),
        roi_count=int(node.params.get("roi_count", 4)),
        atlas_path=node.params.get("atlas_path"),
        generate_seed_map=bool(node.params.get("generate_seed_map", False)),
    )

    result["node_id"] = node.id
    return result


def run_functional_connectivity_qc_dataset_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_functional_connectivity_dataset_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result


def run_functional_connectivity_gpu_candidate_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_functional_connectivity_gpu_candidate_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_functional_connectivity_contract_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_functional_connectivity_contract(
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"functional_connectivity_subject": run_functional_connectivity_subject_node,
"functional_connectivity_qc_dataset_report": run_functional_connectivity_qc_dataset_report_node,
"functional_connectivity_gpu_candidate_contract": run_functional_connectivity_gpu_candidate_contract_node,
"dpabi_functional_connectivity_contract": run_dpabi_functional_connectivity_contract_node,
```

---

## 7. 创建 examples/pipeline_rsfmri_functional_connectivity.yaml

创建文件：

```text
examples/pipeline_rsfmri_functional_connectivity.yaml
```

内容：

```yaml
pipeline_id: rsfmri_functional_connectivity_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run Python ROI/seed functional connectivity on filtered synthetic derivatives and generate GPU/DPABI backend contracts."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_functional_connectivity_001"
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

  - id: functional_connectivity_subject
    name: Python Functional Connectivity
    agent: metrics-runner
    backend: python
    depends_on:
      - temporal_filtering_subject
    inputs: []
    outputs: []
    params:
      backend: python
      roi_count: 4
      atlas_path: null
      generate_seed_map: false
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: functional_connectivity_gpu_candidate_contract
    name: Functional Connectivity GPU Candidate Contract
    agent: contract-runner
    backend: python
    depends_on:
      - functional_connectivity_subject
    inputs: []
    outputs:
      - "./work/gpu/contracts/functional_connectivity_gpu_candidate_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_functional_connectivity_contract
    name: DPABI Functional Connectivity Backend Contract
    agent: contract-runner
    backend: python
    depends_on:
      - functional_connectivity_subject
    inputs: []
    outputs:
      - "./work/dpabi/contracts/functional_connectivity_backend_contract.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: functional_connectivity_qc_dataset_report
    name: Functional Connectivity QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - functional_connectivity_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/functional_connectivity_qc_summary.json"
      - "./reports/rsfmri/functional_connectivity_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
```

默认所有 SPM 节点 `approved: false`。  
真正执行必须由 CLI/API 显式设为 `approved: true`。  
Python FC 本身不需要 MATLAB approval，但它依赖前面的 SPM derivative 输出。

---

## 8. 创建 backend/app/tools/run_rsfmri_functional_connectivity_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_functional_connectivity_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_functional_connectivity.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("outputs/work/rsfmri/approved_pipeline_functional_connectivity.yaml"),
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
class RsfmriFunctionalConnectivityRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_functional_connectivity.yaml")
    approved: bool = Field(default=False)
```

---

## 10. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/functional-connectivity/run
GET  /api/rsfmri/functional-connectivity
```

新增导入：

```python
from backend.app.api.models import RsfmriFunctionalConnectivityRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增辅助函数：

```python
def _make_functional_connectivity_approved_copy(source: Path, target: Path) -> Path:
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
@router.post("/api/rsfmri/functional-connectivity/run")
def api_run_rsfmri_functional_connectivity(
    request: RsfmriFunctionalConnectivityRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="Functional connectivity pipeline requires approved=true because it depends on approved SPM preprocessing derivatives.",
        )

    try:
        approved_pipeline = _make_functional_connectivity_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("outputs/work/rsfmri/approved_pipeline_functional_connectivity.yaml"),
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


@router.get("/api/rsfmri/functional-connectivity")
def api_get_rsfmri_functional_connectivity() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")
    gpu_contract_base = Path("work") / "gpu" / "contracts"
    dpabi_contract_base = Path("work") / "dpabi" / "contracts"

    subject_fc_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/functional_connectivity_qc.json")):
        subject_fc_qc.append(_read_json_if_exists(path))

    subject_results = []
    for path in sorted((derivatives_base / "rsfmri_fc").glob("*/fc_result.json")):
        subject_results.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "functional_connectivity_qc_summary": _read_json_if_exists(report_base / "functional_connectivity_qc_summary.json"),
        "functional_connectivity_qc_report": _read_text_if_exists(report_base / "functional_connectivity_qc_report.md"),
        "subject_functional_connectivity_qc": subject_fc_qc,
        "subject_functional_connectivity_results": subject_results,
        "gpu_candidate_contract": _read_json_if_exists(gpu_contract_base / "functional_connectivity_gpu_candidate_contract.json"),
        "dpabi_backend_contract": _read_json_if_exists(dpabi_contract_base / "functional_connectivity_backend_contract.json"),
    }
```

---

## 11. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriFunctionalConnectivity(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/functional-connectivity/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriFunctionalConnectivity(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/functional-connectivity"
  );
}
```

---

## 12. 创建 frontend/src/components/RsfmriFunctionalConnectivityPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriFunctionalConnectivityPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriFunctionalConnectivity,
  runRsfmriFunctionalConnectivity
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriFunctionalConnectivityPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 Python Functional Connectivity？这只处理 synthetic derivatives，不会修改 rawdata，不会执行 DPABI 或 GPU。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriFunctionalConnectivity(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_functional_connectivity.yaml",
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
      const response = await getRsfmriFunctionalConnectivity(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.functional_connectivity_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 Python Functional Connectivity
        </button>
        <button onClick={handleLoad}>加载 FC 结果</button>
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
          <span>Mean ROI Count</span>
          <strong>
            {summary?.mean_roi_count == null
              ? "-"
              : Number(summary.mean_roi_count).toFixed(2)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Functional Connectivity QC Summary</h3>
      <JsonBlock value={loaded?.functional_connectivity_qc_summary} emptyText="暂无 FC QC summary" />

      <h3>Subject Functional Connectivity QC</h3>
      <JsonBlock value={loaded?.subject_functional_connectivity_qc} emptyText="暂无 subject FC QC" />

      <h3>Subject Functional Connectivity Results</h3>
      <JsonBlock value={loaded?.subject_functional_connectivity_results} emptyText="暂无 subject FC results" />

      <h3>GPU Candidate Contract</h3>
      <JsonBlock value={loaded?.gpu_candidate_contract} emptyText="暂无 GPU candidate contract" />

      <h3>DPABI Backend Contract</h3>
      <JsonBlock value={loaded?.dpabi_backend_contract} emptyText="暂无 DPABI backend contract" />

      <h3>Functional Connectivity QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.functional_connectivity_qc_report === "string"
            ? loaded.functional_connectivity_qc_report
            : null
        }
        emptyText="暂无 FC QC report"
      />
    </div>
  );
}
```

---

## 13. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriFunctionalConnectivityPanel } from "./components/RsfmriFunctionalConnectivityPanel";
```

在 `rs-fMRI ReHo` 后新增 Section：

```tsx
<Section
  title="rs-fMRI Functional Connectivity"
  description="提取 synthetic ROI time series，计算 ROI-to-ROI correlation / Fisher-z matrix，并生成 GPU candidate 与 DPABI 后端 contract。"
>
  <RsfmriFunctionalConnectivityPanel baseUrl={baseUrl} />
</Section>
```

---

## 14. 新增轻量测试

创建文件：

```text
tests/unit/test_functional_connectivity.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from backend.app.tools.functional_connectivity import run_python_functional_connectivity_subject


def test_python_functional_connectivity_outputs_matrices(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    func_dir.mkdir(parents=True)

    input_nii = func_dir / "filt_resid_swrasub-001_bold.nii"

    n_time = 12
    t = np.linspace(0, 2 * np.pi, n_time, dtype=np.float32)

    data = np.zeros((4, 4, 4, n_time), dtype=np.float32)

    # Make x-axis chunks have different but finite signals.
    data[0:1, :, :, :] = np.sin(t)
    data[1:2, :, :, :] = np.sin(t)
    data[2:3, :, :, :] = np.cos(t)
    data[3:4, :, :, :] = -np.sin(t)

    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(input_nii))

    result = run_python_functional_connectivity_subject(
        subject_id=subject_id,
        derivatives_dir=str(derivatives),
        roi_count=4,
        generate_seed_map=True,
    )

    assert result["ok"] is True

    fc_dir = derivatives / "rsfmri_fc" / subject_id
    assert (fc_dir / "roi_timeseries.tsv").exists()
    assert (fc_dir / "correlation_matrix.tsv").exists()
    assert (fc_dir / "fisher_z_matrix.tsv").exists()
    assert (fc_dir / "seed_correlation_map.nii").exists()

    qc_path = derivatives / "rsfmri_qc" / subject_id / "functional_connectivity_qc.json"
    assert qc_path.exists()

    payload = json.loads(qc_path.read_text(encoding="utf-8"))
    assert payload["subject_id"] == subject_id
    assert payload["fc_qc_status"] in {"PASS", "WARNING"}
    assert payload["roi_count"] == 4
    assert payload["correlation_matrix_shape"] == [4, 4]
```

---

## 15. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/functional-connectivity")
```

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

---

## 16. 更新 README.md

追加第四十六步说明：

```markdown
## Step 46: Functional Connectivity and FC QC

This step implements Python NumPy ROI/seed functional connectivity.

It supports:

- derivative filtered residual functional input
- generated synthetic ROI atlas
- ROI mean time series extraction
- ROI-to-ROI Pearson correlation matrix
- Fisher-z transformed matrix
- optional single-seed seed-to-voxel map
- subject-level FC QC
- dataset-level FC QC report
- GPU candidate backend contract without GPU execution
- DPABI backend contract without DPABI execution
- frontend visualization

It does not execute DPABI or GPU code.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_functional_connectivity_cli
```

This should fail safely because upstream SPM steps are not approved.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_functional_connectivity_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_functional_connectivity.yaml --approve
```

Expected outputs:

```text
derivatives/rsfmri_fc/sub-001/synthetic_roi_atlas.nii
derivatives/rsfmri_fc/sub-001/roi_definitions.json
derivatives/rsfmri_fc/sub-001/roi_timeseries.tsv
derivatives/rsfmri_fc/sub-001/correlation_matrix.tsv
derivatives/rsfmri_fc/sub-001/correlation_matrix.json
derivatives/rsfmri_fc/sub-001/fisher_z_matrix.tsv
derivatives/rsfmri_fc/sub-001/fisher_z_matrix.json
derivatives/rsfmri_fc/sub-001/fc_result.json
derivatives/rsfmri_qc/sub-001/functional_connectivity_qc.json
derivatives/rsfmri_qc/sub-001/functional_connectivity_qc.md
reports/rsfmri/functional_connectivity_qc_summary.json
reports/rsfmri/functional_connectivity_qc_report.md
work/gpu/contracts/functional_connectivity_gpu_candidate_contract.json
work/dpabi/contracts/functional_connectivity_backend_contract.json
work/pipeline_runs/run_rsfmri_functional_connectivity_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/functional-connectivity
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/functional-connectivity/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_functional_connectivity.yaml",
    "approved": true
  }'
```

### Frontend

Use:

```text
rs-fMRI Functional Connectivity
```

### Safety

This step:

- only processes derivative filtered residual functional input
- uses generated synthetic ROI atlas by default
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
specs/functional_connectivity_qc_spec.md
backend/app/tools/functional_connectivity.py
backend/app/tools/gpu_fc_contract.py
backend/app/tools/dpabi_fc_contract.py
backend/app/tools/functional_connectivity_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_functional_connectivity.yaml
backend/app/tools/run_rsfmri_functional_connectivity_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriFunctionalConnectivityPanel.tsx
frontend/src/App.tsx
tests/unit/test_functional_connectivity.py
backend/app/tools/api_smoke_test.py
README.md
```

先运行不带 approval：

```bash
python -m backend.app.tools.run_rsfmri_functional_connectivity_cli
```

应该安全失败，不应启动 SPM / DPABI / GPU。

然后运行 approved：

```bash
python -m backend.app.tools.run_rsfmri_functional_connectivity_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_functional_connectivity.yaml --approve
```

如果本地 MATLAB + SPM 可用，应生成：

```text
derivatives/rsfmri_fc/sub-001/roi_timeseries.tsv
derivatives/rsfmri_fc/sub-001/correlation_matrix.tsv
derivatives/rsfmri_fc/sub-001/fisher_z_matrix.tsv
derivatives/rsfmri_qc/sub-001/functional_connectivity_qc.json
reports/rsfmri/functional_connectivity_qc_summary.json
work/gpu/contracts/functional_connectivity_gpu_candidate_contract.json
work/dpabi/contracts/functional_connectivity_backend_contract.json
```

FC QC JSON 必须包含：

```json
{
  "node_id": "functional_connectivity_qc_subject",
  "subject_id": "sub-001",
  "fc_qc_status": "PASS",
  "roi_count": 4,
  "timepoints": 0,
  "empty_roi_count": 0,
  "correlation_matrix_shape": [4, 4],
  "diagonal_mean": 1.0
}
```

实际数值根据 synthetic 数据、shape 和 ROI atlas 决定。

运行测试：

```bash
python -m pytest tests/unit/test_functional_connectivity.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/functional-connectivity

curl -X POST http://127.0.0.1:8000/api/rsfmri/functional-connectivity/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

未批准 POST 必须返回 403。

批准 POST 可运行：

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/functional-connectivity/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI Functional Connectivity 区域。
2. 可以点击批准并运行。
3. 点击运行前有 confirm 弹窗。
4. 可以加载 FC 结果。
5. 显示 subject 数量。
6. 显示 PASS / WARNING / FAIL 数量。
7. 显示 mean ROI count。
8. 显示 FC QC summary JSON。
9. 显示 subject FC QC JSON。
10. 显示 subject FC result JSON。
11. 显示 GPU candidate contract。
12. 显示 DPABI backend contract。
13. 显示 FC QC Markdown report。
14. 不修改 rawdata。
15. 不运行 DPABI。
16. 不运行 GPU。
17. 不调用 DPARSF_run / DPARSFA_run。
18. 不执行完整 preprocessing。

---

## 18. 重要限制

本步骤只做 Python NumPy ROI/seed Functional Connectivity、FC QC、GPU candidate contract、DPABI FC backend contract。

不要实现：

- group-level statistics
- graph theory metrics
- dynamic FC
- ICA
- 真实 DPABI FC 执行
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
3. synthetic ROI atlas 如何生成
4. ROI time series 如何提取
5. correlation matrix 和 Fisher-z matrix 如何计算
6. seed-to-voxel map 如何可选生成
7. FC QC 如何计算
8. GPU candidate backend contract 为什么只生成不执行
9. DPABI FC backend contract 为什么只生成不执行
10. 输出哪些 derivatives、FC matrices 和 reports
11. 为什么本步骤仍然不是完整 preprocessing
12. 下一步如何实现 Group-level Dataset Summary + Cross-subject Metrics Dashboard

```
这一步给 rs-fMRI 后处理加了功能连接分析。

**自动生成 synthetic ROI atlas。** `functional_connectivity.py` 根据功能像的空间尺寸沿 x 轴均匀切成 4 个矩形 ROI，写入 `derivatives/rsfmri_fc/{subject}/synthetic_roi_atlas.nii`。不需要真实脑图谱。

**提取 ROI 时间序列并算矩阵。** 对每个 ROI 内所有体素的时间序列求均值得到 ROI mean time series，输出 TSV。算 ROI 两两之间的 Pearson 相关系数矩阵，再做 Fisher-z 变换（对角线置零、clip 到 ±0.999999 防无穷大），输出 TSV 和 JSON 两种格式。

**可选 seed-to-voxel map。** 默认关闭。开启后拿第一个非空 ROI 的时间序列当种子，和全脑每个体素算相关系数，输出 seed correlation map 和 fisher-z map 两张 NIfTI。

**QC 检查。** 对角线均值是否接近 1、矩阵是否对称、有无空 ROI、finite fraction。

同时生成了 GPU contract 和 DPABI contract，都不执行。Pipeline 现在 20 个节点，从原始 BOLD 一路到功能连接矩阵，预处理链完整闭环。
```
