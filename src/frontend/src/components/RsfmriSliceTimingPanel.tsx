import { useState } from "react";
import { getRsfmriSpmSliceTiming, runRsfmriSpmSliceTiming } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriSliceTimingPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "Confirm to run SPM slice timing correction? This only processes synthetic BIDS data and will not modify rawdata.",
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriSpmSliceTiming(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_spm_slice_timing.yaml",
        approved: true,
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
      const response = await getRsfmriSpmSliceTiming(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.slice_timing_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          Approve and Run SPM Slice Timing
        </button>
        <button onClick={handleLoad}>Load Slice Timing Results</button>
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
          <span>FAIL</span>
          <strong>{String(summary?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Mean TR</span>
          <strong>{summary?.mean_tr == null ? "-" : Number(summary.mean_tr).toFixed(4)}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="Not yet run" />

      <h3>Slice Timing QC Summary</h3>
      <JsonBlock
        value={loaded?.slice_timing_qc_summary}
        emptyText="No slice timing QC summary available"
      />

      <h3>Subject Slice Timing QC</h3>
      <JsonBlock
        value={loaded?.subject_slice_timing_qc}
        emptyText="No subject slice timing QC available"
      />

      <h3>Slice Timing QC Report</h3>
      <TextViewer
        text={
          typeof loaded?.slice_timing_qc_report === "string" ? loaded.slice_timing_qc_report : null
        }
        emptyText="No slice timing QC report available"
      />
    </div>
  );
}
