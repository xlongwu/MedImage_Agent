# Phase B2：Insights Dashboard 运行洞察面板

> 目标版本：v0.2.0 | 预计工期：2–3 天 | 前置条件：Phase B1 SessionDB 完成

---

## 1. 目标与范围

基于 SessionDB 生成运维级 insights，使项目具备可观测性。核心指标包括成功率、失败率、最慢节点、最常见错误等。

**不做**：LLM 驱动的分析、实时监控、告警推送。

---

## 2. 前置条件检查

- [ ] Phase B1 SessionDB 可用
- [ ] SessionDB 中至少有 1 条 run 记录（可通过 quickstart demo 生成）

---

## 3. 新增/修改文件清单

```text
backend/app/tools/insights.py               # 新增：Insights 计算引擎
backend/app/api/routes.py                   # 修改：新增 2 个端点
backend/app/api/models.py                   # 修改：新增 InsightsResponse model
examples/pipeline_insights.yaml             # 新增：pipeline YAML
tests/unit/test_insights.py                 # 新增：测试
frontend/src/components/InsightsDashboardPanel.tsx  # 新增：前端面板
frontend/src/App.tsx                        # 修改：注册新面板
reports/insights/                           # 新增：insights 输出目录
```

---

## 4. 核心指标定义

```text
核心指标 (Phase B2)：
  total_runs            总运行次数
  success_rate          成功率 (SUCCESS / total)
  failure_rate          失败率
  partial_rate          部分成功率
  avg_duration_seconds  平均运行时长
  recent_trend          最近 10 次运行趋势
  slowest_nodes         Top 5 最慢节点
  most_failed_nodes     Top 5 最常失败节点
  top_error_categories  Top 5 错误类别
  subject_failure_map   每个 subject 的失败节点数
  run_timeline          最近 20 次运行的时间线
```

---

## 5. 逐步实施步骤

### Step 1：创建 Insights 计算引擎

文件：`backend/app/tools/insights.py`

```python
"""Insights engine — generate operational metrics from SessionDB."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from backend.app.memory.session_db import SessionDB


def build_insights(
    db_path: str = "outputs/memory/sessions/archive.sqlite",
    report_dir: str = "./reports/insights",
) -> dict[str, Any]:
    db = SessionDB(db_path)
    stats = db.stats()

    runs = db.query_runs(limit=200)
    errors = db.query_errors(limit=500)
    error_cats = db.error_categories()

    # Success/failure breakdown
    total = stats["total_runs"]
    success = stats["success_runs"]
    failed = total - success
    success_rate = round(success / total * 100, 1) if total > 0 else 0
    failure_rate = round(failed / total * 100, 1) if total > 0 else 0

    # Duration stats
    durations = [r.get("duration_seconds") for r in runs if r.get("duration_seconds")]
    avg_duration = round(mean(durations), 1) if durations else 0
    median_duration = round(median(durations), 1) if durations else 0
    max_duration = round(max(durations), 1) if durations else 0

    # Node-level aggregation (query all nodes)
    node_stats: dict[str, dict[str, Any]] = {}
    for run in runs:
        nodes = db.query_nodes_by_run(run["run_id"])
        for n in nodes:
            nid = n["node_id"]
            if nid not in node_stats:
                node_stats[nid] = {"total": 0, "success": 0, "failed": 0, "durations": []}
            node_stats[nid]["total"] += 1
            if n.get("ok"):
                node_stats[nid]["success"] += 1
            else:
                node_stats[nid]["failed"] += 1
            if n.get("duration_seconds"):
                node_stats[nid]["durations"].append(n["duration_seconds"])

    slowest_nodes = sorted(
        [{"node_id": k, "avg_duration": round(mean(v["durations"]), 1),
          "count": v["total"], "failure_rate": round(v["failed"]/max(v["total"],1)*100, 1)}
         for k, v in node_stats.items() if v["durations"]],
        key=lambda x: -x["avg_duration"],
    )[:5]

    most_failed = sorted(
        [{"node_id": k, "failed": v["failed"], "total": v["total"],
          "failure_rate": round(v["failed"]/max(v["total"],1)*100, 1)}
         for k, v in node_stats.items()],
        key=lambda x: -x["failed"],
    )[:5]

    # Recent trend (last 10 runs)
    recent = runs[:10]
    trend = [{"run_id": r["run_id"], "status": r["status"], "started_at": r.get("started_at")} for r in recent]

    # Subject failure map
    subject_failures: dict[str, int] = {}
    for run in runs[-50:]:  # last 50 runs
        nodes = db.query_nodes_by_run(run["run_id"])
        for n in nodes:
            sid = n.get("subject_id", "project")
            if sid != "project" and not n.get("ok"):
                subject_failures[sid] = subject_failures.get(sid, 0) + 1

    insights = {
        "ok": True,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "summary": {
            "total_runs": total,
            "success": success,
            "failed": failed,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "avg_duration_seconds": avg_duration,
            "median_duration_seconds": median_duration,
            "max_duration_seconds": max_duration,
            "total_errors_logged": stats["total_errors"],
        },
        "slowest_nodes": slowest_nodes,
        "most_failed_nodes": most_failed,
        "top_error_categories": error_cats[:5],
        "recent_trend": trend,
        "subject_failure_map": {
            k: v for k, v in sorted(subject_failures.items(), key=lambda x: -x[1])[:20]
        },
    }

    db.close()

    # Write reports
    report_out = Path(report_dir)
    report_out.mkdir(parents=True, exist_ok=True)
    (report_out / "insights_summary.json").write_text(
        json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown report
    lines = [
        "# MedImage Agent Insights Report",
        "",
        f"Generated: {insights['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Total Runs: **{total}**",
        f"- Success Rate: **{success_rate}%**",
        f"- Failure Rate: **{failure_rate}%**",
        f"- Avg Duration: **{avg_duration}s** (median: {median_duration}s, max: {max_duration}s)",
        f"- Total Errors Logged: **{stats['total_errors']}**",
        "",
        "## Slowest Nodes (avg duration)",
        "",
        "| Node | Avg Duration (s) | Count | Failure Rate |",
        "|------|-----------------:|------:|-------------:|",
    ]
    for n in slowest_nodes:
        lines.append(f"| {n['node_id']} | {n['avg_duration']} | {n['count']} | {n['failure_rate']}% |")

    lines += [
        "",
        "## Most Failed Nodes",
        "",
        "| Node | Failed | Total | Failure Rate |",
        "|------|-------:|------:|-------------:|",
    ]
    for n in most_failed:
        lines.append(f"| {n['node_id']} | {n['failed']} | {n['total']} | {n['failure_rate']}% |")

    lines += [
        "",
        "## Top Error Categories",
        "",
        "| Category | Count |",
        "|----------|------:|",
    ]
    for c in error_cats[:5]:
        lines.append(f"| {c['category']} | {c['count']} |")

    lines += ["", "## Safety Note", "", "Insights are generated from run history only. No rawdata is accessed."]

    (report_out / "insights_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return insights
```

