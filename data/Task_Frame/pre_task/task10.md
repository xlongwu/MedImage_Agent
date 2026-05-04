你是我的工程搭建助手。前九步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。
Step 8：完成最小长期记忆、后台复盘和错误知识库闭环。
Step 9：完成最小 FastAPI 后端服务闭环。

现在开始第十步。

第十步目标：实现“最小可视化前端闭环”。

这一步要为 MedImage Agent 建立一个本地 Web UI，使用户可以在浏览器中完成：

- 查看 API 健康状态
- 查看项目配置
- 查看 pipeline 列表
- 查看 pipeline 节点
- 创建 Agent Plan
- 查看 plan.json
- 明确点击批准后执行 pipeline
- 查看 agent_summary
- 查看 background review
- 查看 dataset evaluation report
- 查看 subject_qc_table.csv
- 查看关键输出文件路径

本步骤只做最小 React 前端，不做复杂 UI，不做拖拽 Pipeline Builder，不做 WebSocket，不做登录，不做数据库，不做真实 LLM，不做多用户。

不要实现：
- React Flow 拖拽式 DAG
- WebSocket 实时日志
- 用户系统
- 权限登录
- 数据库
- 多项目管理
- 真实医学影像可视化
- Niivue
- GPU 配置页面
- DPABI pipeline
- 复杂状态管理库
- Electron
- 生产部署

本步骤只做能跑通的本地前端 MVP。

---

## 1. 创建 specs/frontend_mvp_spec.md

创建文件：

```text
specs/frontend_mvp_spec.md

内容：

# Frontend MVP Specification

This document defines the MVP web frontend for MedImage Agent.

## Goals

The frontend should provide a minimal visual workflow for:

1. Checking backend API status.
2. Viewing project configuration.
3. Viewing available pipelines.
4. Inspecting a selected pipeline.
5. Creating an Agent plan.
6. Reviewing the generated plan.
7. Explicitly approving execution.
8. Viewing agent run summary.
9. Viewing dataset evaluation reports.
10. Viewing background review and proposed memory patch.

## Scope

Supported:

- React + TypeScript + Vite
- Local FastAPI backend
- Simple dashboard layout
- API health check
- Pipeline list
- Plan button
- Execute with approval button
- Report viewer
- JSON / Markdown / CSV text preview

Unsupported:

- Authentication
- Multi-user support
- Database
- Drag-and-drop pipeline builder
- WebSocket logs
- Real-time task streaming
- Medical image viewer
- GPU dashboard
- DPABI-specific UI
- Production deployment

## Safety Rules

- Execution button must clearly say it will run the approved pipeline.
- Execution must send `approved: true`.
- UI must never call execute automatically.
- UI must not provide delete file controls.
- UI must not expose arbitrary file reading beyond backend safe-file API.
- UI must distinguish QC/report output from clinical diagnosis.

## MVP Pages

The MVP can be a single page with sections:

1. API Status
2. Project Config
3. Pipeline Explorer
4. Agent Plan
5. Execute Pipeline
6. Agent Run Summary
7. Dataset Evaluation Report
8. Background Review

## Default Backend

```text
http://127.0.0.1:8000

---

## 2. 创建 frontend/ Vite React 项目结构

如果当前项目没有 frontend/，请创建：

