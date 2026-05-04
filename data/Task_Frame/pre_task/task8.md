你是我的工程搭建助手。前七步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。

现在开始第八步。

第八步目标：实现“最小长期记忆 + 后台复盘 + 错误知识库闭环”。

这一步借鉴 Hermes Agent 的记忆和后台复盘思想，但仍然不接真实 LLM。  
现在只实现 deterministic memory/runtime review，用结构化规则从 pipeline run 中提炼经验。

本步骤要实现：

- memory/ 目录结构
- MEMORY.md / USER.md / ENVIRONMENT.md
- project-level LESSONS.md
- ERROR_KB.yaml
- run history JSONL
- deterministic background review
- 从 agent_summary / pipeline summary / dataset_summary / state files 中提取复盘信息
- 生成 review_summary.md
- 生成 proposed_memory_patch.md
- 将 background review 接入 agent_execute 之后，可选自动运行
- 不自动覆盖重要记忆内容，只追加安全的 run history 和 review 文件
- 不接真实 LLM
- 不做 UI
- 不做多 Agent 智能协作
- 不做 GPU
- 不做并行调度
- 不修改 SPM / DPABI 源码

本步骤只做最小记忆和复盘闭环。

---

## 1. 创建 specs/memory_runtime_spec.md

创建文件：

```text
specs/memory_runtime_spec.md

内容：

# Memory Runtime Specification

This document defines the MVP memory and background review system for MedImage Agent.

## Goals

The memory system should help the agent preserve useful knowledge across runs:

- environment configuration
- project-level lessons
- known errors and fixes
- run history
- dataset evaluation outcomes
- pipeline reliability observations

## Memory Layers

### Global Prompt Memory

Files:

```text
memory/global/MEMORY.md
memory/global/USER.md
memory/global/ENVIRONMENT.md
memory/global/ERROR_KB.yaml

Purpose:

Store high-level stable context.
Keep concise.
Do not store raw imaging data.
Do not store PHI.
Project Memory

Files:

memory/projects/{project_name}/PROJECT.md
memory/projects/{project_name}/LESSONS.md
memory/projects/{project_name}/RUN_HISTORY.jsonl

Purpose:

Store project-specific decisions, run summaries, and lessons.
Run Review

Files:

work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md

Purpose:

Summarize what happened in the run.
Propose memory updates.
Do not automatically rewrite stable memory without review.
What to Store

Allowed:

pipeline ID and version
run ID
software paths
success/failure status
QC metrics summary
dataset quality score
known error patterns
non-sensitive subject IDs
recommendations such as INCLUDE / MANUAL_REVIEW / EXCLUDE counts

Forbidden:

patient names
hospital IDs
raw DICOM headers
raw NIfTI content
PHI
clinical diagnosis
disease conclusions
Background Review Inputs

The MVP background reviewer reads:

work/agent_runs/{agent_run_id}/agent_summary.json
work/pipeline_runs/{run_id}/summary.json
reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/exclusion_recommendations.csv
work/states/{run_id}/...
Background Review Outputs
work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
memory/projects/{project_name}/RUN_HISTORY.jsonl
Safety Rules
Do not modify rawdata.
Do not delete files.
Do not store PHI.
Do not make clinical conclusions.
Proposed memory patches require human review before merging.
RUN_HISTORY.jsonl can be appended automatically.

---

## 2. 创建 memory 初始目录和文件

请创建：

