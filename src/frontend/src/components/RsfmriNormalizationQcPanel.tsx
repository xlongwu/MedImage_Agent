import { useState } from "react";
import {
  getRsfmriNormalizationQc,
  runRsfmriNormalizationQc
} from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriNormalizationQcPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "Confirm to run SPM Normalization + Normalization QC? This only processes synthetic BIDS data and will not modify rawdata."
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriNormalizationQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_normalization_qc.yaml",
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
      const response = await getRsfmriNormalizationQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.normalization_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          Approve and Run Normalization + Normalization QC
        </button>
        <button onClick={handleLoad}>Load Normalization QC Results</button>
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
          <span>Mean Finite Fraction</span>
          <strong>
            {summary?.mean_finite_fraction == null
              ? "-"
              : Number(summary.mean_finite_fraction).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="Not yet run" />

      <h3>Normalization QC Summary</h3>
      <JsonBlock value={loaded?.normalization_qc_summary} emptyText="No normalization QC summary available" />

      <h3>Subject Normalization QC</h3>
      <JsonBlock value={loaded?.subject_normalization_qc} emptyText="No subject normalization QC available" />

      <h3>Normalization QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.normalization_qc_report === "string"
            ? loaded.normalization_qc_report
            : null
        }
        emptyText="No normalization QC report available"
      />
    </div>
  );
}
