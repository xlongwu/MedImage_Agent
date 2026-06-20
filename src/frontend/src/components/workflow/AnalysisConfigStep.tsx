import React from "react";
import type { WorkflowState, WorkflowAction, AnalysisConfig } from "../../state/workflowTypes";

interface Props {
  state: WorkflowState;
  dispatch: React.Dispatch<WorkflowAction>;
}

const items: {
  key: keyof AnalysisConfig;
  label: string;
  desc: string;
  dependsOn: keyof AnalysisConfig | null;
}[] = [
  {
    key: "enabled",
    label: "Run Post-Processing Analysis",
    desc: "Only preprocessing without derived metrics",
    dependsOn: null,
  },
  {
    key: "alffFalff",
    label: "ALFF / fALFF",
    desc: "Amplitude of Low Frequency Fluctuations",
    dependsOn: "enabled",
  },
  {
    key: "reho",
    label: "ReHo",
    desc: "Regional Homogeneity (KCC, neighborhood 27)",
    dependsOn: "enabled",
  },
  {
    key: "functionalConnectivity",
    label: "Functional Connectivity",
    desc: "ROI-based correlation matrix (4 ROIs)",
    dependsOn: "enabled",
  },
  {
    key: "groupSummary",
    label: "Group Summary",
    desc: "Cross-subject aggregate statistics",
    dependsOn: "enabled",
  },
  {
    key: "reportExport",
    label: "Report Export + Validation",
    desc: "Generate ZIP package with checksums",
    dependsOn: "enabled",
  },
];

type AnalysisStepKey = Exclude<keyof AnalysisConfig, "enabled">;

function isAnalysisStepKey(key: keyof AnalysisConfig): key is AnalysisStepKey {
  return key !== "enabled";
}

function analysisEnabled(value: AnalysisConfig[keyof AnalysisConfig]): boolean {
  return typeof value === "boolean" ? value : value.enabled;
}

export function AnalysisConfigStep({ state, dispatch }: Props) {
  const toggle = (key: keyof AnalysisConfig) => {
    if (key === "enabled") {
      dispatch({ type: "SET_ANALYSIS", config: { enabled: !state.analysis.enabled } });
      return;
    }

    if (isAnalysisStepKey(key)) {
      const item = state.analysis[key];
      dispatch({
        type: "SET_ANALYSIS",
        config: { [key]: { ...item, enabled: !item.enabled } } as Partial<AnalysisConfig>,
      });
    }
  };

  return (
    <div>
      <h2>Step 3: Analysis Configuration</h2>
      <p style={{ color: "#666", marginBottom: 16 }}>
        Optional post-processing analysis steps. Skip if you only need preprocessed data.
      </p>

      {items.map((item) => {
        const cfg = state.analysis[item.key];
        const enabled = analysisEnabled(cfg);
        const disabled = item.dependsOn ? !analysisEnabled(state.analysis[item.dependsOn]) : false;
        return (
          <div
            key={item.key}
            onClick={() => !disabled && toggle(item.key)}
            style={{
              display: "flex",
              alignItems: "center",
              padding: "12px 16px",
              marginBottom: 8,
              cursor: disabled ? "not-allowed" : "pointer",
              border: "1px solid",
              borderColor: enabled && !disabled ? "#c8e6c9" : "#eee",
              borderRadius: 6,
              background: enabled && !disabled ? "#f1f8e9" : "#fafafa",
              opacity: disabled ? 0.4 : enabled ? 1 : 0.5,
            }}
          >
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: 4,
                marginRight: 12,
                flexShrink: 0,
                background: enabled && !disabled ? "#4caf50" : "#e0e0e0",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                fontWeight: 700,
              }}
            >
              {enabled && !disabled ? "✓" : ""}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{item.label}</div>
              <div style={{ fontSize: 12, color: "#888" }}>{item.desc}</div>
            </div>
            {item.key === "enabled" && (
              <div style={{ fontSize: 12, color: "#1976d2", fontWeight: 600 }}>Main Toggle</div>
            )}
          </div>
        );
      })}

      {state.analysis.alffFalff.enabled && state.analysis.enabled && (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            background: "#f5f5f5",
            borderRadius: 6,
            fontSize: 13,
          }}
        >
          <strong>ALFF/fALFF:</strong> Band {state.analysis.alffFalff.lowHz}-
          {state.analysis.alffFalff.highHz} Hz
          {" | "}
          <strong>ReHo:</strong> {state.analysis.reho.neighborhood}-voxel neighborhood
          {" | "}
          <strong>FC:</strong> {state.analysis.functionalConnectivity.roiCount} ROIs
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 2 })} style={btnBack}>
          Back
        </button>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 4 })} style={btnNext}>
          Next: Confirm & Run
        </button>
      </div>
    </div>
  );
}

const btnNext: React.CSSProperties = {
  padding: "8px 20px",
  background: "#1976d2",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  cursor: "pointer",
  fontWeight: 600,
};
const btnBack: React.CSSProperties = {
  padding: "8px 20px",
  background: "#f5f5f5",
  border: "1px solid #ccc",
  borderRadius: 4,
  cursor: "pointer",
};