```text id="8xqnwi"
memory/
├── global/
│   ├── MEMORY.md
│   ├── USER.md
│   ├── ENVIRONMENT.md
│   └── ERROR_KB.yaml
├── projects/
└── sessions/
memory/global/MEMORY.md

内容：

# MedImage Agent Memory

This file stores concise global memory for MedImage Agent.

## System Role

MedImage Agent is a visual and agent-based medical imaging preprocessing framework.

It supports:

- BIDS-like dataset inspection
- MATLAB / SPM / DPABI environment checks
- synthetic subject-level preprocessing tests
- QC metric aggregation
- dataset-level evaluation reports
- deterministic Agent Runtime with Plan Mode and Execute Mode

## Safety Rules

- Do not modify rawdata.
- Do not store PHI.
- Do not make clinical conclusions.
- Treat reports as engineering QC and research preprocessing support only.
- Require explicit approval before execution.
memory/global/USER.md

内容：

# User Memory

## Preferences

- Prefer Chinese explanations.
- Prefer staged engineering prompts.
- Prefer reproducible and auditable workflow design.
- Prefer safe, local medical imaging processing.

## Current Project

The user is building a medical imaging preprocessing Agent platform based on Hermes Agent and Claude Code Agent architecture ideas.
memory/global/ENVIRONMENT.md

内容：

# Environment Memory

This file stores environment-level facts.

## Current Known Paths

- SPM path: ./third_party/spm12
- DPABI path: ./third_party/DPABI_V8.2_240510
- MATLAB command: matlab
- Work directory: ./work
- Logs directory: ./logs
- Reports directory: ./reports
- Derivatives directory: ./derivatives

## Notes

Verify these paths with the environment check before execution.
memory/global/ERROR_KB.yaml

内容：

version: "0.1.0"
errors:
  - id: matlab_not_found
    source: matlab
    pattern: "No such file or directory: matlab"
    probable_causes:
      - MATLAB is not installed
      - MATLAB is not in PATH
      - matlab_command is incorrect in project_config
    suggested_fixes:
      - Set runtime.matlab_command to the full MATLAB executable path
      - Add MATLAB to PATH
    retryable: false

  - id: spm_path_missing
    source: spm
    pattern: "SPM directory not found"
    probable_causes:
      - third_party/spm12 is missing
      - project_config points to the wrong SPM path
    suggested_fixes:
      - Check third_party/spm12 exists
      - Update third_party.spm_dir in project_config
    retryable: false

  - id: dpabi_path_missing
    source: dpabi
    pattern: "DPABI directory not found"
    probable_causes:
      - third_party/DPABI_V8.2_240510 is missing
      - project_config points to the wrong DPABI path
    suggested_fixes:
      - Check third_party/DPABI_V8.2_240510 exists
      - Update third_party.dpabi_dir in project_config
    retryable: false

  - id: nifti_dependency_missing
    source: python
    pattern: "Missing dependency: nibabel"
    probable_causes:
      - Python dependency nibabel is not installed
    suggested_fixes:
      - pip install nibabel
      - pip install numpy nibabel pyyaml
    retryable: true

  - id: matlab_returncode_nonzero
    source: matlab
    pattern: "MATLAB exited with return code"
    probable_causes:
      - MATLAB script failed
      - SPM path is invalid
      - input NIfTI could not be read
      - output path is not writable
    suggested_fixes:
      - Inspect stdout_log and stderr_log
      - Inspect node result JSON
      - Re-run environment check
    retryable: depends
3. 创建 backend/app/runtime/memory_store.py

创建文件：

backend/app/runtime/memory_store.py

目标：提供最小 memory 文件读写能力。

功能要求：

提供函数：
ensure_memory_layout(root_dir: str = ".") -> dict
get_project_memory_dir(project_name: str, root_dir: str = ".") -> Path
append_run_history(project_name: str, record: dict, root_dir: str = ".") -> Path
read_error_kb(root_dir: str = ".") -> dict
match_error_patterns(errors: list[str], root_dir: str = ".") -> list[dict]
使用 pathlib、json、yaml。
如果 PyYAML 缺失，提示 pip install pyyaml。
不要存储 PHI。
RUN_HISTORY.jsonl 只追加，不覆盖。
如果 memory 文件不存在，自动创建基础文件。

参考实现方向：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def ensure_memory_layout(root_dir: str = ".") -> dict[str, str]:
    root = Path(root_dir)
    global_dir = root / "memory" / "global"
    projects_dir = root / "memory" / "projects"
    sessions_dir = root / "memory" / "sessions"

    global_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    defaults = {
        "MEMORY.md": "# MedImage Agent Memory\n",
        "USER.md": "# User Memory\n",
        "ENVIRONMENT.md": "# Environment Memory\n",
    }

    for filename, content in defaults.items():
        path = global_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")

    error_kb = global_dir / "ERROR_KB.yaml"
    if not error_kb.exists():
        error_kb.write_text("version: '0.1.0'\nerrors: []\n", encoding="utf-8")

    return {
        "global_dir": str(global_dir),
        "projects_dir": str(projects_dir),
        "sessions_dir": str(sessions_dir),
    }


def sanitize_project_name(project_name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in project_name)
    return safe or "default_project"


def get_project_memory_dir(project_name: str, root_dir: str = ".") -> Path:
    ensure_memory_layout(root_dir)
    project_dir = Path(root_dir) / "memory" / "projects" / sanitize_project_name(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    project_md = project_dir / "PROJECT.md"
    lessons_md = project_dir / "LESSONS.md"

    if not project_md.exists():
        project_md.write_text(f"# Project Memory: {project_name}\n", encoding="utf-8")
    if not lessons_md.exists():
        lessons_md.write_text(f"# Lessons: {project_name}\n", encoding="utf-8")

    return project_dir


def append_run_history(
    project_name: str,
    record: dict[str, Any],
    root_dir: str = ".",
) -> Path:
    project_dir = get_project_memory_dir(project_name, root_dir)
    history_path = project_dir / "RUN_HISTORY.jsonl"

    safe_record = dict(record)
    safe_record.pop("raw_patient_data", None)
    safe_record.pop("phi", None)

    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(safe_record, ensure_ascii=False) + "\n")

    return history_path


def read_error_kb(root_dir: str = ".") -> dict[str, Any]:
    ensure_memory_layout(root_dir)
    return _load_yaml(Path(root_dir) / "memory" / "global" / "ERROR_KB.yaml")


def match_error_patterns(
    errors: list[str],
    root_dir: str = ".",
) -> list[dict[str, Any]]:
    kb = read_error_kb(root_dir)
    entries = kb.get("errors", []) or []

    matches: list[dict[str, Any]] = []
    joined_errors = "\n".join(errors)

    for entry in entries:
        pattern = str(entry.get("pattern", ""))
        if pattern and pattern in joined_errors:
            matches.append(entry)

    return matches
4. 创建 backend/app/runtime/background_review.py

创建文件：

backend/app/runtime/background_review.py

目标：实现 deterministic background review。

提供函数：

run_background_review(
    agent_run_id: str,
    project_config_path: str,
    agent_summary_path: str | None = None,
) -> dict

功能要求：

读取 project_config。
确定 project_name。
找到 agent_summary.json。
从 agent_summary 中找到 pipeline_summary_path。
读取 pipeline summary。
尝试读取 dataset_summary.json。
尝试读取 exclusion_recommendations.csv。
汇总：
pipeline status
dataset quality score
subjects_total
subjects_include
subjects_manual_review
subjects_exclude
errors
warnings
matched error knowledge
写入：
work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
追加：
memory/projects/{project_name}/RUN_HISTORY.jsonl
不要自动修改 MEMORY.md / LESSONS.md。
proposed_memory_patch.md 只给建议，供用户人工合并。
不要崩溃，缺文件时记录 warnings。

参考实现方向：

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from backend.app.runtime.memory_store import (
    append_run_history,
    ensure_memory_layout,
    match_error_patterns,
)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"YAML file not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run_background_review(
    agent_run_id: str,
    project_config_path: str,
    agent_summary_path: str | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    ensure_memory_layout(".")

    project_config = _load_yaml(project_config_path)
    project_name = project_config.get("project", {}).get("name", "default_project")
    runtime = project_config.get("runtime", {})
    work_dir = runtime.get("work_dir", "./work")
    report_dir = runtime.get("report_dir", "./reports")

    agent_run_dir = Path(work_dir) / "agent_runs" / agent_run_id
    agent_run_dir.mkdir(parents=True, exist_ok=True)

    if agent_summary_path:
        summary_path = Path(agent_summary_path)
    else:
        summary_path = agent_run_dir / "agent_summary.json"

    agent_summary = _read_json(summary_path)
    if not agent_summary:
        warnings.append(f"Missing or invalid agent summary: {summary_path}")
        agent_summary = {}

    pipeline_summary_path = agent_summary.get("pipeline_summary_path")
    pipeline_summary = _read_json(Path(pipeline_summary_path)) if pipeline_summary_path else None
    if not pipeline_summary:
        warnings.append("Missing or invalid pipeline summary.")
        pipeline_summary = {}

    dataset_summary_path = Path(report_dir) / "dataset_evaluation" / "dataset_summary.json"
    dataset_summary = _read_json(dataset_summary_path)
    if not dataset_summary:
        warnings.append(f"Missing dataset summary: {dataset_summary_path}")
        dataset_summary = {}

    exclusion_path = Path(report_dir) / "dataset_evaluation" / "exclusion_recommendations.csv"
    exclusion_rows = _read_csv_rows(exclusion_path)

    all_errors: list[str] = []
    for source in [agent_summary, pipeline_summary, dataset_summary]:
        value = source.get("errors", [])
        if isinstance(value, list):
            all_errors.extend(str(x) for x in value)
        elif value:
            all_errors.append(str(value))

    matched_errors = match_error_patterns(all_errors, ".")

    pipeline_status = pipeline_summary.get("status") or agent_summary.get("pipeline_status")
    dataset_quality_score = dataset_summary.get("dataset_quality_score")
    subjects_total = dataset_summary.get("subjects_total")
    subjects_include = dataset_summary.get("subjects_include")
    subjects_manual_review = dataset_summary.get("subjects_manual_review")
    subjects_exclude = dataset_summary.get("subjects_exclude")

    review_lines: list[str] = []
    review_lines.append("# Background Review Summary")
    review_lines.append("")
    review_lines.append(f"- Agent run ID: {agent_run_id}")
    review_lines.append(f"- Project: {project_name}")
    review_lines.append(f"- Pipeline status: {pipeline_status}")
    review_lines.append(f"- Dataset quality score: {dataset_quality_score}")
    review_lines.append(f"- Total subjects: {subjects_total}")
    review_lines.append(f"- Include: {subjects_include}")
    review_lines.append(f"- Manual review: {subjects_manual_review}")
    review_lines.append(f"- Exclude: {subjects_exclude}")
    review_lines.append("")
    review_lines.append("## Warnings")
    review_lines.append("")
    if warnings:
        for item in warnings:
            review_lines.append(f"- {item}")
    else:
        review_lines.append("- None")
    review_lines.append("")
    review_lines.append("## Errors")
    review_lines.append("")
    if all_errors:
        for item in all_errors:
            review_lines.append(f"- {item}")
    else:
        review_lines.append("- None")
    review_lines.append("")
    review_lines.append("## Matched Error Knowledge")
    review_lines.append("")
    if matched_errors:
        for item in matched_errors:
            review_lines.append(f"- {item.get('id')}: {item.get('pattern')}")
            fixes = item.get("suggested_fixes", [])
            for fix in fixes:
                review_lines.append(f"  - Suggested fix: {fix}")
    else:
        review_lines.append("- None")
    review_lines.append("")
    review_lines.append("## Subjects Requiring Attention")
    review_lines.append("")
    if exclusion_rows:
        for row in exclusion_rows:
            review_lines.append(
                f"- {row.get('subject_id')}: {row.get('recommendation')} — {row.get('reasons')}"
            )
    else:
        review_lines.append("- None")

    review_summary_path = agent_run_dir / "review_summary.md"
    review_summary_path.write_text("\n".join(review_lines) + "\n", encoding="utf-8")

    patch_lines: list[str] = []
    patch_lines.append("# Proposed Memory Patch")
    patch_lines.append("")
    patch_lines.append("This file is a proposal only. Review before merging into MEMORY.md or LESSONS.md.")
    patch_lines.append("")
    patch_lines.append("## Proposed Project Lesson")
    patch_lines.append("")
    patch_lines.append(f"- Run `{agent_run_id}` finished with pipeline status `{pipeline_status}`.")
    if dataset_quality_score is not None:
        patch_lines.append(f"- Dataset quality score was `{dataset_quality_score}`.")
    if subjects_exclude:
        patch_lines.append(f"- `{subjects_exclude}` subject(s) were recommended for exclusion.")
    if subjects_manual_review:
        patch_lines.append(f"- `{subjects_manual_review}` subject(s) require manual review.")
    if matched_errors:
        patch_lines.append("")
        patch_lines.append("## Proposed Error KB Updates")
        patch_lines.append("")
        patch_lines.append("Matched known errors; no new error pattern is automatically added.")
    patch_lines.append("")
    patch_lines.append("## Safety Note")
    patch_lines.append("")
    patch_lines.append("Do not store PHI or raw imaging data in memory.")

    proposed_patch_path = agent_run_dir / "proposed_memory_patch.md"
    proposed_patch_path.write_text("\n".join(patch_lines) + "\n", encoding="utf-8")

    history_record = {
        "agent_run_id": agent_run_id,
        "project_name": project_name,
        "pipeline_status": pipeline_status,
        "dataset_quality_score": dataset_quality_score,
        "subjects_total": subjects_total,
        "subjects_include": subjects_include,
        "subjects_manual_review": subjects_manual_review,
        "subjects_exclude": subjects_exclude,
        "review_summary_path": str(review_summary_path),
        "proposed_memory_patch_path": str(proposed_patch_path),
        "matched_error_ids": [item.get("id") for item in matched_errors],
    }

    history_path = append_run_history(project_name, history_record, ".")

    return {
        "ok": True,
        "node_id": "background_review",
        "backend": "python",
        "agent_run_id": agent_run_id,
        "project_name": project_name,
        "outputs": [
            str(review_summary_path),
            str(proposed_patch_path),
            str(history_path),
        ],
        "metrics": {
            "matched_errors": len(matched_errors),
            "attention_subjects": len(exclusion_rows),
        },
        "warnings": warnings,
        "errors": errors,
    }
5. 修改 backend/app/runtime/agent_runtime.py

在 run_orchestrator_execute 中增加可选 background review。

要求：

函数签名增加参数：
run_background_review_after_execute: bool = True
pipeline 执行完成并写入 agent_summary.json 后，如果该参数为 true：
调用 run_background_review(...)
将 review result 写入 agent_summary 中的 background_review
重新保存 agent_summary.json
不要因为 background review 失败而让 pipeline execution 失败。
background review 失败时写入 warnings。

新增导入：

from backend.app.runtime.background_review import run_background_review

实现思路：

try:
    if run_background_review_after_execute:
        review_result = run_background_review(
            agent_run_id=agent_run_id,
            project_config_path=project_config_path,
            agent_summary_path=str(agent_summary_path),
        )
        agent_summary["background_review"] = review_result
        if not review_result.get("ok"):
            agent_summary.setdefault("warnings", []).append("Background review failed.")
        agent_summary_path.write_text(
            json.dumps(agent_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
except Exception as exc:
    agent_summary.setdefault("warnings", []).append(f"Background review error: {exc}")
6. 新增 backend/app/tools/background_review_cli.py

创建文件：

backend/app/tools/background_review_cli.py

功能：

默认 agent_run_id：
agent_run_001
默认 project config：
examples/project_config_dataset.yaml
调用 run_background_review。
打印 JSON。
返回码：
ok=true 返回 0
ok=false 返回 1

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.background_review import run_background_review


def main() -> int:
    agent_run_id = sys.argv[1] if len(sys.argv) > 1 else "agent_run_001"
    project_config = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/project_config_dataset.yaml")

    result = run_background_review(
        agent_run_id=agent_run_id,
        project_config_path=str(project_config),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
7. 创建 specs/background_review_spec.md

创建文件：

specs/background_review_spec.md

内容：

# Background Review Specification

The background reviewer summarizes completed agent runs and proposes memory updates.

## Inputs

- agent_summary.json
- pipeline summary.json
- dataset_summary.json
- exclusion_recommendations.csv
- ERROR_KB.yaml

## Outputs

- review_summary.md
- proposed_memory_patch.md
- RUN_HISTORY.jsonl

## Rules

- Background review must not block successful pipeline execution.
- Background review must not modify rawdata.
- Background review must not store PHI.
- Background review must not automatically rewrite MEMORY.md or USER.md.
- Proposed patches require human review.
- RUN_HISTORY.jsonl can be appended automatically.

## Review Sections

- Run overview
- Dataset quality score
- Subject recommendation counts
- Warnings
- Errors
- Matched known errors
- Subjects requiring attention
- Proposed project lessons
8. 更新 README.md

追加第八步说明：

## Step 8: Memory and Background Review

This step adds deterministic long-term memory and background review.

It creates:

```text
memory/global/MEMORY.md
memory/global/USER.md
memory/global/ENVIRONMENT.md
memory/global/ERROR_KB.yaml
memory/projects/{project_name}/RUN_HISTORY.jsonl
work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
Run with Agent Execute
python -m backend.app.tools.agent_plan_cli
python -m backend.app.tools.agent_execute_cli --approve

