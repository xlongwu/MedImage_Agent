# Phase B3：Error Intelligence 结构化错误知识库

> 目标版本：v0.2.0 | 预计工期：2–3 天 | 前置条件：Phase B1 SessionDB 完成

---

## 1. 目标与范围

将 `memory/global/ERROR_KB.yaml` 从简单字符串匹配升级为结构化分类系统，支持至少 15 种错误类别，每种包含 severity、retryable、suggested_fixes、affected_backend 等字段。

**不做**：自动修复、LLM 驱动的错误解释（那是 Phase F）。

---

## 2. 前置条件检查

- [ ] 现有 `ERROR_KB.yaml` 有 5 条记录
- [ ] Phase B1 SessionDB 可用（用于持久化分类结果）

---

## 3. 新增/修改文件清单

```text
memory/global/ERROR_KB.yaml                 # 修改：升级到 v0.2.0 schema，扩展到 15+ 类别
backend/app/tools/error_classifier.py       # 新增：结构化错误分类器
backend/app/tools/error_kb_validator.py     # 新增：ERROR_KB schema 验证器
backend/app/runtime/error_diagnoser.py      # 修改：使用新的 error_classifier
backend/app/api/routes.py                   # 修改：新增 3 个端点
tests/unit/test_error_classifier.py         # 新增：测试
```

---

## 4. 升级后的 ERROR_KB Schema

文件：`memory/global/ERROR_KB.yaml`（从 v0.1.0 升级到 v0.2.0）

