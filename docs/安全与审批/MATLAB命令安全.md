# MATLAB Command Safety Guard

> M6-T002a | matlab_safety.py — pure-function safety validators

**代码位置**: `src/backend/app/safety/matlab_safety.py`

## 一、职责

提供纯函数安全校验，用于 MATLAB/SPM/DPABI runner 调用前的最后一层防御。
不调用 MATLAB，不写文件，无副作用。

## 二、核心函数

### `validate_matlab_command(command) → MatlabSafetyResult`

验证 `matlab_command` 字符串安全性。

**允许**:
- `matlab`
- `matlab.exe`
- `/usr/local/bin/matlab` (warning if nonexistent)

**拒绝**:
- 空字符串 → `MATLAB_COMMAND_EMPTY`
- 包含 shell metacharacters (`; & | \` $ > < \n \r`) → `MATLAB_COMMAND_FORBIDDEN_CHAR`
- 含空格 (参数) → `MATLAB_COMMAND_HAS_ARGUMENTS`
- 非 `matlab`/`matlab.exe` basename → `MATLAB_COMMAND_INVALID_BASENAME`
- 路径含 `..` → `MATLAB_COMMAND_PATH_TRAVERSAL`
- 路径指向 rawdata/derivatives/reports/work → `MATLAB_COMMAND_FORBIDDEN_LOCATION`

### `validate_third_party_dir(path, *, name) → MatlabSafetyResult`

验证 `spm_dir` / `dpabi_dir` 路径安全性。

**拒绝**:
- 空路径 → `THIRD_PARTY_DIR_EMPTY`
- 包含 `..` → `THIRD_PARTY_DIR_PATH_TRAVERSAL`
- 指向 rawdata/derivatives/reports/work → `THIRD_PARTY_DIR_FORBIDDEN_LOCATION`
- 是文件 → `THIRD_PARTY_DIR_IS_FILE`

**Warning**:
- 不存在 → `THIRD_PARTY_DIR_NOT_FOUND` (warning, not error)

### `validate_matlab_runtime_config(*, matlab_command, spm_dir, dpabi_dir) → MatlabSafetyResult`

合并三个校验为单个结果。

## 三、数据结构

```python
@dataclass(frozen=True)
class MatlabSafetyIssue:
    code: str        # e.g. "MATLAB_COMMAND_EMPTY"
    message: str     # human-readable
    severity: str    # "error" | "warning"
    field: str|None  # which config field

@dataclass(frozen=True)
class MatlabSafetyResult:
    ok: bool
    errors: list[MatlabSafetyIssue]
    warnings: list[MatlabSafetyIssue]

    def to_dict(self) -> dict
```

## 四、错误码

| Code | Severity |
|------|:---:|
| `MATLAB_COMMAND_EMPTY` | error |
| `MATLAB_COMMAND_FORBIDDEN_CHAR` | error |
| `MATLAB_COMMAND_HAS_ARGUMENTS` | error |
| `MATLAB_COMMAND_INVALID_BASENAME` | error |
| `MATLAB_COMMAND_PATH_TRAVERSAL` | error |
| `MATLAB_COMMAND_FORBIDDEN_LOCATION` | error |
| `MATLAB_COMMAND_NOT_FOUND` | warning |
| `THIRD_PARTY_DIR_EMPTY` | error |
| `THIRD_PARTY_DIR_PATH_TRAVERSAL` | error |
| `THIRD_PARTY_DIR_FORBIDDEN_LOCATION` | error |
| `THIRD_PARTY_DIR_IS_FILE` | error |
| `THIRD_PARTY_DIR_NOT_FOUND` | warning |

## 五、测试

```bash
pytest tests/unit/test_matlab_safety.py -v  # 29 tests
```