After execution, background review should run automatically.

Expected outputs:

work/agent_runs/agent_run_001/review_summary.md
work/agent_runs/agent_run_001/proposed_memory_patch.md
memory/projects/medimage_agent_dataset_mvp/RUN_HISTORY.jsonl
Run Background Review Manually
python -m backend.app.tools.background_review_cli
Safety

The background reviewer does not automatically rewrite stable memory files.
It only appends run history and creates proposed memory patches for human review.


---

## 9. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/memory_runtime_spec.md
specs/background_review_spec.md
memory/global/MEMORY.md
memory/global/USER.md
memory/global/ENVIRONMENT.md
memory/global/ERROR_KB.yaml
backend/app/runtime/memory_store.py
backend/app/runtime/background_review.py
backend/app/runtime/agent_runtime.py
backend/app/tools/background_review_cli.py
README.md

运行：

python -m backend.app.tools.agent_plan_cli
python -m backend.app.tools.agent_execute_cli --approve

成功后应该生成：

work/agent_runs/agent_run_001/agent_summary.json
work/agent_runs/agent_run_001/review_summary.md
work/agent_runs/agent_run_001/proposed_memory_patch.md
memory/projects/medimage_agent_dataset_mvp/RUN_HISTORY.jsonl

其中：

work/agent_runs/agent_run_001/review_summary.md