```yaml
version: "0.2.0"

categories:
  matlab_missing:
    severity: critical
    retryable: false
    human_action_required: true
    patterns:
      - "matlab: command not found"
      - "No MATLAB executable"
      - "matlab not found"
      - "MATLAB is not installed"
    likely_causes:
      - "MATLAB is not installed or not on PATH"
    suggested_fixes:
      - "Install MATLAB R2020b or later"
      - "Configure matlab_command in project config"
      - "Run environment check: POST /api/environment/check"
    affected_backends:
      - matlab
      - spm
      - dpabi

  spm_path_error:
    severity: critical
    retryable: false
    human_action_required: true
    patterns:
      - "Undefined function or variable 'spm'"
      - "spm not found"
      - "SPM path missing"
      - "spm_dir not set"
    likely_causes:
      - "SPM12 directory not found at configured path"
      - "SPM not added to MATLAB path"
    suggested_fixes:
      - "Check spm_dir in project config"
      - "Verify spm12/ exists in third_party/"
      - "Run SPM smoke test: POST /api/spm/smoke-test"
    affected_backends:
      - spm

  dpabi_path_error:
    severity: critical
    retryable: false
    human_action_required: true
    patterns:
      - "Undefined function or variable 'y_"
      - "dpabi not found"
      - "DPABI path missing"
      - "DPABI_V"
    likely_causes:
      - "DPABI directory not found at configured path"
      - "DPABI not added to MATLAB path"
    suggested_fixes:
      - "Check dpabi_dir in project config"
      - "Verify DPABI_V* exists in third_party/"
      - "Run DPABI capability inspection"
    affected_backends:
      - dpabi

  nifti_io_error:
    severity: high
    retryable: true
    human_action_required: false
    patterns:
      - "nibabel"
      - "nifti"
      - "NIfTI"
      - "Cannot read NIfTI"
      - "File is not a NIfTI"
    likely_causes:
      - "Corrupted NIfTI file"
      - "Missing nibabel dependency"
      - "File permissions issue"
    suggested_fixes:
      - "pip install nibabel"
      - "Check file integrity with nibabel.load()"
      - "Regenerate synthetic data"
    affected_backends:
      - python

  numpy_dependency_error:
    severity: high
    retryable: true
    human_action_required: false
    patterns:
      - "No module named 'numpy'"
      - "numpy not found"
      - "import numpy"
    likely_causes:
      - "numpy not installed"
    suggested_fixes:
      - "pip install numpy"
    affected_backends:
      - python
      - gpu

  matlab_returncode_nonzero:
    severity: high
    retryable: true
    human_action_required: true
    patterns:
      - "return code"
      - "exit code"
      - "MATLAB exited with"
      - "non-zero exit"
    likely_causes:
      - "MATLAB script threw an error"
      - "Missing SPM/DPABI on MATLAB path"
      - "SPM batch invalid"
      - "Output directory not writable"
    suggested_fixes:
      - "Check MATLAB stdout/stderr log"
      - "Run SPM smoke test"
      - "Check output directory permissions"
    affected_backends:
      - matlab
      - spm
      - dpabi

  qc_failure:
    severity: medium
    retryable: false
    human_action_required: true
    patterns:
      - "QC_FAILURE"
      - "qc_status: FAIL"
      - "motion_qc_status: FAIL"
      - "registration_qc_status: FAIL"
    likely_causes:
      - "Subject data quality below threshold"
      - "Excessive head motion"
      - "Poor normalization"
    suggested_fixes:
      - "Review QC report for subject"
      - "Check motion plots"
      - "Consider excluding subject from analysis"
    affected_backends:
      - python

  missing_input_file:
    severity: high
    retryable: false
    human_action_required: true
    patterns:
      - "No such file"
      - "File not found"
      - "Missing input"
      - "not found"
    likely_causes:
      - "Expected derivative file does not exist"
      - "Upstream node failed silently"
      - "File naming mismatch"
    suggested_fixes:
      - "Check upstream node results"
      - "Verify file naming convention"
      - "Re-run upstream processing"
    affected_backends:
      - python
      - matlab
      - spm

  path_traversal_blocked:
    severity: high
    retryable: false
    human_action_required: false
    patterns:
      - "path traversal"
      - "path_traversal"
      - "PathRejected"
      - "unsafe path"
    likely_causes:
      - "Path contains '..' or absolute reference"
      - "Path outside allowed directories"
    suggested_fixes:
      - "Use relative paths within allowed directories"
      - "Check project config paths"
    affected_backends:
      - python

  gpu_not_available:
    severity: medium
    retryable: true
    human_action_required: false
    patterns:
      - "CUDA not available"
      - "cupy not found"
      - "No GPU"
      - "gpu not detected"
    likely_causes:
      - "No CUDA-capable GPU"
      - "CuPy not installed"
    suggested_fixes:
      - "Use CPU backend (default)"
      - "Install CuPy: pip install cupy-cuda11x"
    affected_backends:
      - gpu

  scheduler_config_error:
    severity: medium
    retryable: false
    human_action_required: true
    patterns:
      - "max_workers must be"
      - "scheduler"
      - "parallel"
      - "worker count"
    likely_causes:
      - "Invalid scheduler configuration"
    suggested_fixes:
      - "Check scheduler params in project config"
      - "max_workers valid range: 1-8"
    affected_backends:
      - python

  pipeline_schema_error:
    severity: high
    retryable: false
    human_action_required: true
    patterns:
      - "pipeline schema"
      - "validation error"
      - "missing required field"
      - "node dependency"
    likely_causes:
      - "Pipeline YAML does not conform to schema"
      - "Missing required node parameters"
    suggested_fixes:
      - "Validate pipeline YAML against schema"
      - "Check spec docs for required fields"
    affected_backends:
      - python

  disk_space_error:
    severity: critical
    retryable: false
    human_action_required: true
    patterns:
      - "No space left"
      - "disk full"
      - "Disk quota"
      - "out of space"
    likely_causes:
      - "Insufficient disk space"
    suggested_fixes:
      - "Free disk space in derivatives/ or work/"
      - "Clean old demo runs"
    affected_backends:
      - python
      - matlab

  timeout_error:
    severity: high
    retryable: true
    human_action_required: false
    patterns:
      - "timeout"
      - "timed out"
      - "took too long"
    likely_causes:
      - "MATLAB processing exceeded time limit"
      - "Network timeout"
    suggested_fixes:
      - "Increase timeout in config"
      - "Process fewer subjects per batch"
    affected_backends:
      - matlab
      - spm

  permission_denied:
    severity: critical
    retryable: false
    human_action_required: true
    patterns:
      - "Permission denied"
      - "requires confirmation"
      - "not allowed"
      - "requires approval"
    likely_causes:
      - "Tool requires approval that was not given"
      - "File write permission denied"
    suggested_fixes:
      - "Set approved=true in request"
      - "Check file permissions"
    affected_backends:
      - python
      - matlab
```

---

## 5. 新增 Error Classifier

文件：`backend/app/tools/error_classifier.py`

