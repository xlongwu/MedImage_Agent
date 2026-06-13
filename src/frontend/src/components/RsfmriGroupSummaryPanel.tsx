import { useState } from "react";
import { getRsfmriGroupSummary, runRsfmriGroupSummary } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock"; import { StatusBadge } from "./StatusBadge"; import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
function fmt(v: unknown, d=4) { if (v===null||v===undefined) return "-"; const n=Number(v); return Number.isFinite(n)?n.toFixed(d):String(v); }
export function RsfmriGroupSummaryPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string,unknown>|null>(null);
  const [loaded, setLoaded] = useState<Record<string,unknown>|null>(null);
  const [status, setStatus] = useState("IDLE"); const [error, setError] = useState("");
  async function handleRun() { setStatus("RUNNING"); setError(""); try { const r=await runRsfmriGroupSummary(baseUrl,{project_config_path:"examples/project_config_dataset.yaml",pipeline_path:"examples/pipeline_rsfmri_group_summary.yaml"}); setResult(r); setStatus("SUCCESS"); } catch(err) { setError(err instanceof Error?err.message:String(err)); setStatus("ERROR"); } }
  async function handleLoad() { setStatus("LOADING"); setError(""); try { setLoaded(await getRsfmriGroupSummary(baseUrl)); setStatus("LOADED"); } catch(err) { setError(err instanceof Error?err.message:String(err)); setStatus("ERROR"); } }
  const dd=loaded?.dashboard_data as Record<string,unknown>|undefined;
  const cc=dd?.summary_cards as Record<string,unknown>|undefined;
  const mm=dd?.metric_means as Record<string,unknown>|undefined;
  return (<div><div className="row"><button onClick={handleRun}>Generate Group Summary</button><button onClick={handleLoad}>Load Dashboard</button><StatusBadge status={status} /></div>{error?<div className="errorBox">{error}</div>:null}
    <div className="metricGrid"><div className="metricCard"><span>Subjects</span><strong>{String(cc?.subjects_total??"-")}</strong></div><div className="metricCard"><span>With QC</span><strong>{String(cc?.subjects_with_any_qc??"-")}</strong></div><div className="metricCard"><span>Warnings</span><strong>{String(cc?.warnings_total??"-")}</strong></div><div className="metricCard"><span>Errors</span><strong>{String(cc?.errors_total??"-")}</strong></div><div className="metricCard"><span>Contracts</span><strong>{String(cc?.contracts_total??"-")}</strong></div></div>
    <div className="metricGrid"><div className="metricCard"><span>Mean FD</span><strong>{fmt(mm?.mean_fd)}</strong></div><div className="metricCard"><span>Mean fALFF</span><strong>{fmt(mm?.falff_mean)}</strong></div><div className="metricCard"><span>Mean ReHo</span><strong>{fmt(mm?.reho_mean)}</strong></div><div className="metricCard"><span>Mean FC ROI</span><strong>{fmt(mm?.fc_roi_count,2)}</strong></div></div>
    <h3>Run Summary</h3><JsonBlock value={result} emptyText="Not yet run" />
    <h3>Dataset Summary</h3><JsonBlock value={loaded?.dataset_summary} emptyText="No summary" />
    <h3>Dashboard Data</h3><JsonBlock value={loaded?.dashboard_data} emptyText="No dashboard" />
    <h3>Pipeline Completeness</h3><JsonBlock value={loaded?.pipeline_completeness} emptyText="No completeness" />
    <h3>Contracts Overview</h3><JsonBlock value={loaded?.contracts_overview} emptyText="No contracts" />
    <h3>Subject Metrics CSV</h3><JsonBlock value={{path:loaded?.subject_metrics_table_path}} emptyText="No CSV" />
    <h3>Report</h3><TextViewer text={typeof loaded?.dataset_summary_report==="string"?loaded.dataset_summary_report:null} emptyText="No report" />
  </div>);
}
