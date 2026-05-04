# Phase D：DPABI Wrapper 原型

> 目标版本：v0.3.0-beta | 预计工期：2–3 周 | 前置条件：Phase C SPM 单节点验证通过

---

## 1. 目标与范围

从 DPABI 单函数 sandbox 验证入手，实现安全的 DPABI wrapper 原型。**不接 DPARSF 全流程**。

**不做**：DPARSF_run、DPARSFA_run、DPABI GUI 调用、DPABI Surf/Fiber/Net 模块。

---

## 2. 核心原则

```
默认: contract_only（只生成 MATLAB script，不执行）
逐步开放: dry_run → synthetic_execute → approved_execute
禁止: DPARSF_run / DPARSFA_run（代码层面拦截）
```

---

## 3. 新增/修改文件清单

```text
backend/app/tools/dpabi_wrapper.py              # 新增：核心 DPABI 单函数 wrapper
backend/app/tools/dpabi_smoke_test.py           # 修改：增强 smoke test
backend/app/tools/dpabi_single_function_runner.py # 修改：支持 4 种执行模式
backend/app/tools/dpabi_safety.py               # 新增：DPABI 安全拦截
backend/app/api/routes.py                       # 修改：新增 DPABI 端点
examples/pipeline_dpabi_single_func.yaml        # 新增：pipeline YAML
tests/unit/test_dpabi_safety.py                 # 新增：安全测试
```

---

## 4. 优先实现的 DPABI 函数

按顺序：

```text
1. y_Smooth           → 空间平滑（最简单，风险最低）
2. y_Filter           → 时域滤波
3. y_RegressOutImgCovariates → Nuisance regression
4. y_alff_falff       → ALFF/fALFF
5. y_Reho             → ReHo
6. y_ROItseries       → ROI signal extraction
7. y_FC               → FC matrix
```

### 执行模式矩阵

| 模式 | 生成 MATLAB script | 真实执行 | approved | 输入限制 |
|------|-------------------|---------|----------|---------|
| `contract_only` | ✅ | ❌ | 不需要 | — |
| `dry_run` | ✅ | ❌ | 不需要 | — |
| `synthetic_execute` | ✅ | ✅ | 必须 true | synthetic only |
| `approved_execute` | ✅ | ✅ | 必须 true | whitelist |

默认模式：`contract_only`

---

## 5. DPABI 安全拦截

文件：`backend/app/tools/dpabi_safety.py`

```python
"""DPABI safety gate — prevent dangerous DPABI/DPARSF calls."""

FORBIDDEN_FUNCTIONS = {
    "DPARSF_run",
    "DPARSFA_run",
    "DPABI_run",
    "dpabi_gui",
}

FORBIDDEN_PATTERNS = [
    "DPARSF",
    "DPARSFA",
]

def check_dpabi_call(function_name: str) -> tuple[bool, str | None]:
    """Returns (allowed, rejection_reason)."""
    if function_name in FORBIDDEN_FUNCTIONS:
        return False, f"FORBIDDEN: {function_name} is blocked by safety policy"
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in function_name.lower():
            return False, f"FORBIDDEN: {function_name} matches blocked pattern '{pattern}'"
    return True, None
```

---

## 6. 每个 DPABI 调用的交付物

```text
work/dpabi/{function_name}_{subject_id}/
  ├── matlab_script.m
  ├── input_manifest.json
  ├── output_manifest.json
  ├── matlab_stdout.log
  ├── matlab_stderr.log
  ├── dpabi_result.json
  └── dpabi_qc.json
```

---

## 7. DPABI Wrapper 核心方法签名

```python
def run_dpabi_single_function(
    function_name: str,          # e.g. "y_Smooth"
    input_bold: str,             # path to input BOLD NIfTI
    subject_id: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    dpabi_dir: str,
    matlab_command: str,
    mode: str = "contract_only", # contract_only | dry_run | synthetic_execute | approved_execute
    approved: bool = False,
    params: dict | None = None,  # function-specific params (fwhm, band, etc.)
) -> dict[str, Any]:
```

---

## 8. API 端点

```text
POST /api/dpabi/smoke-test              → DPABI 环境 smoke test
POST /api/dpabi/run-single-function     → 执行单个 DPABI 函数
GET  /api/dpabi/results/{run_id}        → 查看 DPABI 执行结果
GET  /api/dpabi/function-list           → 列出可用 DPABI 函数
```

---

## 9. 验收标准

- [ ] 默认 `contract_only` 模式不执行任何 MATLAB 代码
- [ ] `dry_run` 只生成 `.m` 文件，不执行
- [ ] `synthetic_execute` 需要 `approved=true` 才执行
- [ ] `DPARSF_run` 和 `DPARSFA_run` 被代码层面拦截
- [ ] `y_Smooth` 单函数可真实运行并产出正确输出
- [ ] `y_Filter` 单函数可真实运行
- [ ] 每个调用生成 input_manifest + output_manifest + MATLAB script + log
- [ ] 所有输出在 derivatives/ / work/ / logs/ / reports/ 中
- [ ] 安全测试覆盖禁止函数拦截
