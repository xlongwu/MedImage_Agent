import { useState } from "react";
import { createSchedulerPlan } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
};

export function SchedulerPanel({ baseUrl }: Props) {
  const [projectConfigPath, setProjectConfigPath] = useState(
    "examples/project_config_dataset.yaml"
  );
  const [pipelinePath, setPipelinePath] = useState(
    "examples/pipeline_subject_preprocess_parallel.yaml"
  );
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleCreatePlan() {
    setError("");
    setStatus("LOADING");
    setPlan(null);

    try {
      const result = await createSchedulerPlan(baseUrl, {
        project_config_path: projectConfigPath,
        pipeline_path: pipelinePath,
      });
      setPlan(result);
      setStatus("DONE");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const mode = (plan?.mode as string) || "unknown";
  const maxWorkers = (plan?.max_workers as number) || 1;
  const matlabMaxWorkers = (plan?.matlab_max_workers as number) || 1;
  const subjectNodes = (plan?.subject_level_nodes as string[]) || [];
  const matlabSubjectNodes = (plan?.matlab_subject_nodes as string[]) || [];
  const warnings = (plan?.warnings as string[]) || [];
  const estimatedParallelism = (plan?.estimated_parallelism as Record<string, unknown>) || {};

  return (
    <div>
      <div className="formGrid">
        <label>
          Project Config Path
          <input
            value={projectConfigPath}
            onChange={(e) => setProjectConfigPath(e.target.value)}
          />
        </label>
        <label>
          Pipeline Path
          <input
            value={pipelinePath}
            onChange={(e) => setPipelinePath(e.target.value)}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={handleCreatePlan} disabled={status === "LOADING"}>
          {status === "LOADING" ? "生成中..." : "生成 Scheduler Plan"}
        </button>
        {plan ? <StatusBadge status={plan.ok ? "SUCCESS" : "FAILED"} /> : null}
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {plan ? (
        <div>
          <h3>Scheduler 配置</h3>
          <div className="jsonBlock">
            <div>Mode: {mode}</div>
            <div>Max Workers: {maxWorkers}</div>
            <div>MATLAB Max Workers: {matlabMaxWorkers}</div>
          </div>

          <h3>并行度估计</h3>
          <div className="jsonBlock">
            <div>Subject Workers: {String(estimatedParallelism.subject_workers)}</div>
            <div>MATLAB Workers: {String(estimatedParallelism.matlab_workers)}</div>
          </div>

          <h3>Subject-Level Nodes</h3>
          {subjectNodes.length > 0 ? (
            <ul>
              {subjectNodes.map((nodeId) => (
                <li key={nodeId}>
                  {nodeId}
                  {matlabSubjectNodes.includes(nodeId) ? " (MATLAB)" : ""}
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty">无 subject-level 节点</div>
          )}

          {warnings.length > 0 ? (
            <div>
              <h3>警告</h3>
              <div className="issueList">
                {warnings.map((warning, index) => (
                  <div key={index} className="issueCard">
                    <div className="issueMessage">{warning}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <h3>完整 Plan JSON</h3>
          <JsonBlock value={plan} emptyText="无 plan 数据" />
        </div>
      ) : null}
    </div>
  );
}