```text
frontend/
├── package.json
├── index.html
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api.ts
    ├── types.ts
    ├── styles.css
    └── components/
        ├── Section.tsx
        ├── JsonBlock.tsx
        ├── StatusBadge.tsx
        ├── PipelineExplorer.tsx
        ├── AgentControls.tsx
        ├── ReportViewer.tsx
        └── TextViewer.tsx

如果 frontend/ 已存在，不要删除已有内容；只按需补齐文件。

3. 创建 frontend/package.json

内容：

{
  "name": "medimage-agent-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1 --port 5173",
    "build": "tsc && vite build",
    "preview": "vite preview --host 127.0.0.1 --port 5173"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "typescript": "latest",
    "react": "latest",
    "react-dom": "latest"
  },
  "devDependencies": {}
}

不要引入复杂 UI 库。先用纯 CSS。

4. 创建 frontend/tsconfig.json

内容：

{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}
5. 创建 frontend/vite.config.ts

内容：

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173
  }
});
6. 创建 frontend/index.html

内容：

<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>MedImage Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
7. 创建 frontend/src/types.ts

内容：

export type ApiResult<T = unknown> = {
  ok?: boolean;
  error?: string;
} & T;

export type PipelineSummary = {
  pipeline_id: string;
  version: string;
  modality: string;
  description: string;
  nodes_total: number;
  nodes: Array<{
    id: string;
    name: string;
    backend: string;
    parallel_level: string;
    depends_on: string[];
  }>;
};

export type AgentPlanRequest = {
  agent_run_id: string;
  project_config_path: string;
  pipeline_path: string;
};

export type AgentExecuteRequest = AgentPlanRequest & {
  approved: boolean;
};

export type AgentRun = {
  ok: boolean;
  agent_run_id: string;
  plan: unknown | null;
  agent_summary: unknown | null;
  review_summary: string | null;
  proposed_memory_patch: string | null;
};

export type DatasetEvaluationReport = {
  ok: boolean;
  dataset_summary: unknown | null;
  subject_qc_table: string | null;
  exclusion_recommendations: string | null;
  report_markdown: string | null;
  report_html: string | null;
};
8. 创建 frontend/src/api.ts

内容：

import type {
  AgentExecuteRequest,
  AgentPlanRequest,
  AgentRun,
  DatasetEvaluationReport
} from "./types";

export const DEFAULT_API_BASE = "http://127.0.0.1:8000";

async function requestJson<T>(
  baseUrl: string,
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    },
    ...options
  });

  const text = await response.text();
  let payload: unknown;

  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { ok: false, error: text };
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? JSON.stringify((payload as { detail: unknown }).detail, null, 2)
        : text;
    throw new Error(detail || `HTTP ${response.status}`);
  }

  return payload as T;
}

export async function getHealth(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/health");
}

export async function getProjectConfig(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/project-config");
}

export async function listPipelines(baseUrl: string) {
  return requestJson<{ ok: boolean; pipelines: string[] }>(
    baseUrl,
    "/api/pipelines"
  );
}

export async function getPipeline(baseUrl: string, pipelineName: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/pipelines/${encodeURIComponent(pipelineName)}`
  );
}

export async function createAgentPlan(
  baseUrl: string,
  payload: AgentPlanRequest
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/agent/plan", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function executeAgentPlan(
  baseUrl: string,
  payload: AgentExecuteRequest
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/agent/execute", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAgentRun(baseUrl: string, agentRunId: string) {
  return requestJson<AgentRun>(
    baseUrl,
    `/api/agent-runs/${encodeURIComponent(agentRunId)}`
  );
}

export async function getDatasetEvaluationReport(baseUrl: string) {
  return requestJson<DatasetEvaluationReport>(
    baseUrl,
    "/api/reports/dataset-evaluation"
  );
}
9. 创建 frontend/src/components/Section.tsx

内容：

import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  children: ReactNode;
};

export function Section({ title, description, children }: Props) {
  return (
    <section className="section">
      <div className="sectionHeader">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      <div>{children}</div>
    </section>
  );
}
10. 创建 frontend/src/components/JsonBlock.tsx

内容：

type Props = {
  value: unknown;
  emptyText?: string;
};

