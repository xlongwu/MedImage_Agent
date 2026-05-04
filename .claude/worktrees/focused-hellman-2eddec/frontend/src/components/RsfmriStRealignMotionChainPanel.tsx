import { useState } from "react";
import {
  getRsfmriStRealignMotionQc,
  runRsfmriStRealignMotionQc
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriStRealignMotionChainPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "Confirm to run Slice Timing → Realignment → Motion QC chain pipeline? This only processes synthetic BIDS data and will not modify rawdata."
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriStRealignMotionQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_st_realign_motion_qc.yaml",
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
      const response = await getRsfmriStRealignMotionQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const chainSummary = loaded?.chain_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          Approve and Run ST → Realign → Motion QC
        </button>
        <button onClick={handleLoad}>Load Chain Results</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(chainSummary?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(chainSummary?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>WARNING</span>
          <strong>{String(chainSummary?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>FAIL</span>
          <strong>{String(chainSummary?.subjects_fail ?? "-")}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="Not yet run" />

      <h3>Chain Summary</h3>
      <JsonBlock value={loaded?.chain_summary} emptyText="No chain summary available" />

      <h3>Slice Timing Summary</h3>
      <JsonBlock value={loaded?.slice_timing_qc_summary} emptyText="No slice timing summary available" />

      <h3>Motion QC Summary</h3>
      <JsonBlock value={loaded?.motion_qc_summary} emptyText="No motion QC summary available" />

      <h3>Subject Slice Timing QC</h3>
      <JsonBlock value={loaded?.subject_slice_timing_qc} emptyText="No subject slice timing QC available" />

      <h3>Subject Motion QC</h3>
      <JsonBlock value={loaded?.subject_motion_qc} emptyText="No subject motion QC available" />

      <h3>Chain Report</h3>
      <TextViewer
        text={
          typeof loaded?.chain_report === "string"
            ? loaded.chain_report
            : null
        }
        emptyText="No chain report available"
      />
    </div>
  );
}
