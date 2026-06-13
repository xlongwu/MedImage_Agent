import { useState } from "react";
import {
  getRsfmriCoregistrationQc,
  runRsfmriCoregistrationQc
} from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriCoregistrationQcPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "Confirm to run SPM Coregistration + Registration QC? This only processes synthetic BIDS data and will not modify rawdata."
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriCoregistrationQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_coregistration_qc.yaml",
        approved: true
      });
      setResult(response);
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
      const response = await getRsfmriCoregistrationQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.registration_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          Approve and Run Coregistration + Registration QC
        </button>
        <button onClick={handleLoad}>Load Registration QC Results</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(summary?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(summary?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>WARNING</span>
          <strong>{String(summary?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>FAIL</span>
          <strong>{String(summary?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Mean Center Distance</span>
          <strong>
            {summary?.mean_center_distance_mm == null
              ? "-"
              : Number(summary.mean_center_distance_mm).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="Not yet run" />

      <h3>Registration QC Summary</h3>
      <JsonBlock value={loaded?.registration_qc_summary} emptyText="No registration QC summary available" />

      <h3>Subject Registration QC</h3>
      <JsonBlock value={loaded?.subject_registration_qc} emptyText="No subject registration QC available" />

      <h3>Registration QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.registration_qc_report === "string"
            ? loaded.registration_qc_report
            : null
        }
        emptyText="No registration QC report available"
      />
    </div>
  );
}
