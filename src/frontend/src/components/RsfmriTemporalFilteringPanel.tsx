import { useState } from "react";
import { getRsfmriTemporalFiltering, runRsfmriTemporalFiltering } from "../api";
import { JsonBlock } from "./JsonBlock"; import { StatusBadge } from "./StatusBadge"; import { TextViewer } from "./TextViewer";

type Props = { baseUrl: string };

export function RsfmriTemporalFilteringPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE"); const [error, setError] = useState("");

  async function handleRun() {
    if (!window.confirm("Confirm to run Python Temporal Filtering? This only processes synthetic derivatives and will not modify rawdata or execute DPABI.")) return;
    setStatus("RUNNING"); setError("");
    try {
      const r = await runRsfmriTemporalFiltering(baseUrl, { project_config_path: "examples/project_config_dataset.yaml", pipeline_path: "examples/pipeline_rsfmri_temporal_filtering.yaml", approved: true });
      setResult(r); setStatus("SUCCESS");
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); setStatus("ERROR"); }
  }
  async function handleLoad() {
    setStatus("LOADING"); setError("");
    try { const r = await getRsfmriTemporalFiltering(baseUrl); setLoaded(r); setStatus("LOADED"); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); setStatus("ERROR"); }
  }

  const s = loaded?.temporal_filtering_qc_summary as Record<string, unknown> | undefined;
  return (<div>
    <div className="row"><button className="dangerButton" onClick={handleRun}>Approve and Run Python Temporal Filtering</button><button onClick={handleLoad}>Load Temporal Filtering Results</button><StatusBadge status={status} /></div>
    {error ? <div className="errorBox">{error}</div> : null}
    <div className="metricGrid">
      <div className="metricCard"><span>Subjects</span><strong>{String(s?.subjects_total ?? "-")}</strong></div>
      <div className="metricCard"><span>PASS</span><strong>{String(s?.subjects_pass ?? "-")}</strong></div>
      <div className="metricCard"><span>WARNING</span><strong>{String(s?.subjects_warning ?? "-")}</strong></div>
      <div className="metricCard"><span>FAIL</span><strong>{String(s?.subjects_fail ?? "-")}</strong></div>
      <div className="metricCard"><span>Mean Variance Ratio</span><strong>{s?.mean_variance_ratio == null ? "-" : Number(s.mean_variance_ratio).toFixed(4)}</strong></div>
    </div>
    <h3>Run Summary</h3><JsonBlock value={result} emptyText="Not yet run" />
    <h3>Temporal Filtering QC Summary</h3><JsonBlock value={loaded?.temporal_filtering_qc_summary} emptyText="No temporal filtering QC summary available" />
    <h3>Subject Temporal Filtering QC</h3><JsonBlock value={loaded?.subject_temporal_filtering_qc} emptyText="No subject temporal filtering QC available" />
    <h3>DPABI Backend Contract</h3><JsonBlock value={loaded?.dpabi_backend_contract} emptyText="No DPABI backend contract available" />
    <h3>Temporal Filtering QC Report</h3><TextViewer text={typeof loaded?.temporal_filtering_qc_report === "string" ? loaded.temporal_filtering_qc_report : null} emptyText="No temporal filtering QC report available" />
  </div>);
}
