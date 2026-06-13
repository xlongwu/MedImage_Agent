import React from "react";
import type { WorkflowState, WorkflowAction, PreprocessingConfig } from "../../state/workflowTypes";

interface Props { state: WorkflowState; dispatch: React.Dispatch<WorkflowAction>; }

const steps: { key: keyof PreprocessingConfig; label: string; desc: string }[] = [
  { key: "sliceTiming", label: "Slice Timing Correction", desc: "Correct interleaved slice acquisition timing" },
  { key: "realignment", label: "Realignment", desc: "Motion correction with 6-parameter rigid body" },
  { key: "coregistration", label: "Coregistration", desc: "Align T1 anatomical to functional space" },
  { key: "segmentation", label: "Segmentation", desc: "Segment GM, WM, and CSF tissue classes" },
  { key: "normalization", label: "Normalization", desc: "Warp to MNI standard space" },
  { key: "smoothing", label: "Smoothing", desc: "Gaussian spatial smoothing" },
  { key: "nuisanceRegression", label: "Nuisance Regression", desc: "Regress out motion and physiological noise" },
  { key: "temporalFiltering", label: "Temporal Filtering", desc: "Bandpass filter to resting-state frequencies" },
];

export function PreprocessingConfigStep({ state, dispatch }: Props) {
  const toggle = (key: keyof PreprocessingConfig) => {
    const step = state.preprocessing[key];
    dispatch({
      type: "SET_PREPROCESSING",
      config: { [key]: { ...step, enabled: !step.enabled } } as Partial<PreprocessingConfig>,
    });
  };

  return (
    <div>
      <h2>Step 2: Preprocessing Configuration</h2>
      <p style={{ color: "#666", marginBottom: 16 }}>Select preprocessing steps. Default settings are recommended for rs-fMRI.</p>

      {steps.map((item) => {
        const cfg = state.preprocessing[item.key];
        const enabled = cfg.enabled;
        return (
          <div key={item.key} onClick={() => toggle(item.key)} style={{
            display: "flex", alignItems: "center", padding: "12px 16px", marginBottom: 8, cursor: "pointer",
            border: "1px solid", borderColor: enabled ? "#c8e6c9" : "#eee",
            borderRadius: 6, background: enabled ? "#f1f8e9" : "#fafafa",
            opacity: enabled ? 1 : 0.5,
          }}>
            <div style={{
              width: 22, height: 22, borderRadius: 4, marginRight: 12, flexShrink: 0,
              background: enabled ? "#4caf50" : "#e0e0e0", color: "#fff",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700,
            }}>
              {enabled ? "✓" : ""}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{item.label}</div>
              <div style={{ fontSize: 12, color: "#888" }}>{item.desc}</div>
            </div>
          </div>
        );
      })}

      <div style={{ marginTop: 16, padding: 12, background: "#f5f5f5", borderRadius: 6 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Key Parameters</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
          <div>TR: <strong>{state.preprocessing.sliceTiming.tr || "auto-detect"}</strong></div>
          <div>Reference Slice: <strong>{state.preprocessing.sliceTiming.referenceSlice}</strong></div>
          <div>Smoothing FWHM: <strong>{state.preprocessing.smoothing.fwhm.join("×")} mm</strong></div>
          <div>Filter Band: <strong>{state.preprocessing.temporalFiltering.lowHz}-{state.preprocessing.temporalFiltering.highHz} Hz</strong></div>
          <div>Nuisance Model: <strong>{state.preprocessing.nuisanceRegression.model}</strong></div>
          <div>Normalize Voxel: <strong>{state.preprocessing.normalization.voxelSize.join("×")} mm</strong></div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 1 })} style={btnBack}>Back</button>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 3 })} style={btnNext}>Next: Analysis</button>
      </div>
    </div>
  );
}

const btnNext: React.CSSProperties = { padding: "8px 20px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 };
const btnBack: React.CSSProperties = { padding: "8px 20px", background: "#f5f5f5", border: "1px solid #ccc", borderRadius: 4, cursor: "pointer" };
