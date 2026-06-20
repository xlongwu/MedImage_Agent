import { useState } from "react";
import {
  getLatestRsfmriReportExport,
  listRsfmriReportExports,
  runRsfmriReportExport,
} from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
export function RsfmriReportExporterPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [list, setList] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");
  async function handleRun() {
    setStatus("RUNNING");
    setError("");
    try {
      setResult(
        await runRsfmriReportExport(baseUrl, {
          project_config_path: "examples/project_config_dataset.yaml",
          pipeline_path: "examples/pipeline_rsfmri_report_exporter.yaml",
        }),
      );
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  async function loadLatest() {
    setStatus("LOADING");
    setError("");
    try {
      setLatest(await getLatestRsfmriReportExport(baseUrl));
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  async function loadList() {
    setStatus("LOADING");
    setError("");
    try {
      setList(await listRsfmriReportExports(baseUrl));
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  const es = latest?.export_summary as Record<string, unknown> | undefined;
  const m = latest?.manifest as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>Generate Report Package</button>
        <button onClick={loadLatest}>Load Latest</button>
        <button onClick={loadList}>List Exports</button>
        <StatusBadge status={status} />
      </div>
      {error ? <div className="errorBox">{error}</div> : null}
      <div className="metricGrid">
        <div className="metricCard">
          <span>Export ID</span>
          <strong>{String(latest?.export_id ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(es?.exported_subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Files</span>
          <strong>{String(es?.exported_files_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>ZIP Size</span>
          <strong>{String(es?.zip_size_bytes ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Manifest Files</span>
          <strong>{Array.isArray(m?.files) ? m.files.length : "-"}</strong>
        </div>
      </div>
      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="Not yet run" />
      <h3>Export Summary</h3>
      <JsonBlock value={latest?.export_summary} emptyText="No summary" />
      <h3>Manifest</h3>
      <JsonBlock value={latest?.manifest} emptyText="No manifest" />
      <h3>Paths</h3>
      <JsonBlock
        value={{ zip_path: latest?.zip_path, package_dir: latest?.package_dir }}
        emptyText="No paths"
      />
      <h3>README</h3>
      <TextViewer
        text={typeof latest?.readme_md === "string" ? latest.readme_md : null}
        emptyText="No README"
      />
      <h3>Index</h3>
      <TextViewer
        text={typeof latest?.index_md === "string" ? latest.index_md : null}
        emptyText="No index"
      />
      <h3>Export List</h3>
      <JsonBlock value={list} emptyText="No exports" />
    </div>
  );
}
