import { useState } from "react";
import {
  createAgentPlan,
  executeAgentPlan,
  getAgentRun
} from "../lib/api/legacy";
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
