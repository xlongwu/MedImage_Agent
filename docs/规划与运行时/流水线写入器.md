# Pipeline Writer

将 reviewed pipeline dict 安全写入 YAML 文件，供 Pipeline Executor 使用。

**状态**: 已实现 (M5-T013, M5-T013-fix)，已集成到 dry-run API (M5-T014 ✅)。

**代码位置**: `src/backend/app/planner/pipeline_writer.py`

## 一、安全设计

### 固定输出目录

```python
REVIEWED_PIPELINE_DIR = Path("outputs/work/reviewed_pipelines")
```

- **不可由调用方指定路径** — `output_dir` 参数已移除
- 测试通过 `monkeypatch` 注入 `tmp_path`
- 这是 M5-T013-fix 的安全收口

### 禁止目录

以下目录禁止写入：

| 禁止目录 | 原因 |
|------|------|
| `data/` / `rawdata/` | rawdata readonly |
| `outputs/derivatives/` / `derivatives/` | 衍生数据目录 |
| `outputs/reports/` / `reports/` | 报告目录 |

写入前对 `REVIEWED_PIPELINE_DIR.resolve()` 做前缀检查。

### 路径穿越防护

- `..` 出现在路径中 → `ValueError`
- filename 通过 `_sanitize_name()` 处理：
  - `..` → `__`
  - 非 `[a-zA-Z0-9_.-]` → `_`
  - 连续 `_` 压缩为单个 `_`
  - 空结果 → `"pipeline"`

## 二、核心函数

### `write_reviewed_pipeline_yaml(pipeline, *, audit_id, plan_hash) → Path`

```python
from src.backend.app.planner.pipeline_writer import write_reviewed_pipeline_yaml

path = write_reviewed_pipeline_yaml(
    pipeline_dict,
    audit_id="audit_abc123",
    plan_hash="def456...",
)
```

- **Atomic write**: 先写 `.tmp`，再 `replace()` 到目标
- **不覆盖已有文件**: 文件名已存在时追加计数器 `_1`, `_2`, ...
- **文件名格式**: `reviewed_{name}_{timestamp}_{plan_hash[:12]}.yaml`
- 依赖 PyYAML

## 三、文件名示例

```
outputs/work/reviewed_pipelines/
  reviewed_planned_motion_qc_20260529T120000_abc123def456.yaml
```

## 四、集成状态（M5-T014 ✅）

`pipeline_writer` 已集成到 `POST /api/plans/execute-reviewed` dry-run API：

- 请求字段 `write_pipeline_yaml: bool = False`
- `write_pipeline_yaml=true` 强制要求 `persist_audit=true`
- 仅在 adapter/policy 通过 + `persist_audit=true` 时写入
- 写入失败 → `PIPELINE_WRITE_FAILED`
- audit 不满足 → `PIPELINE_WRITE_REQUIRES_AUDIT`
- 所有 response 包含 `pipeline_yaml` 字段
- audit `dry_run_result` 包含 `pipeline_yaml` summary

## 五、测试

```bash
pytest tests/unit/test_pipeline_writer.py -v  # 14 tests
```

覆盖：
- YAML 写入 + roundtrip
- 特殊字符 sanitize
- 不覆盖已有文件
- atomic write（无 `.tmp` 残留）
- 路径穿越防护（`../` → sanitized）
- 无 rawdata 写入
- 输入不突变
- 测试全部通过 monkeypatch 注入 tmp_path
