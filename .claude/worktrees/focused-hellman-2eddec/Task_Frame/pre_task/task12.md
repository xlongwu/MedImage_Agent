你是我的工程搭建助手。前十一步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。
Step 8：完成最小长期记忆、后台复盘和错误知识库闭环。
Step 9：完成最小 FastAPI 后端服务闭环。
Step 10：完成最小 React 前端闭环。
Step 11：完成 Run Monitor + State / Log Viewer 闭环。

现在开始第十二步。

第十二步目标：实现“错误诊断与重跑建议闭环”。

当前系统已经可以：
- 执行 pipeline
- 查看 run summary
- 查看 state
- 查看日志
- 查看 report
- 读取 ERROR_KB.yaml

但还缺一个关键能力：当 pipeline 或某个 subject/node 失败时，系统应该能自动读取 state、errors、warnings、stdout/stderr 日志，匹配 ERROR_KB，生成结构化诊断结果和安全的 retry plan。

本步骤要实现：

- Error Diagnosis Spec
- deterministic error diagnoser
- 从 run summary / node states / logs 中收集错误
- 匹配 memory/global/ERROR_KB.yaml
- 生成 diagnosis.json
- 生成 diagnosis_report.md
- 生成 retry_plan.json
- 生成 retry_plan.md
- 后端 API 暴露诊断结果
- 前端 Run Monitor 中增加 Error Diagnosis 区域
- 不自动执行 retry
- 不删除文件
- 不修改 state
- 不修改 rawdata
- 不自动修改 memory

不要实现：
- 自动重跑
- UI 中的重跑按钮
- WebSocket
- 数据库
- 并行调度
- GPU
- DPABI pipeline
- 真实 LLM
- 多 Agent 对话
- 自动修改 ERROR_KB
- 删除文件
- 任意命令执行

本步骤只做 deterministic error diagnosis 和 retry plan 生成。

---

## 1. 创建 specs/error_diagnosis_spec.md

创建文件：

