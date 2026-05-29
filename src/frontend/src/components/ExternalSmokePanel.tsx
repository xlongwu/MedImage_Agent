import { useEffect, useState } from "react";
import { getExternalSmokeStatus, runExternalSmoke } from "../api";
import { JsonBlock } from "./JsonBlock";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

const DPABI_FUNCTIONS = [
  "y_Smooth",
  "y_Filter",
  "y_RegressOutImgCovariates",
  "y_alff_falff",
  "y_Reho",
  "y_ROItseries",
  "y_FC"
];

export default function ExternalSmokePanel({ baseUrl }: Props) {
  const [target, setTarget] = useState("all");
  const [mode, setMode] = useState("manual_package");
  const [configPath, setConfigPath] = useState("examples/project_config.yaml");
  const [approved, setApproved] = useState(false);
  const [approvedBy, setApprovedBy] = useState("local-user");
  const [dpabiFunction, setDpabiFunction] = useState("y_Smooth");
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void refresh();
  }, [baseUrl]);

  async function refresh() {
    setError("");
    try {
      const payload = await getExternalSmokeStatus(baseUrl);
      setStatus(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function run() {
    setBusy(true);
    setError("");
    try {
      const payload = await runExternalSmoke(baseUrl, {
        target,
        mode,
        config_path: configPath,
        approved,
        approved_by: approvedBy,
        dpabi_function: dpabiFunction
      });
      setResult(payload);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const reportText = String(status?.report_text || "");
  const checklistText = String(status?.checklist_text || "");
  const commandsText = String(status?.commands_text || "");

  return (
    <div>
      {error ? <div className="errorBox">{error}</div> : null}
      <div className="formGrid">
        <label>
          Target
          <select value={target} onChange={(event) => setTarget(event.target.value)}>
            <option value="all">SPM + DPABI</option>
            <option value="spm">SPM</option>
            <option value="dpabi">DPABI</option>
          </select>
        </label>
        <label>
          Mode
          <select value={mode} onChange={(event) => setMode(event.target.value)}>
            <option value="manual_package">Manual package</option>
            <option value="preflight">Preflight</option>
            <option value="approved_smoke">Approved smoke</option>
          </select>
        </label>
        <label>
          Config path
          <input value={configPath} onChange={(event) => setConfigPath(event.target.value)} />
        </label>
        <label>
          DPABI function
          <select value={dpabiFunction} onChange={(event) => setDpabiFunction(event.target.value)}>
            {DPABI_FUNCTIONS.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Approved by
          <input value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} />
        </label>
      </div>
      <div className="row">
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={approved}
            onChange={(event) => setApproved(event.target.checked)}
          />
          Approve MATLAB smoke
        </label>
        <button onClick={run} disabled={busy}>{busy ? "Running..." : "Run external smoke"}</button>
        <button onClick={refresh} disabled={busy}>Refresh status</button>
      </div>
      <h3>Latest status</h3>
      <JsonBlock value={status} emptyText="No external smoke status" />
      <h3>Last run result</h3>
      <JsonBlock value={result} emptyText="No run in this session" />
      <h3>Checklist</h3>
      <TextViewer text={checklistText || "No checklist generated"} />
      <h3>Commands</h3>
      <TextViewer text={commandsText || "No commands generated"} />
      <h3>Diagnostic report</h3>
      <TextViewer text={reportText || "No diagnostic report generated"} />
    </div>
  );
}