应该包含：

# Background Review Summary
- Agent run ID: agent_run_001
- Project: medimage_agent_dataset_mvp
- Pipeline status:
- Dataset quality score:

其中：

work/agent_runs/agent_run_001/proposed_memory_patch.md

应该包含：

# Proposed Memory Patch
## Proposed Project Lesson
## Safety Note

其中：

memory/projects/medimage_agent_dataset_mvp/RUN_HISTORY.jsonl

应该至少追加一行 JSONL，包含：

{
  "agent_run_id": "agent_run_001",
  "project_name": "medimage_agent_dataset_mvp"
}

也可以单独运行：

python -m backend.app.tools.background_review_cli

如果 agent_summary 或 dataset_summary 缺失，background review 不应该崩溃，而应该在 warnings 中说明缺失文件。

10. 重要限制

本步骤只做 deterministic memory + background review。

不要实现：

真实 LLM API
自然语言记忆抽取
自动修改 MEMORY.md / USER.md
自动生成 Skill
UI
FastAPI 服务
多 Agent 对话
并行调度
GPU
DPABI pipeline
数据库
临床结论

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 background review
自动生成了哪些 memory/review 文件
RUN_HISTORY.jsonl 记录了什么
proposed_memory_patch.md 为什么需要人工 review

'''
这一步主要做的是：

## 第八步：最小长期记忆 + 后台复盘 + 错误知识库闭环
这是在第七步 Agent Runtime 基础上， 借鉴 Hermes Agent 的记忆和后台复盘思想 ，实现 deterministic 的记忆系统和复盘机制（ 不接真实 LLM ）。

### 核心目标
1. Memory Layer 架构
   
   - Global Memory ( memory/global/ )：系统级稳定上下文
     
     - MEMORY.md - 系统角色和能力
     - USER.md - 用户偏好
     - ENVIRONMENT.md - 环境路径和设置
     - ERROR_KB.yaml - 已知错误模式和修复方法
   - Project Memory ( memory/projects/{project_name}/ )：项目特定知识
     
     - PROJECT.md - 项目描述
     - LESSONS.md - 学到的经验教训
     - RUN_HISTORY.jsonl - 追加-only 运行历史
2. 后台复盘 (Background Review)
   
   - 读取 agent_summary.json 、 pipeline summary 、 dataset_summary
   - 匹配错误模式（与 ERROR_KB.yaml 对比）
   - 生成 review_summary.md - 本次运行发生了什么
   - 生成 proposed_memory_patch.md - 建议的记忆更新
   - 追加到 RUN_HISTORY.jsonl
3. 错误知识库 (ERROR_KB)
   
   - 5 种预定义错误模式：
     - matlab_not_found - MATLAB 未找到
     - spm_path_missing - SPM 路径缺失
     - dpabi_path_missing - DPABI 路径缺失
     - nifti_dependency_missing - nibabel 依赖缺失
     - matlab_returncode_nonzero - MATLAB 返回非零退出码
   - 每种错误包含：pattern、probable_causes、suggested_fixes、retryable
### 安全规则
允许存储 ：

- Pipeline ID、run ID、状态
- 软件路径、QC 指标摘要
- Dataset quality score
- 已知错误模式
- 非敏感 subject ID
- INCLUDE/MANUAL_REVIEW/EXCLUDE 计数
禁止存储 （PHI 保护）：

- Patient names、hospital IDs
- Raw DICOM headers、raw NIfTI content
- 临床诊断、疾病结论
### 为什么 proposed_memory_patch.md 需要人工 review？
1. 安全第一 - 防止自动覆盖重要记忆
2. PHI 检查 - 人工确认没有存储敏感信息
3. 质量把控 - 确认建议的 lessons 是否合理
4. 稳定性 - MEMORY.md / LESSONS.md 是稳定文件，不应被自动修改
### 输出文件
```
work/agent_runs/{agent_run_id}/
├── plan.json
├── agent_summary.json
├── review_summary.md          # 复盘摘要
└── proposed_memory_patch.md   # 建议的记忆补丁（需人工 review）

memory/projects/{project_name}/
├── PROJECT.md
├── LESSONS.md
└── RUN_HISTORY.jsonl          # 自动追加
```
### 明确不做的事情
- ❌ 真实 LLM API
- ❌ 自动覆盖 MEMORY.md / LESSONS.md
- ❌ 多 Agent 智能协作
- ❌ GPU / 并行调度
- ❌ 修改 SPM / DPABI 源码
这一步已经 全部完成 并验证通过。成功实现了：

- Memory Layer 架构 ✅
- 后台复盘机制 ✅
- 错误知识库 ✅
- RUN_HISTORY 自动追加 ✅
- review_summary 和 proposed_memory_patch 生成 ✅
'''