export function JsonBlock({ value, emptyText = "No data" }: Props) {
  if (value === null || value === undefined) {
    return <div className="empty">{emptyText}</div>;
  }

  return (
    <pre className="codeBlock">
      {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
    </pre>
  );
}
11. 创建 frontend/src/components/StatusBadge.tsx

内容：

type Props = {
  status?: string | boolean | null;
};

export function StatusBadge({ status }: Props) {
  const text =
    typeof status === "boolean" ? (status ? "OK" : "FAILED") : status || "UNKNOWN";

  const normalized = String(text).toUpperCase();

  let className = "badge";
  if (["OK", "SUCCESS", "HEALTHY"].includes(normalized)) {
    className += " badgeSuccess";
  } else if (["FAILED", "ERROR", "INVALID"].includes(normalized)) {
    className += " badgeError";
  } else if (["PARTIAL", "WARNING", "MANUAL_REVIEW"].includes(normalized)) {
    className += " badgeWarning";
  }

  return <span className={className}>{text}</span>;
}
12. 创建 frontend/src/components/TextViewer.tsx

内容：

type Props = {
  text?: string | null;
  emptyText?: string;
};

export function TextViewer({ text, emptyText = "No text available" }: Props) {
  if (!text) {
    return <div className="empty">{emptyText}</div>;
  }

  return <pre className="textViewer">{text}</pre>;
}
13. 创建 frontend/src/components/PipelineExplorer.tsx

内容：

import { useEffect, useState } from "react";
import { getPipeline, listPipelines } from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
  selectedPipeline: string;
  onSelectPipeline: (value: string) => void;
};