```text
specs/error_diagnosis_spec.md

内容：

# Error Diagnosis Specification

This document defines the MVP error diagnosis and retry planning behavior.

## Goals

The Error Diagnoser helps users understand failed or suspicious pipeline runs.

It should:

- Read pipeline summary.
- Read project-level node states.
- Read subject-level node states.
- Collect errors and warnings.
- Read safe stdout/stderr logs.
- Match known patterns from ERROR_KB.yaml.
- Generate diagnosis.json.
- Generate diagnosis_report.md.
- Generate retry_plan.json.
- Generate retry_plan.md.

## Scope

Supported:

- deterministic diagnosis
- ERROR_KB pattern matching
- state-based failure detection
- log-based pattern matching
- safe retry recommendations
- Markdown report generation

Unsupported:

- automatic retry execution
- automatic file deletion
- automatic state modification
- automatic memory modification
- clinical diagnosis
- real LLM inference
- DPABI-specific deep diagnosis
- GPU-specific scheduling diagnosis

## Inputs

```text
work/pipeline_runs/{run_id}/summary.json
work/states/{run_id}/...
logs/*.log
memory/global/ERROR_KB.yaml
Outputs
work/diagnosis/{run_id}/diagnosis.json
work/diagnosis/{run_id}/diagnosis_report.md
work/diagnosis/{run_id}/retry_plan.json
work/diagnosis/{run_id}/retry_plan.md
Diagnosis Categories
ENVIRONMENT_ERROR
MATLAB_ERROR
SPM_ERROR
PYTHON_DEPENDENCY_ERROR
NIFTI_IO_ERROR
DATASET_STRUCTURE_ERROR
QC_FAILURE
UNKNOWN_ERROR
Retry Recommendation Types
NO_RETRY
SAFE_RETRY
FIX_CONFIG_THEN_RETRY
FIX_DEPENDENCY_THEN_RETRY
MANUAL_REVIEW
RERUN_ENVIRONMENT_CHECK
Safety Rules
Do not execute retry automatically.
Do not delete outputs.
Do not modify rawdata.
Do not modify derivatives.
Do not modify state files.
Retry plan is advisory only.
Any future retry execution must require explicit user approval.

---

## 2. 创建 backend/app/runtime/error_diagnoser.py

创建文件：

```text
backend/app/runtime/error_diagnoser.py

目标：读取 run 状态、日志和 ERROR_KB，生成诊断和 retry plan。

功能要求：

提供主函数：
diagnose_run(
    run_id: str,
    work_dir: str = "./work",
    log_dir: str = "./logs",
    memory_root: str = ".",
) -> dict
输入：
run_id
work_dir
log_dir
memory/global/ERROR_KB.yaml
输出目录：
work/diagnosis/{run_id}/
写入：
diagnosis.json
diagnosis_report.md
retry_plan.json
retry_plan.md
读取：
pipeline summary
project-level states
subject-level states
state 中的 errors/warnings
state 中 stdout_log / stderr_log 的内容摘要
ERROR_KB.yaml
日志读取必须安全：
只读取 logs/ 下 .log 文件
每个 log 最多读取前 20000 字符和后 20000 字符
不读取 NIfTI
不读取 third_party
不读取 rawdata
诊断输出结构：
{
  "ok": true,
  "run_id": "run_subject_preprocess_001",
  "status": "SUCCESS",
  "issues_total": 0,
  "issues": [],
  "retry_plan_path": "work/diagnosis/run_subject_preprocess_001/retry_plan.json",
  "outputs": [
    "work/diagnosis/run_subject_preprocess_001/diagnosis.json",
    "work/diagnosis/run_subject_preprocess_001/diagnosis_report.md",
    "work/diagnosis/run_subject_preprocess_001/retry_plan.json",
    "work/diagnosis/run_subject_preprocess_001/retry_plan.md"
  ],
  "warnings": [],
  "errors": []
}
issue 结构：
{
  "issue_id": "issue_001",
  "scope": "subject",
  "subject_id": "sub-001",
  "node": "spm_smooth_subject",
  "status": "FAILED",
  "category": "SPM_ERROR",
  "message": "MATLAB exited with return code 1.",
  "matched_error_ids": ["matlab_returncode_nonzero"],
  "probable_causes": [],
  "suggested_fixes": [],
  "retry_recommendation": "RERUN_ENVIRONMENT_CHECK",
  "stdout_log": "logs/sub-001_spm_smooth_stdout.log",
  "stderr_log": "logs/sub-001_spm_smooth_stderr.log"
}
retry_plan 结构：
{
  "run_id": "run_subject_preprocess_001",
  "safe_to_auto_retry": false,
  "requires_approval": true,
  "steps": [
    {
      "step_id": "retry_001",
      "action": "RERUN_ENVIRONMENT_CHECK",
      "reason": "MATLAB returned non-zero exit code.",
      "scope": "project",
      "requires_user_action": true
    }
  ]
}
3. error_diagnoser.py 参考实现方向

可以按下面结构实现，但允许根据已有代码调整。

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.runtime.memory_store import match_error_patterns
from backend.app.runtime.run_inspector import inspect_run


LOG_READ_LIMIT = 20_000


def _read_text_excerpt(path: str | None) -> str:
    if not path:
        return ""

    p = Path(path)
    normalized = str(p).replace("\\", "/")

    if not normalized.startswith("logs/") and "/logs/" not in normalized:
        return ""

    if p.suffix.lower() != ".log":
        return ""

    if not p.exists():
        return ""

    text = p.read_text(encoding="utf-8", errors="replace")
    if len(text) <= LOG_READ_LIMIT * 2:
        return text

    return (
        text[:LOG_READ_LIMIT]
        + "\n\n...[LOG TRUNCATED]...\n\n"
        + text[-LOG_READ_LIMIT:]
    )


def _categorize_issue(message: str, matched_errors: list[dict[str, Any]]) -> str:
    text = message.lower()

    for item in matched_errors:
        source = str(item.get("source", "")).lower()
        if source == "matlab":
            return "MATLAB_ERROR"
        if source == "spm":
            return "SPM_ERROR"
        if source == "dpabi":
            return "DPABI_ERROR"
        if source == "python":
            return "PYTHON_DEPENDENCY_ERROR"

    if "matlab" in text:
        return "MATLAB_ERROR"
    if "spm" in text:
        return "SPM_ERROR"
    if "nifti" in text or ".nii" in text:
        return "NIFTI_IO_ERROR"
    if "missing dependency" in text or "importerror" in text:
        return "PYTHON_DEPENDENCY_ERROR"
    if "dataset" in text or "bids" in text:
        return "DATASET_STRUCTURE_ERROR"
    if "qc" in text or "nan_count" in text:
        return "QC_FAILURE"

    return "UNKNOWN_ERROR"


def _retry_recommendation(category: str, matched_errors: list[dict[str, Any]]) -> str:
    if matched_errors:
        retryable_values = {str(item.get("retryable")) for item in matched_errors}
        if "false" in retryable_values:
            return "FIX_CONFIG_THEN_RETRY"
        if "true" in retryable_values:
            return "SAFE_RETRY"

    if category in {"PYTHON_DEPENDENCY_ERROR"}:
        return "FIX_DEPENDENCY_THEN_RETRY"
    if category in {"MATLAB_ERROR", "SPM_ERROR"}:
        return "RERUN_ENVIRONMENT_CHECK"
    if category in {"QC_FAILURE"}:
        return "MANUAL_REVIEW"

    return "MANUAL_REVIEW"


def _collect_issue_from_state(
    issue_id: str,
    state: dict[str, Any],
    scope: str,
) -> dict[str, Any] | None:
    status = state.get("status")
    errors = state.get("errors", []) or []
    warnings = state.get("warnings", []) or []

    if status not in {"FAILED", "NEEDS_REVIEW"} and not errors:
        return None

    stdout_log = state.get("stdout_log") or state.get("log_path")
    stderr_log = state.get("stderr_log")

    stdout_excerpt = _read_text_excerpt(stdout_log)
    stderr_excerpt = _read_text_excerpt(stderr_log)

    messages: list[str] = []
    messages.extend(str(item) for item in errors)
    messages.extend(str(item) for item in warnings)

    if stdout_excerpt:
        messages.append(stdout_excerpt)
    if stderr_excerpt:
        messages.append(stderr_excerpt)

    matched_errors = match_error_patterns(messages, ".")
    category = _categorize_issue("\n".join(messages), matched_errors)
    retry = _retry_recommendation(category, matched_errors)

    probable_causes: list[str] = []
    suggested_fixes: list[str] = []

    for item in matched_errors:
        probable_causes.extend(item.get("probable_causes", []) or [])
        suggested_fixes.extend(item.get("suggested_fixes", []) or [])

    return {
        "issue_id": issue_id,
        "scope": scope,
        "subject_id": state.get("subject"),
        "node": state.get("node"),
        "status": status,
        "category": category,
        "message": "; ".join(str(item) for item in errors[:3]) if errors else f"status={status}",
        "matched_error_ids": [item.get("id") for item in matched_errors],
        "probable_causes": probable_causes,
        "suggested_fixes": suggested_fixes,
        "retry_recommendation": retry,
        "stdout_log": stdout_log,
        "stderr_log": stderr_log,
    }


def _build_retry_plan(run_id: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    steps = []
    safe_to_auto_retry = True

    for index, issue in enumerate(issues, start=1):
        recommendation = issue.get("retry_recommendation", "MANUAL_REVIEW")

        if recommendation != "SAFE_RETRY":
            safe_to_auto_retry = False

        steps.append({
            "step_id": f"retry_{index:03d}",
            "action": recommendation,
            "reason": issue.get("message"),
            "scope": issue.get("scope"),
            "subject_id": issue.get("subject_id"),
            "node": issue.get("node"),
            "requires_user_action": recommendation != "SAFE_RETRY",
            "matched_error_ids": issue.get("matched_error_ids", []),
            "suggested_fixes": issue.get("suggested_fixes", []),
        })

    return {
        "run_id": run_id,
        "safe_to_auto_retry": safe_to_auto_retry and bool(issues),
        "requires_approval": True,
        "steps": steps,
    }


def _write_markdown_report(
    path: Path,
    run_id: str,
    diagnosis: dict[str, Any],
    retry_plan: dict[str, Any],
) -> None:
    lines: list[str] = []
    lines.append("# Error Diagnosis Report")
    lines.append("")
    lines.append(f"- Run ID: {run_id}")
    lines.append(f"- Pipeline status: {diagnosis.get('status')}")
    lines.append(f"- Issues total: {diagnosis.get('issues_total')}")
    lines.append("")
    lines.append("## Issues")
    lines.append("")

    issues = diagnosis.get("issues", [])
    if not issues:
        lines.append("No failed or suspicious nodes were detected.")
    else:
        for issue in issues:
            lines.append(f"### {issue.get('issue_id')} · {issue.get('node')}")
            lines.append("")
            lines.append(f"- Scope: {issue.get('scope')}")
            lines.append(f"- Subject: {issue.get('subject_id')}")
            lines.append(f"- Status: {issue.get('status')}")
            lines.append(f"- Category: {issue.get('category')}")
            lines.append(f"- Retry recommendation: {issue.get('retry_recommendation')}")
            lines.append(f"- Message: {issue.get('message')}")
            lines.append("")
            if issue.get("matched_error_ids"):
                lines.append("Matched known errors:")
                for item in issue.get("matched_error_ids", []):
                    lines.append(f"- {item}")
                lines.append("")
            if issue.get("suggested_fixes"):
                lines.append("Suggested fixes:")
                for fix in issue.get("suggested_fixes", []):
                    lines.append(f"- {fix}")
                lines.append("")

    lines.append("## Retry Plan")
    lines.append("")
    lines.append(f"- Requires approval: {retry_plan.get('requires_approval')}")
    lines.append(f"- Safe to auto retry: {retry_plan.get('safe_to_auto_retry')}")
    lines.append("")

    steps = retry_plan.get("steps", [])
    if not steps:
        lines.append("No retry steps are required.")
    else:
        for step in steps:
            lines.append(
                f"- {step.get('step_id')}: {step.get('action')} "
                f"for {step.get('subject_id')} / {step.get('node')}"
            )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This retry plan is advisory only. It does not execute retries automatically.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def diagnose_run(
    run_id: str,
    work_dir: str = "./work",
    log_dir: str = "./logs",
    memory_root: str = ".",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    inspection = inspect_run(run_id=run_id, work_dir=work_dir)
    summary = inspection.get("summary") or {}
    pipeline_status = summary.get("status", "UNKNOWN")

    issues: list[dict[str, Any]] = []

    counter = 1

    for state in inspection.get("project_states", []):
        issue = _collect_issue_from_state(
            issue_id=f"issue_{counter:03d}",
            state=state,
            scope="project",
        )
        if issue:
            issues.append(issue)
            counter += 1

    for subject in inspection.get("subjects", []):
        for state in subject.get("nodes", []):
            issue = _collect_issue_from_state(
                issue_id=f"issue_{counter:03d}",
                state=state,
                scope="subject",
            )
            if issue:
                issues.append(issue)
                counter += 1

    out_dir = Path(work_dir) / "diagnosis" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    retry_plan = _build_retry_plan(run_id, issues)

    diagnosis_path = out_dir / "diagnosis.json"
    diagnosis_report_path = out_dir / "diagnosis_report.md"
    retry_plan_path = out_dir / "retry_plan.json"
    retry_plan_md_path = out_dir / "retry_plan.md"

    diagnosis = {
        "ok": True,
        "run_id": run_id,
        "status": pipeline_status,
        "issues_total": len(issues),
        "issues": issues,
        "retry_plan_path": str(retry_plan_path),
        "outputs": [
            str(diagnosis_path),
            str(diagnosis_report_path),
            str(retry_plan_path),
            str(retry_plan_md_path),
        ],
        "warnings": warnings + inspection.get("warnings", []),
        "errors": errors,
    }

    diagnosis_path.write_text(
        json.dumps(diagnosis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    retry_plan_path.write_text(
        json.dumps(retry_plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_markdown_report(
        path=diagnosis_report_path,
        run_id=run_id,
        diagnosis=diagnosis,
        retry_plan=retry_plan,
    )

    retry_lines = [
        "# Retry Plan",
        "",
        f"- Run ID: {run_id}",
        f"- Requires approval: {retry_plan.get('requires_approval')}",
        f"- Safe to auto retry: {retry_plan.get('safe_to_auto_retry')}",
        "",
        "## Steps",
        "",
    ]

    if retry_plan.get("steps"):
        for step in retry_plan["steps"]:
            retry_lines.append(f"### {step.get('step_id')}")
            retry_lines.append("")
            retry_lines.append(f"- Action: {step.get('action')}")
            retry_lines.append(f"- Subject: {step.get('subject_id')}")
            retry_lines.append(f"- Node: {step.get('node')}")
            retry_lines.append(f"- Reason: {step.get('reason')}")
            retry_lines.append(f"- Requires user action: {step.get('requires_user_action')}")
            retry_lines.append("")
    else:
        retry_lines.append("No retry required.")

    retry_lines.append("")
    retry_lines.append("This file is advisory only. It does not execute commands.")

    retry_plan_md_path.write_text("\n".join(retry_lines) + "\n", encoding="utf-8")

    return diagnosis
4. 新增 backend/app/tools/diagnose_run_cli.py

创建文件：

backend/app/tools/diagnose_run_cli.py

功能：

默认 run_id：
run_subject_preprocess_001
调用 diagnose_run。
打印 diagnosis JSON。
返回码：
ok=true 返回 0
ok=false 返回 1

参考实现：

from __future__ import annotations

import json
import sys

from backend.app.runtime.error_diagnoser import diagnose_run


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "run_subject_preprocess_001"

    result = diagnose_run(run_id=run_id)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
5. 修改 backend/app/api/routes.py

新增 API：

GET /api/runs/{run_id}/diagnosis

要求：

调用 diagnose_run。
不自动执行 retry。
返回 diagnosis JSON。
诊断输出文件可通过 /api/files/read 安全读取。
run_id 必须校验，禁止路径穿越。

新增导入：

from backend.app.runtime.error_diagnoser import diagnose_run

新增路由：

@router.get("/api/runs/{run_id}/diagnosis")
def api_diagnose_run(run_id: str) -> dict[str, Any]:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")

    result = diagnose_run(run_id=run_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result
6. 修改 frontend/src/api.ts

新增函数：

export async function diagnoseRun(baseUrl: string, runId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/runs/${encodeURIComponent(runId)}/diagnosis`
  );
}
7. 创建 frontend/src/components/ErrorDiagnosis.tsx

创建文件：

frontend/src/components/ErrorDiagnosis.tsx

内容：

import { useState } from "react";
import { diagnoseRun } from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
  defaultRunId?: string;
};

export function ErrorDiagnosis({
  baseUrl,
  defaultRunId = "run_subject_preprocess_001"
}: Props) {
  const [runId, setRunId] = useState(defaultRunId);
  const [diagnosis, setDiagnosis] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleDiagnose() {
    setStatus("DIAGNOSING");
    setError("");
    setDiagnosis(null);

    try {
      const result = await diagnoseRun(baseUrl, runId);
      setDiagnosis(result);
      const issuesTotal =
        typeof result.issues_total === "number" ? result.issues_total : 0;
      setStatus(issuesTotal > 0 ? "ISSUES_FOUND" : "SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const issues =
    diagnosis && Array.isArray(diagnosis.issues)
      ? (diagnosis.issues as Array<Record<string, unknown>>)
      : [];

  return (
    <div>
      <div className="formGrid">
        <label>
          Run ID
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>
      </div>

      <div className="row">
        <button onClick={handleDiagnose}>生成错误诊断</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {issues.length > 0 ? (
        <div className="issueList">
          {issues.map((issue) => (
            <div key={String(issue.issue_id)} className="issueCard">
              <div className="stateCardHeader">
                <strong>{String(issue.issue_id)} · {String(issue.node)}</strong>
                <StatusBadge status={String(issue.category || "UNKNOWN")} />
              </div>
              <div className="stateMeta">
                <span>Subject: {String(issue.subject_id || "project")}</span>
                <span>Status: {String(issue.status || "UNKNOWN")}</span>
                <span>
                  Retry: {String(issue.retry_recommendation || "MANUAL_REVIEW")}
                </span>
              </div>
              <div className="smallError">{String(issue.message || "")}</div>
              {Array.isArray(issue.suggested_fixes) &&
              issue.suggested_fixes.length > 0 ? (
                <div className="fixBox">
                  <strong>Suggested fixes</strong>
                  <ul>
                    {(issue.suggested_fixes as unknown[]).map((fix, index) => (
                      <li key={index}>{String(fix)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : diagnosis ? (
        <div className="empty">未发现失败或可疑节点。</div>
      ) : null}

      <h3>Diagnosis JSON</h3>
      <JsonBlock value={diagnosis} emptyText="尚未生成诊断" />
    </div>
  );
}
8. 修改 frontend/src/App.tsx

新增导入：

import { ErrorDiagnosis } from "./components/ErrorDiagnosis";

在 Run Monitor 后面新增 Section：

<Section
  title="5. Error Diagnosis"
  description="读取 state 和日志，匹配 ERROR_KB，生成错误诊断和重跑建议。"
>
  <ErrorDiagnosis baseUrl={baseUrl} />
</Section>

如果 Dataset Evaluation Report 原来是第 5 节，顺延为第 6 节。

9. 修改 frontend/src/styles.css

追加样式：

.issueList {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 12px 0;
}

.issueCard {
  border: 1px solid #f3d19e;
  background: #fffaf0;
  border-radius: 16px;
  padding: 14px;
}

.fixBox {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px;
  margin-top: 10px;
}

.fixBox ul {
  margin: 8px 0 0;
  padding-left: 20px;
}
10. 更新 backend/app/tools/api_smoke_test.py

增加测试：

call("GET", "/api/runs/run_subject_preprocess_001/diagnosis")

注意：这个 API 只读 state/log 并生成 diagnosis 文件，不执行 pipeline。

11. 更新 README.md

追加第十二步说明：

## Step 12: Error Diagnosis and Retry Plan

This step adds deterministic error diagnosis.

It reads:

- pipeline summary
- node states
- subject states
- stdout / stderr logs
- ERROR_KB.yaml

It writes:

```text
work/diagnosis/{run_id}/diagnosis.json
work/diagnosis/{run_id}/diagnosis_report.md
work/diagnosis/{run_id}/retry_plan.json
work/diagnosis/{run_id}/retry_plan.md
CLI
python -m backend.app.tools.diagnose_run_cli run_subject_preprocess_001
API
curl http://127.0.0.1:8000/api/runs/run_subject_preprocess_001/diagnosis
Frontend

Open the frontend and use the Error Diagnosis section.

Safety

The retry plan is advisory only.

This step does not:

execute retry
delete files
modify rawdata
modify derivatives
modify state
modify memory automatically

---

## 12. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/error_diagnosis_spec.md
backend/app/runtime/error_diagnoser.py
backend/app/tools/diagnose_run_cli.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/ErrorDiagnosis.tsx
frontend/src/App.tsx
frontend/src/styles.css
README.md

运行 CLI：

python -m backend.app.tools.diagnose_run_cli run_subject_preprocess_001

成功后应生成：

work/diagnosis/run_subject_preprocess_001/diagnosis.json
work/diagnosis/run_subject_preprocess_001/diagnosis_report.md
work/diagnosis/run_subject_preprocess_001/retry_plan.json
work/diagnosis/run_subject_preprocess_001/retry_plan.md

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/runs/run_subject_preprocess_001/diagnosis
python -m backend.app.tools.api_smoke_test

启动前端：

cd frontend
npm run dev

打开：

http://127.0.0.1:5173

页面应该能完成：

输入 run_id。
点击“生成错误诊断”。
如果无错误，显示未发现失败或可疑节点。
如果有失败 state，显示 issue card。
issue card 中显示 subject、node、category、retry recommendation。
显示 suggested fixes。
显示 diagnosis JSON。
不自动执行任何 retry。
不提供删除按钮。
不修改 state 文件。
13. 重要限制

本步骤只做 Error Diagnosis + Retry Plan。

不要实现：

自动 retry
retry 按钮
删除文件
修改 state
修改 memory
真实 LLM 诊断
WebSocket
数据库
并行调度
GPU
DPABI pipeline
复杂日志流式读取
医学诊断结论

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行错误诊断
诊断输出在哪里
retry_plan 为什么只是 advisory
前端如何查看诊断结果


'''
这一步（Step 12）主要实现的是 "错误诊断与重跑建议闭环" 。

## 核心目标
当 pipeline 或某个 subject/node 失败时，系统能够：

1. 自动分析 - 读取 state、errors、warnings、stdout/stderr 日志
2. 错误匹配 - 匹配 memory/global/ERROR_KB.yaml 中的已知错误模式
3. 生成诊断 - 生成结构化的诊断结果
4. 重试建议 - 生成安全的 retry plan
## 关键实现
### 后端
- Error Diagnoser - 读取 run 状态、日志和 ERROR_KB，生成诊断和 retry plan
- 4 个输出文件 ：
  - diagnosis.json - 结构化诊断
  - diagnosis_report.md - 可读报告
  - retry_plan.json - 机器可读重试计划
  - retry_plan.md - 可读重试计划
- 新 API 端点 ： GET /api/runs/{run_id}/diagnosis
### 前端
- ErrorDiagnosis 组件 - 错误诊断 UI
  - 输入 Run ID
  - 运行诊断
  - 显示问题列表（状态、分类、消息、匹配的错误模式、建议修复、重试建议）
## 诊断分类
- ENVIRONMENT_ERROR
- MATLAB_ERROR
- SPM_ERROR
- PYTHON_DEPENDENCY_ERROR
- NIFTI_IO_ERROR
- DATASET_STRUCTURE_ERROR
- QC_FAILURE
- UNKNOWN_ERROR
## 重试建议类型
- NO_RETRY
- SAFE_RETRY
- FIX_CONFIG_THEN_RETRY
- FIX_DEPENDENCY_THEN_RETRY
- MANUAL_REVIEW
- RERUN_ENVIRONMENT_CHECK
## 限制（明确不做）
- ❌ 自动重跑
- ❌ UI 中的重跑按钮
- ❌ 自动修改 ERROR_KB
- ❌ 删除文件
- ❌ 任意命令执行
这一步只做 deterministic error diagnosis 和 retry plan 生成 ，不执行任何重试操作。
'''