```python
"""Structured error classifier backed by ERROR_KB.yaml v0.2.0."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _load_error_kb(kb_path: str = "outputs/memory/global/ERROR_KB.yaml") -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required")
    path = Path(kb_path)
    if not path.exists():
        return {"version": "0.0.0", "categories": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"version": "0.0.0", "categories": {}}


def classify_error(
    message: str,
    kb_path: str = "outputs/memory/global/ERROR_KB.yaml",
) -> dict[str, Any]:
    kb = _load_error_kb(kb_path)
    categories = kb.get("categories", {})
    best_match = None
    best_score = 0

    for cat_name, cat_def in categories.items():
        patterns = cat_def.get("patterns", [])
        score = 0
        for pattern in patterns:
            if pattern.lower() in message.lower():
                score += 1
        if score > best_score:
            best_score = score
            best_match = cat_name

    if best_match and best_score > 0:
        cat = categories[best_match]
        return {
            "classified": True,
            "category": best_match,
            "severity": cat.get("severity", "unknown"),
            "retryable": cat.get("retryable", False),
            "human_action_required": cat.get("human_action_required", True),
            "likely_causes": cat.get("likely_causes", []),
            "suggested_fixes": cat.get("suggested_fixes", []),
            "affected_backends": cat.get("affected_backends", []),
            "match_score": best_score,
        }

    return {
        "classified": False,
        "category": "UNKNOWN_ERROR",
        "severity": "medium",
        "retryable": False,
        "human_action_required": True,
        "likely_causes": [],
        "suggested_fixes": ["Manual review required"],
        "affected_backends": [],
        "match_score": 0,
    }


def classify_errors_batch(
    errors: list[str],
    kb_path: str = "outputs/memory/global/ERROR_KB.yaml",
) -> list[dict[str, Any]]:
    return [classify_error(msg, kb_path) for msg in errors]


def validate_error_kb(kb_path: str = "outputs/memory/global/ERROR_KB.yaml") -> dict[str, Any]:
    kb = _load_error_kb(kb_path)
    errors: list[str] = []
    warnings: list[str] = []

    version = kb.get("version", "unknown")
    if version != "0.2.0":
        warnings.append(f"ERROR_KB version is {version}, expected 0.2.0")

    categories = kb.get("categories", {})
    if not categories:
        errors.append("No categories defined")
    else:
        required_fields = ["severity", "retryable", "patterns", "suggested_fixes"]
        for name, cat in categories.items():
            for field in required_fields:
                if field not in cat:
                    errors.append(f"Category '{name}': missing '{field}'")
            if not isinstance(cat.get("patterns"), list) or len(cat.get("patterns", [])) == 0:
                errors.append(f"Category '{name}': patterns must be non-empty list")

    return {
        "ok": len(errors) == 0,
        "version": version,
        "categories_count": len(categories),
        "errors": errors,
        "warnings": warnings,
    }
```

---

## 6. 修改 Error Diagnoser

在 `backend/app/runtime/error_diagnoser.py` 的 `_collect_issue_from_state` 函数中，替换简单的 `match_error_patterns()` 调用为：

```python
from backend.app.tools.error_classifier import classify_error

# Replace:
# matched = match_error_patterns(state.get("errors", []), memory_root)

# With:
classified = classify_error("; ".join(state.get("errors", [])))
category = classified.get("category", "UNKNOWN_ERROR")
```

---

## 7. 新增 API 端点

```python
from backend.app.tools.error_classifier import classify_error, classify_errors_batch, validate_error_kb


@router.post("/api/errors/classify")
async def errors_classify(request: dict[str, Any]):
    """Classify a single error message."""
    message = request.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    return classify_error(message)


@router.get("/api/errors/kb")
async def errors_kb():
    """Get the error knowledge base summary."""
    return validate_error_kb()


@router.post("/api/errors/kb/validate")
async def errors_kb_validate():
    """Validate the ERROR_KB schema."""
    return validate_error_kb()
```

---

## 8. 测试用例

```python
def test_classify_known_error():
    result = classify_error("matlab: command not found")
    assert result["classified"] is True
    assert result["category"] == "matlab_missing"
    assert result["retryable"] is False
    assert result["severity"] == "critical"


def test_classify_unknown_error():
    result = classify_error("something completely unexpected happened here")
    assert result["classified"] is False
    assert result["category"] == "UNKNOWN_ERROR"


def test_validate_error_kb():
    result = validate_error_kb()
    assert result["ok"] is True
    assert result["categories_count"] >= 15


def test_classify_batch():
    errors = ["matlab: command not found", "NIfTI read error"]
    results = classify_errors_batch(errors)
    assert len(results) == 2
    assert results[0]["category"] == "matlab_missing"
    assert results[1]["category"] == "nifti_io_error"
```

---

## 9. 验收标准

- [ ] ERROR_KB.yaml 升级到 v0.2.0，包含 15+ 类别
- [ ] 每个类别有 severity / retryable / patterns / suggested_fixes / affected_backends
- [ ] `classify_error()` 可正确分类已知错误模式
- [ ] 未知错误返回 UNKNOWN_ERROR 而非崩溃
- [ ] `validate_error_kb()` 验证 schema 完整性
- [ ] `error_diagnoser.py` 使用新的 classifier
- [ ] 分类结果写入 SessionDB errors 表
- [ ] API 端点可用
- [ ] 不自动执行修复（只给建议）
- [ ] 3+ 个单元测试通过
