import { useState } from "react";
import {
  getRsfmriPreprocessingPlan,
  refreshRsfmriPreprocessingPlan
} from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriPreprocessingPlanPanel({ baseUrl }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await getRsfmriPreprocessingPlan(baseUrl);
      setPayload(result);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleRefresh() {
    setStatus("REFRESHING");
    setError("");

    try {
      const result = await refreshRsfmriPreprocessingPlan(baseUrl);
      setPayload({
        ok: true,
        plan: result
      });
      setStatus("REFRESHED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const plan = payload?.plan as Record<string, unknown> | undefined;
  const summary = plan?.summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleLoad}>Load rs-fMRI Preprocessing Plan</button>
        <button onClick={handleRefresh}>Refresh Plan</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Steps</span>
          <strong>{String(plan?.steps_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Approval Steps</span>
          <strong>{String(summary?.approval_required_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>MATLAB Steps</span>
          <strong>{String(summary?.matlab_steps_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>GPU Candidates</span>
          <strong>{String(summary?.gpu_candidate_count ?? "-")}</strong>
        </div>
      </div>

      <h3>rs-fMRI Preprocessing Plan JSON</h3>
      <JsonBlock value={plan} emptyText="Plan not yet loaded" />

      <h3>rs-fMRI Preprocessing Plan Report</h3>
      <TextViewer
        text={
          typeof payload?.report === "string"
            ? payload.report
            : null
        }
        emptyText="No plan report available"
      />
    </div>
  );
}
