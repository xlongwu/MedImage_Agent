import React, { useState } from "react";
import { DEFAULT_API_BASE } from "../../api";
import type { WorkflowState, WorkflowAction } from "../../state/workflowTypes";

interface Props {
  state: WorkflowState;
  dispatch: React.Dispatch<WorkflowAction>;
}

export function DataUploadStep({ state, dispatch }: Props) {
  const [pathInput, setPathInput] = useState(state.datasetPath || "");
  const [inspecting, setInspecting] = useState(false);
  const [inspectResult, setInspectResult] = useState<any>(null);

  const selectSource = (sourceType: "upload" | "directory" | "demo") => {
    if (sourceType === "demo") {
      dispatch({ type: "SET_DATA_SOURCE", sourceType: "demo", path: "examples/synthetic_bids/rawdata" });
    } else {
      dispatch({ type: "SET_DATA_SOURCE", sourceType, path: pathInput });
    }
  };

  const runInspection = async () => {
    setInspecting(true);
    try {
      const path = state.dataSource === "demo" ? "examples/synthetic_bids/rawdata" : state.datasetPath;
      const res = await fetch(`${DEFAULT_API_BASE}/api/real-data/inventory`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rawdata_path: path }),
      });
      setInspectResult(await res.json());
    } catch (e: any) {
      setInspectResult({ error: e.message });
    }
    setInspecting(false);
  };

  return (
    <div>
      <h2>Step 1: Select Data Source</h2>

      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        {[
          { key: "demo", label: "Use Demo Data", desc: "Synthetic BIDS dataset, no MATLAB required" },
          { key: "directory", label: "Local Directory", desc: "Path to BIDS / DICOM / NIfTI data on server" },
        ].map((opt) => (
          <div
            key={opt.key}
            onClick={() => selectSource(opt.key as any)}
            style={{
              flex: 1, padding: 20, borderRadius: 8, cursor: "pointer", border: "2px solid",
              borderColor: state.dataSource === opt.key ? "#1976d2" : "#e0e0e0",
              background: state.dataSource === opt.key ? "#e3f2fd" : "#fff",
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 4 }}>{opt.label}</div>
            <div style={{ fontSize: 13, color: "#777" }}>{opt.desc}</div>
          </div>
        ))}
      </div>

      {state.dataSource === "directory" && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontWeight: 600, fontSize: 14 }}>Data Path:</label>
          <input
            type="text"
            value={pathInput}
            onChange={(e) => { setPathInput(e.target.value); dispatch({ type: "SET_DATA_SOURCE", sourceType: "directory", path: e.target.value }); }}
            placeholder="e.g., data/DemoData or examples/synthetic_bids/rawdata"
            style={{ width: "100%", padding: "8px 12px", marginTop: 4, borderRadius: 4, border: "1px solid #ccc", fontSize: 14 }}
          />
        </div>
      )}

      {state.dataSource !== "none" && (
        <div style={{ marginBottom: 16 }}>
          <button onClick={runInspection} disabled={inspecting} style={btnSecondary}>
            {inspecting ? "Inspecting..." : "Inspect Data"}
          </button>
        </div>
      )}

      {inspectResult && inspectResult.ok === false && !inspectResult.error && (
        <div style={{ padding: 12, background: "#fff3e0", borderRadius: 4, marginBottom: 16, fontSize: 13, color: "#e65100" }}>
          <strong>No data found:</strong> {inspectResult.errors?.join("; ") || "Unknown reason"}
          <br/><span style={{ fontSize: 12 }}>Available: <code>examples/synthetic_bids/rawdata</code> (synthetic BIDS)</span>
        </div>
      )}

      {inspectResult && inspectResult.ok !== false && !inspectResult.error && (
        <div style={{ padding: 16, background: "#e8f5e9", borderRadius: 8, marginBottom: 16 }}>
          <div style={{ fontWeight: 700, color: "#2e7d32", marginBottom: 8 }}>Data Inspection Result</div>
          <div style={{ fontSize: 14, lineHeight: 1.8 }}>
            Format: <strong>{inspectResult.format || "Unknown"}</strong><br/>
            Subjects: <strong>{inspectResult.completeness?.subjects_total ?? inspectResult.summary?.total_subjects ?? "?"}</strong>
            {" | "}T1w: <strong>{inspectResult.completeness?.has_t1w ?? "?"}</strong>
            {" | "}BOLD: <strong>{inspectResult.completeness?.has_bold ?? "?"}</strong>
            {inspectResult.subjects?.[0]?.tr && (
              <>{" | "}TR: <strong>{inspectResult.subjects[0].tr}s</strong></>
            )}
            {inspectResult.subjects?.[0]?.manufacturer && (
              <><br/>Scanner: <strong>{inspectResult.subjects[0].manufacturer} {inspectResult.subjects[0].model}</strong></>
            )}
            {inspectResult.subjects?.[0]?.matrix && (
              <>{" | "}Matrix: <strong>{inspectResult.subjects[0].matrix}</strong></>
            )}
            {inspectResult.subjects?.[0]?.field_strength_t && (
              <>{" | "}Field: <strong>{inspectResult.subjects[0].field_strength_t}T</strong></>
            )}
            {inspectResult.subjects?.[0]?.bold_count && (
              <><br/>BOLD volumes: <strong>{inspectResult.subjects[0].bold_count}</strong></>
            )}
            {inspectResult.subjects?.[0]?.t1_count && (
              <>{" | "}T1 slices: <strong>{inspectResult.subjects[0].t1_count}</strong></>
            )}
            {" | "}Completeness: <strong style={{ color: (inspectResult.completeness?.t1_ratio || 0) >= 100 ? "#2e7d32" : "#ff9800" }}>
              {inspectResult.completeness?.t1_ratio ?? inspectResult.completeness?.has_t1w ? 100 : 0}%
            </strong>
          </div>
        </div>
      )}

      {inspectResult?.error && (
        <div style={{ padding: 12, background: "#fff3e0", borderRadius: 4, marginBottom: 16, fontSize: 13, color: "#e65100" }}>
          Could not connect: {inspectResult.error}. Backend may not be running.<br/>
          Start with: <code>python -m uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000</code>
        </div>
      )}

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 0 })} style={btnBack}>Back</button>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 2 })} disabled={state.dataSource === "none"} style={btnNext}>
          Next: Preprocessing
        </button>
      </div>
    </div>
  );
}

const btnNext: React.CSSProperties = { padding: "8px 20px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 };
const btnBack: React.CSSProperties = { padding: "8px 20px", background: "#f5f5f5", border: "1px solid #ccc", borderRadius: 4, cursor: "pointer" };
const btnSecondary: React.CSSProperties = { padding: "8px 20px", background: "#4caf50", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 };
