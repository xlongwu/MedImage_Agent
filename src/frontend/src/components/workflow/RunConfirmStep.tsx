import React, { useState } from "react";
import { buildInsights, DEFAULT_API_BASE, runWorkflow } from "../../lib/api";
import type { AnalysisConfig, WorkflowAction, WorkflowState } from "../../state/workflowTypes";

interface Props { state: WorkflowState; dispatch: React.Dispatch<WorkflowAction>; }

type EnabledAnalysisConfig = { enabled: boolean };

function hasEnabledFlag(value: AnalysisConfig[keyof AnalysisConfig]): value is EnabledAnalysisConfig {
  return typeof value === "object" && value !== null && "enabled" in value;
}

export function RunConfirmStep({ state, dispatch }: Props) {
  const [running, setRunning] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const preSteps = Object.entries(state.preprocessing).filter(([, value]) => value.enabled);
  const analysisEntries = Object.entries(state.analysis) as Array<[keyof AnalysisConfig, AnalysisConfig[keyof AnalysisConfig]]>;
  const enabledAnalysisSteps = analysisEntries.filter(
    ([key, value]) => key !== "enabled" && hasEnabledFlag(value) && value.enabled
  );

  const startRun = async () => {
    setRunning(true);
    dispatch({ type: "SET_RUN_STATUS", runId: "running", status: "RUNNING" });
    try {
      const data = await runWorkflow(DEFAULT_API_BASE, {
        data_source: state.dataSource,
        dataset_path: state.datasetPath,
      });
      dispatch({ type: "SET_RUN_STATUS", runId: data.demo_id || "run", status: data.ok ? "SUCCESS" : "FAILED" });
      window.__workflowResult = data;
      await buildInsights(DEFAULT_API_BASE);
    } catch {
      dispatch({ type: "SET_RUN_STATUS", runId: "error", status: "FAILED" });
    }
    setRunning(false);
    dispatch({ type: "SET_STEP", step: 5 });
  };

  return (
    <div>
      <h2>Step 4: Confirm & Run</h2>

      <div style={{ padding: 16, background: "#f5f5f5", borderRadius: 8, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Configuration Summary</h3>

        <div style={{ marginBottom: 12 }}>
          <strong>Data:</strong> {state.dataSource === "demo" ? "Demo (Synthetic BIDS)" : state.datasetPath || "Not selected"}
        </div>

        <div style={{ marginBottom: 12 }}>
          <strong>Preprocessing ({preSteps.length} steps):</strong>{" "}
          {preSteps.map(([k]) => (k as string).replace(/([A-Z])/g, " $1").trim()).join(", ")}
        </div>

        {state.analysis.enabled && (
          <div style={{ marginBottom: 12 }}>
            <strong>Analysis:</strong>{" "}
            {enabledAnalysisSteps
              .map(([k]) => k).join(", ")}
          </div>
        )}

        <div style={{ fontSize: 12, color: "#888" }}>
          Output: derivatives/, reports/, exports/, work/
        </div>
      </div>

      <div style={{ padding: 12, background: "#fff3e0", borderRadius: 6, marginBottom: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14 }}>
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
          <span>
            {state.dataSource === "demo"
              ? "I confirm this is a demo run. No MATLAB/SPM/DPABI execution. Rawdata will not be modified."
              : "I confirm rawdata will not be modified. Output will be written to derivatives/ and reports/."}
          </span>
        </label>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 3 })} style={btnBack}>Back</button>
        <button onClick={startRun} disabled={!confirmed || running} style={{
          ...btnRun, opacity: !confirmed || running ? 0.5 : 1, cursor: !confirmed || running ? "not-allowed" : "pointer",
        }}>
          {running ? "Running..." : state.dataSource === "demo" ? "Run Quickstart Demo" : "Start Processing"}
        </button>
      </div>

      {running && (
        <div style={{ marginTop: 16, padding: 12, background: "#e3f2fd", borderRadius: 6, textAlign: "center", color: "#1976d2", fontWeight: 600 }}>
          Processing... This may take a minute.
        </div>
      )}
    </div>
  );
}

const btnRun: React.CSSProperties = { padding: "10px 28px", background: "#4caf50", color: "#fff", border: "none", borderRadius: 6, fontSize: 15, fontWeight: 700 };
const btnBack: React.CSSProperties = { padding: "8px 20px", background: "#f5f5f5", border: "1px solid #ccc", borderRadius: 4, cursor: "pointer" };