### Step 2：新增 API 端点

在 `routes.py` 中新增：

```python
from backend.app.tools.insights import build_insights


@router.post("/api/insights/build")
async def insights_build():
    """Build insights from SessionDB."""
    return build_insights()


@router.get("/api/insights")
async def insights_get():
    """Get latest insights report."""
    import json
    from pathlib import Path
    path = Path("outputs/reports/insights/insights_summary.json")
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No insights built yet. POST /api/insights/build first.")
    return json.loads(path.read_text(encoding="utf-8"))
```

### Step 3：前端组件

文件：`frontend/src/components/InsightsDashboardPanel.tsx`

核心结构：
- 顶部 KPI 卡片（总运行数、成功率、失败率、平均时长）
- 最近趋势折线图区域（可用 CSS bar chart 代替图表库）
- Top 5 最慢节点表格
- Top 5 最常失败节点表格
- Top 错误类别表格
- "Build Insights" 按钮触发 `POST /api/insights/build`
- 加载时显示 `GET /api/insights`

### Step 4：测试

```python
def test_insights_generates_from_session_db(tmp_path: Path):
    from backend.app.memory.session_db import SessionDB
    from backend.app.tools.insights import build_insights

    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))
    db.upsert_run({"run_id": "r1", "pipeline_id": "p1", "status": "SUCCESS", "duration_seconds": 120.0})
    db.upsert_run({"run_id": "r2", "pipeline_id": "p1", "status": "FAILED", "duration_seconds": 45.0})
    db.insert_node({"run_id": "r1", "node_id": "motion_qc", "ok": True, "status": "SUCCESS", "duration_seconds": 5.0})
    db.insert_node({"run_id": "r2", "node_id": "normalize", "ok": False, "status": "FAILED", "errors": ["err"]})
    db.insert_error({"run_id": "r2", "node_id": "normalize", "category": "SPM_ERROR", "message": "fail"})
    db.close()

    report_dir = str(tmp_path / "reports" / "insights")
    insights = build_insights(db_path=str(db_path), report_dir=report_dir)

    assert insights["ok"] is True
    assert insights["summary"]["total_runs"] == 2
    assert insights["summary"]["success_rate"] == 50.0
    assert len(insights["most_failed_nodes"]) >= 1
    assert Path(report_dir, "insights_summary.json").exists()
```

---

## 6. 验收标准

- [ ] `build_insights()` 从 SessionDB 计算所有核心指标
- [ ] 生成的 `insights_summary.json` 和 `insights_report.md` 格式正确
- [ ] API `POST /api/insights/build` 可触发构建
- [ ] API `GET /api/insights` 返回最新报告
- [ ] 前端 InsightsDashboardPanel 显示 KPI 卡片和表格
- [ ] 零 run 时 insights 不崩溃（返回全 0 值）
- [ ] 不依赖 LLM
- [ ] 不修改 rawdata 或 SessionDB 之外的任何文件
- [ ] 单元测试通过
