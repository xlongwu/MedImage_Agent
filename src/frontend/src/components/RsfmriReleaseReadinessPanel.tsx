import { useState } from "react";
import { getReleaseReadiness, runReleaseReadiness } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
export function RsfmriReleaseReadinessPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  async function handleRun() {
    setStatus("RUNNING");
    try {
      setResult(
        await runReleaseReadiness(baseUrl, {
          project_config_path: "examples/project_config_dataset.yaml",
          pipeline_path: "examples/pipeline_rsfmri_release_readiness.yaml",
        }),
      );
      setStatus("SUCCESS");
    } catch (err) {
      setStatus("ERROR");
    }
  }
  async function handleLoad() {
    setStatus("LOADING");
    try {
      setLoaded(await getReleaseReadiness(baseUrl));
      setStatus("LOADED");
    } catch (err) {
      setStatus("ERROR");
    }
  }
  const r = loaded?.result as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>Run Release Readiness Check</button>
        <button onClick={handleLoad}>Load Results</button>
        <StatusBadge status={status} />
      </div>
      <div className="metricGrid">
        <div className="metricCard">
          <span>Status</span>
          <strong>{String(r?.release_readiness_status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Checks</span>
          <strong>{String(r?.checks_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(r?.checks_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>FAIL</span>
          <strong>{String(r?.checks_fail ?? "-")}</strong>
        </div>
      </div>
      <h3>Result</h3>
      <JsonBlock value={loaded?.result} emptyText="No result" />
      <h3>Checks</h3>
      <JsonBlock value={r?.checks} emptyText="No checks" />
      <h3>Report</h3>
      <TextViewer
        text={typeof loaded?.report === "string" ? loaded.report : null}
        emptyText="No report"
      />
      <h3>Dashboard</h3>
      <JsonBlock value={loaded?.dashboard} emptyText="No dashboard" />
    </div>
  );
}
