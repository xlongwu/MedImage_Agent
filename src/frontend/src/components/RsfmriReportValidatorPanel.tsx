import { useState } from "react";
import { getLatestRsfmriReportValidation, listRsfmriReportValidations, runRsfmriReportValidation } from "../api";
import { JsonBlock } from "./JsonBlock"; import { StatusBadge } from "./StatusBadge"; import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
export function RsfmriReportValidatorPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string,unknown>|null>(null);
  const [latest, setLatest] = useState<Record<string,unknown>|null>(null);
  const [vlist, setVlist] = useState<Record<string,unknown>|null>(null);
  const [status, setStatus] = useState("IDLE"); const [error, setError] = useState("");
  async function handleRun() { setStatus("RUNNING"); try { setResult(await runRsfmriReportValidation(baseUrl,{project_config_path:"examples/project_config_dataset.yaml",pipeline_path:"examples/pipeline_rsfmri_report_validator.yaml"})); setStatus("SUCCESS"); } catch(err) { setError(String(err)); setStatus("ERROR"); } }
  async function loadLatest() { setStatus("LOADING"); try { setLatest(await getLatestRsfmriReportValidation(baseUrl)); setStatus("LOADED"); } catch(err) { setError(String(err)); setStatus("ERROR"); } }
  async function loadList() { setStatus("LOADING"); try { setVlist(await listRsfmriReportValidations(baseUrl)); setStatus("LOADED"); } catch(err) { setError(String(err)); setStatus("ERROR"); } }
  const vr = latest?.validation_result as Record<string,unknown>|undefined; const st = vr?.stats as Record<string,unknown>|undefined;
  return (<div><div className="row"><button onClick={handleRun}>Validate Latest Package</button><button onClick={loadLatest}>Load Latest Validation</button><button onClick={loadList}>List Validations</button><StatusBadge status={status} /></div>{error?<div className="errorBox">{error}</div>:null}
    <div className="metricGrid"><div className="metricCard"><span>Status</span><strong>{String(vr?.validation_status??"-")}</strong></div><div className="metricCard"><span>Checksum Mismatches</span><strong>{String(st?.checksum_mismatch_total??"-")}</strong></div><div className="metricCard"><span>Missing Files</span><strong>{String(st?.missing_files_total??"-")}</strong></div><div className="metricCard"><span>ZIP Test OK</span><strong>{String(st?.zip_test_ok??"-")}</strong></div><div className="metricCard"><span>Safety Violations</span><strong>{String(st?.safety_violations_total??"-")}</strong></div></div>
    <h3>Validation Result</h3><JsonBlock value={latest?.validation_result} emptyText="No result" />
    <h3>Validation Checks</h3><JsonBlock value={vr?.checks} emptyText="No checks" />
    <h3>Validation Report</h3><TextViewer text={typeof latest?.validation_report==="string"?latest.validation_report:null} emptyText="No report" />
    <h3>Validation List</h3><JsonBlock value={vlist} emptyText="No list" />
  </div>);
}
