import { useState } from "react";
import { getRsfmriNuisanceRegression, runRsfmriNuisanceRegression } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = { baseUrl: string };

export function RsfmriNuisanceRegressionPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm("Confirm to run Python Nuisance Regression? This only processes synthetic derivatives and will not modify rawdata or execute DPABI.");
    if (!confirmed) return;
    setStatus("RUNNING"); setError("");
    try {
      const r = await runRsfmriNuisanceRegression(baseUrl, { project_config_path: "examples/project_config_dataset.yaml", pipeline_path: "examples/pipeline_rsfmri_nuisance_regression.yaml", approved: true });
      setResult(r); setStatus("SUCCESS");
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); setStatus("ERROR"); }
  }

  async function handleLoad() {
    setStatus("LOADING"); setError("");
    try {
      const r = await getRsfmriNuisanceRegression(baseUrl);
      setLoaded(r); setStatus("LOADED");
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); setStatus("ERROR"); }
  }

  const s = loaded?.nuisance_regression_qc_summary as Record<string, unknown> | undefined;

  return (<div>
    <div className="row">
      <button className="dangerButton" onClick={handleRun}>Approve and Run Python Nuisance Regression</button>
      <button onClick={handleLoad}>Load Nuisance Regression Results</button>
      <StatusBadge status={status} />
    </div>
    {error ? <div className="errorBox">{error}</div> : null}
    <div className="metricGrid">
      <div className="metricCard"><span>Subjects</span><strong>{String(s?.subjects_total ?? "-")}</strong></div>
      <div className="metricCard"><span>PASS</span><strong>{String(s?.subjects_pass ?? "-")}</strong></div>
      <div className="metricCard"><span>WARNING</span><strong>{String(s?.subjects_warning ?? "-")}</strong></div>
      <div className="metricCard"><span>FAIL</span><strong>{String(s?.subjects_fail ?? "-")}</strong></div>
      <div className="metricCard"><span>Mean Variance Ratio</span><strong>{s?.mean_variance_ratio == null ? "-" : Number(s.mean_variance_ratio).toFixed(4)}</strong></div>
    </div>
    <h3>Run Summary</h3><JsonBlock value={result} emptyText="Not yet run" />
    <h3>Nuisance Regression QC Summary</h3><JsonBlock value={loaded?.nuisance_regression_qc_summary} emptyText="No nuisance regression QC summary available" />
    <h3>Subject Nuisance Regression QC</h3><JsonBlock value={loaded?.subject_nuisance_regression_qc} emptyText="No subject nuisance regression QC available" />
    <h3>Subject Confound QC</h3><JsonBlock value={loaded?.subject_confound_qc} emptyText="No subject confound QC available" />
    <h3>DPABI Backend Contract</h3><JsonBlock value={loaded?.dpabi_backend_contract} emptyText="No DPABI backend contract available" />
    <h3>Nuisance Regression QC Report</h3><TextViewer text={typeof loaded?.nuisance_regression_qc_report === "string" ? loaded.nuisance_regression_qc_report : null} emptyText="No nuisance regression QC report available" />
  </div>);
}
