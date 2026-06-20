import { useState } from "react";
import { getRsfmriReho, runRsfmriReho } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
export function RsfmriRehoPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");
  async function handleRun() {
    if (!window.confirm("Run Python ReHo? Synthetic derivatives only, no DPABI/GPU.")) return;
    setStatus("RUNNING");
    setError("");
    try {
      const r = await runRsfmriReho(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_reho.yaml",
        approved: true,
      });
      setResult(r);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  async function handleLoad() {
    setStatus("LOADING");
    setError("");
    try {
      setLoaded(await getRsfmriReho(baseUrl));
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  const s = loaded?.reho_qc_summary as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          Approve and Run Python ReHo
        </button>
        <button onClick={handleLoad}>Load ReHo Results</button>
        <StatusBadge status={status} />
      </div>
      {error ? <div className="errorBox">{error}</div> : null}
      <div className="metricGrid">
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(s?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(s?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>WARNING</span>
          <strong>{String(s?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>FAIL</span>
          <strong>{String(s?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Mean ReHo</span>
          <strong>{s?.mean_reho_mean == null ? "-" : Number(s.mean_reho_mean).toFixed(4)}</strong>
        </div>
      </div>
      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="Not yet run" />
      <h3>ReHo QC Summary</h3>
      <JsonBlock value={loaded?.reho_qc_summary} emptyText="No summary" />
      <h3>Subject QC</h3>
      <JsonBlock value={loaded?.subject_reho_qc} emptyText="No subject QC" />
      <h3>Subject Results</h3>
      <JsonBlock value={loaded?.subject_reho_results} emptyText="No results" />
      <h3>GPU Contract</h3>
      <JsonBlock value={loaded?.gpu_candidate_contract} emptyText="No GPU contract" />
      <h3>DPABI Contract</h3>
      <JsonBlock value={loaded?.dpabi_backend_contract} emptyText="No DPABI contract" />
      <h3>Report</h3>
      <TextViewer
        text={typeof loaded?.reho_qc_report === "string" ? loaded.reho_qc_report : null}
        emptyText="No report"
      />
    </div>
  );
}