export function PipelineExplorer({
  baseUrl,
  selectedPipeline,
  onSelectPipeline
}: Props) {
  const [pipelines, setPipelines] = useState<string[]>([]);
  const [pipelineDetail, setPipelineDetail] = useState<unknown>(null);
  const [status, setStatus] = useState<string>("IDLE");
  const [error, setError] = useState<string>("");

  async function refreshPipelines() {
    setStatus("LOADING");
    setError("");
    try {
      const result = await listPipelines(baseUrl);
      setPipelines(result.pipelines || []);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function loadPipeline(path: string) {
    const name = path.split("/").pop() || path;
    onSelectPipeline(path);
    setPipelineDetail(null);
    setError("");

    try {
      const result = await getPipeline(baseUrl, name);
      setPipelineDetail(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refreshPipelines();
  }, [baseUrl]);

  return (
    <div>
      <div className="row">
        <button onClick={refreshPipelines}>刷新 Pipeline</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="pipelineList">
        {pipelines.map((pipeline) => (
          <button
            key={pipeline}
            className={
              pipeline === selectedPipeline ? "listItem selected" : "listItem"
            }
            onClick={() => loadPipeline(pipeline)}
          >
            {pipeline}
          </button>
        ))}
      </div>

      <JsonBlock value={pipelineDetail} emptyText="请选择一个 pipeline" />
    </div>
  );
}
14. 创建 frontend/src/components/AgentControls.tsx

内容：

import { useState } from "react";
import {
  createAgentPlan,
  executeAgentPlan,
  getAgentRun
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
  selectedPipeline: string;
  onAgentRunLoaded?: (value: unknown) => void;
};

export function AgentControls({
  baseUrl,
  selectedPipeline,
  onAgentRunLoaded
}: Props) {
  const [agentRunId, setAgentRunId] = useState("agent_run_001");
  const [projectConfigPath, setProjectConfigPath] = useState(
    "examples/project_config_dataset.yaml"
  );
  const [pipelinePath, setPipelinePath] = useState(
    selectedPipeline || "examples/pipeline_subject_preprocess.yaml"
  );
  const [plan, setPlan] = useState<unknown>(null);
  const [summary, setSummary] = useState<unknown>(null);
  const [agentRun, setAgentRun] = useState<unknown>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  function currentPipelinePath() {
    return selectedPipeline || pipelinePath;
  }

  async function handlePlan() {
    setStatus("PLANNING");
    setError("");
    setPlan(null);

    try {
      const result = await createAgentPlan(baseUrl, {
        agent_run_id: agentRunId,
        project_config_path: projectConfigPath,
        pipeline_path: currentPipelinePath()
      });
      setPlan(result);
      setStatus("PLAN_READY");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleExecute() {
    const confirmed = window.confirm(
      "确认执行 pipeline？这会调用后端运行已批准的计划，并可能启动 MATLAB。"
    );

    if (!confirmed) {
      return;
    }

    setStatus("EXECUTING");
    setError("");

    try {
      const result = await executeAgentPlan(baseUrl, {
        agent_run_id: agentRunId,
        project_config_path: projectConfigPath,
        pipeline_path: currentPipelinePath(),
        approved: true
      });
      setSummary(result);
      setStatus("EXECUTED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadAgentRun() {
    setError("");
    try {
      const result = await getAgentRun(baseUrl, agentRunId);
      setAgentRun(result);
      onAgentRunLoaded?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="formGrid">
        <label>
          Agent Run ID
          <input
            value={agentRunId}
            onChange={(event) => setAgentRunId(event.target.value)}
          />
        </label>

        <label>
          Project Config
          <input
            value={projectConfigPath}
            onChange={(event) => setProjectConfigPath(event.target.value)}
          />
        </label>

        <label>
          Pipeline Path
          <input
            value={currentPipelinePath()}
            onChange={(event) => setPipelinePath(event.target.value)}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={handlePlan}>生成 Plan</button>
        <button className="dangerButton" onClick={handleExecute}>
          批准并执行 Pipeline
        </button>
        <button onClick={handleLoadAgentRun}>加载 Agent Run</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <h3>Plan</h3>
      <JsonBlock value={plan} emptyText="尚未生成 plan" />

      <h3>Execution Summary</h3>
      <JsonBlock value={summary} emptyText="尚未执行" />

      <h3>Agent Run</h3>
      <JsonBlock value={agentRun} emptyText="尚未加载 agent run" />
    </div>
  );
}
15. 创建 frontend/src/components/ReportViewer.tsx

内容：

import { useState } from "react";
import { getDatasetEvaluationReport } from "../api";
import type { DatasetEvaluationReport } from "../types";
import { JsonBlock } from "./JsonBlock";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function ReportViewer({ baseUrl }: Props) {
  const [report, setReport] = useState<DatasetEvaluationReport | null>(null);
  const [activeTab, setActiveTab] = useState<
    "summary" | "markdown" | "csv" | "exclusion" | "html"
  >("summary");
  const [error, setError] = useState("");

  async function refreshReport() {
    setError("");
    try {
      const result = await getDatasetEvaluationReport(baseUrl);
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="row">
        <button onClick={refreshReport}>刷新报告</button>
        <button onClick={() => setActiveTab("summary")}>Summary</button>
        <button onClick={() => setActiveTab("markdown")}>Markdown</button>
        <button onClick={() => setActiveTab("csv")}>QC CSV</button>
        <button onClick={() => setActiveTab("exclusion")}>Exclusion</button>
        <button onClick={() => setActiveTab("html")}>HTML Source</button>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {activeTab === "summary" ? (
        <JsonBlock value={report?.dataset_summary} emptyText="暂无 dataset summary" />
      ) : null}

      {activeTab === "markdown" ? (
        <TextViewer text={report?.report_markdown} emptyText="暂无 Markdown 报告" />
      ) : null}

      {activeTab === "csv" ? (
        <TextViewer text={report?.subject_qc_table} emptyText="暂无 subject QC table" />
      ) : null}

      {activeTab === "exclusion" ? (
        <TextViewer
          text={report?.exclusion_recommendations}
          emptyText="暂无 exclusion recommendations"
        />
      ) : null}

      {activeTab === "html" ? (
        <TextViewer text={report?.report_html} emptyText="暂无 HTML 报告" />
      ) : null}
    </div>
  );
}
16. 创建 frontend/src/App.tsx

内容：

import { useEffect, useState } from "react";
import { getHealth, getProjectConfig } from "./api";
import { AgentControls } from "./components/AgentControls";
import { JsonBlock } from "./components/JsonBlock";
import { PipelineExplorer } from "./components/PipelineExplorer";
import { ReportViewer } from "./components/ReportViewer";
import { Section } from "./components/Section";
import { StatusBadge } from "./components/StatusBadge";
import "./styles.css";

export default function App() {
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:8000");
  const [health, setHealth] = useState<unknown>(null);
  const [projectConfig, setProjectConfig] = useState<unknown>(null);
  const [selectedPipeline, setSelectedPipeline] = useState(
    "examples/pipeline_subject_preprocess.yaml"
  );
  const [error, setError] = useState("");

  async function refreshHealth() {
    setError("");
    try {
      const result = await getHealth(baseUrl);
      setHealth(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setHealth({ ok: false });
    }
  }

  async function refreshProjectConfig() {
    setError("");
    try {
      const result = await getProjectConfig(baseUrl);
      setProjectConfig(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refreshHealth();
    refreshProjectConfig();
  }, []);

  const healthStatus =
    typeof health === "object" && health && "status" in health
      ? String((health as { status?: unknown }).status)
      : "UNKNOWN";

  return (
    <main className="app">
      <header className="hero">
        <div>
          <h1>MedImage Agent</h1>
          <p>
            可视化医学影像预处理 Agent MVP：Plan Mode、执行审批、QC
            报告与后台复盘。
          </p>
        </div>
        <div className="heroCard">
          <div>API Status</div>
          <StatusBadge status={healthStatus} />
        </div>
      </header>

      <section className="topBar">
        <label>
          Backend API
          <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
        </label>
        <button onClick={refreshHealth}>检查 API</button>
        <button onClick={refreshProjectConfig}>读取 Project Config</button>
      </section>

      {error ? <div className="errorBox">{error}</div> : null}

      <Section
        title="1. Project Config"
        description="显示后端默认项目配置。"
      >
        <JsonBlock value={projectConfig} />
      </Section>

      <Section
        title="2. Pipeline Explorer"
        description="查看 examples/ 下的 pipeline YAML 和节点信息。"
      >
        <PipelineExplorer
          baseUrl={baseUrl}
          selectedPipeline={selectedPipeline}
          onSelectPipeline={setSelectedPipeline}
        />
      </Section>

      <Section
        title="3. Agent Plan / Execute"
        description="先生成 plan，再明确批准执行。执行可能调用 MATLAB。"
      >
        <AgentControls baseUrl={baseUrl} selectedPipeline={selectedPipeline} />
      </Section>

      <Section
        title="4. Dataset Evaluation Report"
        description="查看数据集级评估结果、QC 表和报告内容。"
      >
        <ReportViewer baseUrl={baseUrl} />
      </Section>

      <footer className="footer">
        <p>
          本系统当前仅用于工程 QC 与科研预处理辅助，不提供临床诊断结论。
        </p>
      </footer>
    </main>
  );
}
17. 创建 frontend/src/main.tsx

内容：

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
18. 创建 frontend/src/styles.css

内容：

:root {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  color: #172033;
  background: #f6f7fb;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

button {
  border: 1px solid #d2d8e8;
  background: white;
  border-radius: 10px;
  padding: 9px 14px;
  cursor: pointer;
  font-weight: 600;
}

button:hover {
  border-color: #6a7cff;
}

input {
  border: 1px solid #d2d8e8;
  border-radius: 10px;
  padding: 9px 12px;
  min-width: 280px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #506080;
}

.app {
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  gap: 20px;
  margin-bottom: 20px;
}

.hero h1 {
  margin: 0 0 8px;
  font-size: 36px;
}

.hero p {
  margin: 0;
  color: #596579;
}

.heroCard {
  min-width: 180px;
  background: white;
  border: 1px solid #e4e8f2;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 10px 30px rgba(35, 45, 80, 0.06);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}

.topBar {
  background: white;
  border: 1px solid #e4e8f2;
  border-radius: 18px;
  padding: 16px;
  display: flex;
  gap: 12px;
  align-items: end;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.section {
  background: white;
  border: 1px solid #e4e8f2;
  border-radius: 20px;
  padding: 20px;
  margin: 18px 0;
  box-shadow: 0 10px 30px rgba(35, 45, 80, 0.04);
}

.sectionHeader {
  margin-bottom: 14px;
}

.sectionHeader h2 {
  margin: 0 0 6px;
  font-size: 22px;
}

.sectionHeader p {
  margin: 0;
  color: #68758b;
}

.row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 12px;
}

.formGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.codeBlock,
.textViewer {
  background: #0f172a;
  color: #e5e7eb;
  border-radius: 14px;
  padding: 16px;
  overflow: auto;
  max-height: 520px;
  font-size: 13px;
  line-height: 1.55;
}

.textViewer {
  white-space: pre-wrap;
}

.empty {
  color: #7b8496;
  background: #f6f7fb;
  border: 1px dashed #d2d8e8;
  padding: 14px;
  border-radius: 12px;
}

.errorBox {
  background: #fff1f2;
  border: 1px solid #fecdd3;
  color: #9f1239;
  border-radius: 12px;
  padding: 12px;
  white-space: pre-wrap;
  margin: 10px 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  padding: 5px 10px;
  background: #eef2ff;
  color: #3730a3;
  font-weight: 700;
  font-size: 12px;
}

.badgeSuccess {
  background: #dcfce7;
  color: #166534;
}

.badgeError {
  background: #fee2e2;
  color: #991b1b;
}

.badgeWarning {
  background: #fef3c7;
  color: #92400e;
}

.pipelineList {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0 14px;
}

.listItem {
  text-align: left;
}

.selected {
  border-color: #6a7cff;
  background: #eef2ff;
}

.dangerButton {
  background: #111827;
  color: white;
  border-color: #111827;
}

.dangerButton:hover {
  border-color: #374151;
}

.footer {
  color: #6b7280;
  text-align: center;
  margin-top: 28px;
}
19. 更新 README.md

追加第十步说明：

## Step 10: MVP Frontend

This step adds a minimal React + Vite frontend for the local FastAPI backend.

### Start Backend

```bash
pip install fastapi uvicorn pydantic requests pyyaml
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
Start Frontend
cd frontend
npm install
npm run dev

Open:

http://127.0.0.1:5173
Frontend Features
API health check
project config viewer
pipeline explorer
agent plan creation
explicit approved execution
agent run summary viewer
dataset evaluation report viewer
Safety

The frontend does not execute a pipeline automatically.
The user must click the execution button and confirm approval.


---

## 20. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/frontend_mvp_spec.md
frontend/package.json
frontend/index.html
frontend/tsconfig.json
frontend/vite.config.ts
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/api.ts
frontend/src/types.ts
frontend/src/styles.css
frontend/src/components/Section.tsx
frontend/src/components/JsonBlock.tsx
frontend/src/components/StatusBadge.tsx
frontend/src/components/PipelineExplorer.tsx
frontend/src/components/AgentControls.tsx
frontend/src/components/ReportViewer.tsx
frontend/src/components/TextViewer.tsx
README.md

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

启动前端：

cd frontend
npm install
npm run dev

打开：

http://127.0.0.1:5173

页面应该能完成：

显示 API healthy。
显示 project config。
显示 pipeline 列表。
点击 pipeline 后显示节点信息。
点击“生成 Plan”后生成并显示 plan。
点击“批准并执行 Pipeline”前有 confirm 弹窗。
执行完成后显示 agent summary。
点击“刷新报告”后显示 dataset_summary 和报告内容。
如果后端没有启动，页面应显示清晰错误。
前端不能自动执行 pipeline。
21. 重要限制

本步骤只做最小可视化前端。

不要实现：

拖拽 Pipeline Builder
React Flow
医学影像 Viewer
WebSocket 实时日志
登录系统
用户系统
数据库
Electron
生产部署
真实 LLM 对话界面
多 Agent 对话
GPU dashboard
DPABI pipeline 专属页面

完成后请总结：

新增了哪些文件
修改了哪些文件
如何启动后端
如何启动前端
页面能完成哪些操作
安全限制有哪些
如果前端请求失败应该检查什么

'''
这一步主要做的是：

## 第十步：最小可视化前端闭环
这一步为 MedImage Agent 建立一个本地 Web UI，使用户可以在浏览器中完成完整的 Agent 工作流程。

### 核心目标
创建一个最小化的 React 前端，让用户能够：

1. 查看 API 健康状态
2. 查看项目配置
3. 查看 pipeline 列表和详情
4. 创建 Agent Plan
5. 明确点击批准后执行 pipeline
6. 查看 agent_summary
7. 查看 background review
8. 查看 dataset evaluation report
9. 查看 subject_qc_table.csv
10. 查看关键输出文件路径
### 实现的功能
前端技术栈 ：

- React 18 + TypeScript + Vite
- 纯 CSS（无复杂 UI 库）
页面组件 ：

1. API 状态 ( Section + StatusBadge )
   
   - 检查后端服务健康状态
   - 显示健康/错误状态徽章
2. 项目配置 ( JsonBlock )
   
   - 以 JSON 格式展示项目配置
3. Pipeline 浏览器 ( PipelineExplorer )
   
   - 列出所有可用的 pipeline YAML 文件
   - 点击查看 pipeline 详情（节点、依赖关系等）
4. Agent 控制 ( AgentControls )
   
   - 输入 Agent Run ID、Project Config、Pipeline Path
   - 生成 Plan 按钮 - 创建执行计划
   - 批准并执行 Pipeline 按钮 - 需要用户确认
   - 加载 Agent Run 按钮 - 查看历史运行
5. Agent Run 汇总
   
   - 显示 Plan JSON
   - 显示 Execution Summary
   - 显示 Review Summary（后台复盘）
   - 显示 Proposed Memory Patch（建议的记忆更新）
6. 数据集评估报告 ( ReportViewer )
   
   - Summary（JSON）
   - Markdown 报告
   - QC CSV 表格
   - Exclusion 推荐
   - HTML 源码
### 安全特性
- 执行按钮明确显示"批准并执行 Pipeline"
- 执行前弹出 window.confirm 确认对话框
- UI 不会自动调用 execute
- 无删除文件控件
- 无任意文件读取（通过后端安全 API）
### 项目结构
```
frontend/
├── package.json          # 依赖配置
├── tsconfig.json         # TypeScript 配置
├── vite.config.ts        # Vite 配置
├── index.html            # HTML 入口
└── src/
    ├── main.tsx          # React 入口
    ├── App.tsx           # 主应用组件
    ├── api.ts            # API 调用封装
    ├── types.ts          # TypeScript 类型定义
    ├── styles.css        # 样式
    ├── vite-env.d.ts     # Vite 类型声明
    └── components/
        ├── Section.tsx          # 区块组件
        ├── JsonBlock.tsx        # JSON 展示
        ├── StatusBadge.tsx      # 状态徽章
        ├── TextViewer.tsx       # 文本展示
        ├── PipelineExplorer.tsx # Pipeline 浏览器
        ├── AgentControls.tsx    # Agent 控制面板
        └── ReportViewer.tsx     # 报告查看器
```
### 使用方式
```
# 1. 启动后端 API
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 
8000

# 2. 启动前端开发服务器
cd frontend
npm run dev

# 3. 打开浏览器访问 http://127.0.0.1:5173
```
### 工作流程
1. 检查 API 状态是否为 Healthy
2. 在 Pipeline 浏览器中选择一个 pipeline
3. 点击"生成 Plan"创建执行计划
4. 查看生成的 plan.json
5. 点击"批准并执行 Pipeline"（需要确认）
6. 查看执行结果和报告
### 明确不做的事情
- ❌ React Flow 拖拽式 DAG
- ❌ WebSocket 实时日志
- ❌ 用户系统 / 权限登录
- ❌ 数据库
- ❌ 多项目管理
- ❌ 真实医学影像可视化（Niivue）
- ❌ GPU 配置页面
- ❌ DPABI pipeline
- ❌ 复杂状态管理库（Redux/MobX）
- ❌ Electron 桌面应用
- ❌ 生产部署
这一步已经 全部完成 并验证通过。成功实现了：

- React + TypeScript + Vite 项目结构 ✅
- 所有 UI 组件 ✅
- API 连接和类型定义 ✅
- Build 成功 ✅
- 后端 API 连接正常 ✅
'''