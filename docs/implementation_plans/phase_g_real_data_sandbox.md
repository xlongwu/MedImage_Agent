# Phase G：真实数据沙盒

> 目标版本：v0.5.0 | 预计工期：2–3 周 | 前置条件：Phase C–F 完成

---

## 1. 目标与范围

为真实临床/研究数据提供**只读沙盒模式**，允许系统安全地读取 BIDS metadata、生成协议建议和风险报告，但不执行任何预处理。

**不做**：真实数据自动预处理、自动去标识化、自动上传、临床结论生成。

---

## 2. 核心原则

```
沙盒默认模式: real_data_sandbox_readonly

允许:
  ✓ 读取目录结构
  ✓ 读取 BIDS metadata (dataset_description.json, participants.tsv, *_.json)
  ✓ 读取 NIfTI header (shape, affine, TR, slice timing)
  ✓ 生成 data inventory
  ✓ 生成 protocol recommendation
  ✓ 生成 risk report

禁止:
  ✗ 写入 rawdata
  ✗ 修改 NIfTI 数据
  ✗ 运行 preprocessing
  ✗ 自动去标识化
  ✗ 自动上传
  ✗ 生成临床结论
```

---

## 3. 新增/修改文件清单

```text
backend/app/runtime/real_data_sandbox.py     # 新增：沙盒核心（只读）
backend/app/tools/real_data_inspector.py     # 新增：真实数据只读检查
backend/app/tools/real_data_risk_reporter.py # 新增：风险报告生成
backend/app/tools/real_data_protocol_advisor.py # 新增：协议建议
backend/app/runtime/path_safety.py           # 修改：新增 rawdata 白名单路径
backend/app/api/routes.py                    # 修改：新增沙盒端点
tests/unit/test_real_data_sandbox.py         # 新增：测试
.env.example                                 # 修改：沙盒配置项
```

---

## 4. 安全配置

```bash
# .env
MEDIMAGE_REAL_DATA_MODE=readonly_sandbox    # readonly_sandbox | disabled
MEDIMAGE_RAW_DATA_PATH=/data/bids/rawdata   # BIDS root (只读)
MEDIMAGE_ALLOW_RAWDATA_WRITE=false           # 强制 false
MEDIMAGE_REAL_DATA_SUBJECT_WHITELIST=        # 空白 = 全部 subject
```

---

## 5. 沙盒只读检查功能

### 5.1 Data Inventory

读取 BIDS 元数据生成：

```json
{
  "dataset_root": "/data/bids/rawdata",
  "total_subjects": 120,
  "subject_summary": {
    "sub-001": {
      "t1w": "/data/bids/rawdata/sub-001/anat/sub-001_T1w.nii.gz",
      "bold": "/data/bids/rawdata/sub-001/func/sub-001_task-rest_bold.nii.gz",
      "tr": 2.0,
      "slices": 32,
      "slice_timing": "interleaved",
      "phase_encoding": "j"
    }
  },
  "data_completeness": {
    "has_t1w": 120,
    "has_bold": 120,
    "has_fieldmap": 0,
    "has_participants_tsv": true
  },
  "naming_issues": [],
  "metadata_warnings": []
}
```

### 5.2 Risk Report

基于 metadata 生成风险报告：

```text
检查项:
  - 缺失关键数据（T1w / BOLD）
  - TR 不一致（不同 subject TR 不同）
  - 切片数不一致
  - 缺少 fieldmap
  - BIDS 命名不规范
  - 文件大小异常（可能是截断数据）
  - participants.tsv 是否匹配 subject 目录
```

### 5.3 Protocol Recommendation

基于 data inventory 生成协议建议（不执行）：

```json
{
  "recommended_pipeline": "rsfmri_spm_standard_v1",
  "suggested_params": {
    "slice_timing_reference": "middle_slice",
    "realign_quality": 0.9,
    "normalize_voxel_size": [3, 3, 3],
    "smooth_fwhm": [6, 6, 6]
  },
  "risks": [
    "No fieldmap available; distortion correction skipped",
    "TR varies across subjects (1.5-2.5s); check temporal filtering band"
  ],
  "requires_manual_review": true
}
```

---

## 6. 沙盒 -> 真实执行 的审批流程

真实数据执行必须单独设计审批流程（Phase G 不实现执行，只设计审批 schema）：

```yaml
real_data_execution_request:
  request_id: "req_001"
  operator_name: "Dr. Smith"
  operator_affiliation: "Neuroimaging Lab"
  timestamp: "2026-06-15T10:00:00Z"
  pipeline_id: "rsfmri_spm_standard_v1"
  subject_whitelist: ["sub-001", "sub-002"]
  output_dir: "/data/derivatives/medimage_v0.5"
  execution_approved: false  # 必须改为 true
  approved_by: ""            # 审批人
  approved_at: ""            # 审批时间
  audit_log_path: ""
  safety_checks:
    rawdata_readonly: true
    derivatives_isolated: true
    no_auto_delete: true
    phi_scan_required: true
```

---

## 7. API 端点

```text
POST /api/real-data/inventory         → 生成 data inventory
GET  /api/real-data/inventory/latest  → 查看最新 inventory
POST /api/real-data/risk-report       → 生成风险报告
GET  /api/real-data/risk-report/latest → 查看最新风险报告
POST /api/real-data/protocol-recommend → 生成协议建议
GET  /api/sandbox/status              → 沙盒模式状态
```

---

## 8. 验收标准

- [ ] 沙盒模式默认只读
- [ ] 可读取真实 BIDS 目录结构
- [ ] 可读取 NIfTI header（不读取 voxel data）
- [ ] 可生成 data inventory JSON
- [ ] 可生成 risk report markdown
- [ ] 可生成 protocol recommendation
- [ ] 任何写操作被拦截（path_safety 白名单 + MEDIMAGE_ALLOW_RAWDATA_WRITE=false）
- [ ] 不运行任何 preprocessing
- [ ] 不生成临床结论
- [ ] 不自动上传
- [ ] 所有输出在 reports/ / work/ 中
- [ ] 不访问 PHI（subject_id 级别即可，不读取 DICOM patient 字段）

---

## 9. 风险与注意事项

- **PHI 风险**：真实 DICOM 可能包含 patient name、birth date 等字段。沙盒模式只读 NIfTI header metadata，不读 DICOM patient 字段
- **数据量大**：120+ subject 的 BIDS 目录扫描可能需较长时间。建议 inventory 生成异步化
- **安全边界**：path_safety 在沙盒模式下必须严格限制写入路径
- **法律合规**：真实数据使用需遵守机构 IRB 和数据使用协议。沙盒工具不替代合规审查
