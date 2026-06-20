import React, { useState } from "react";
import { getAdvisorStatus, runAdvisor as runAdvisorRequest } from "../lib/api/advisor";
import type { AdvisorResult, AdvisorStatus } from "../lib/api/advisor";

interface Props {
  baseUrl: string;
}

export default function AdvisorCenterPanel({ baseUrl }: Props) {
  const [advisorType, setAdvisorType] = useState("protocol");
  const [inputJson, setInputJson] = useState("{}");
  const [result, setResult] = useState<AdvisorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<AdvisorStatus | null>(null);

  async function loadStatus() {
    try {
      setStatus(await getAdvisorStatus(baseUrl));
    } catch (e) {
      console.error(e);
    }
  }

  React.useEffect(() => {
    loadStatus();
  }, []);

  const presets: Record<string, string> = {
    protocol:
      '{"modality":"rs-fMRI","task_goal":"standard preprocessing","tr":2.0,"slice_count":32,"available_data":["T1w","BOLD"],"constraints":[]}',
    error:
      '{"error_message":"NIfTI read error: corrupted header","node_id":"temporal_filtering","backend":"python","error_category":"nifti_io_error","subject_id":"sub-003"}',
    "qc-report": '{"subjects_total":120,"subjects_passed":108,"qc_data":{"mean_fd":0.15}}',
    parameters: '{"parameters":{"tr":2.0,"filter_band":[0.01,0.08],"smoothing_fwhm":[6,6,6]}}',
    "docs-qa":
      '{"question":"What rs-fMRI preprocessing pipelines are available?","context_docs":["README.md"]}',
  };

  async function runAdvisor() {
    setLoading(true);
    try {
      const body = JSON.parse(inputJson);
      setResult(await runAdvisorRequest(baseUrl, advisorType, body));
    } catch (error) {
      setResult({ error: error instanceof Error ? error.message : String(error) });
    }
    setLoading(false);
  }

  function loadPreset() {
    setInputJson(presets[advisorType] || "{}");
  }

  const flags = result
    ? [
        "advice_only",
        "requires_human_confirmation",
        "will_execute_pipeline",
        "will_modify_data",
        "clinical_conclusion",
      ]
    : [];

  return (
    <div style={{ padding: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2>Advisor Center</h2>
        <div style={{ fontSize: 13, color: "#666" }}>
          LLM:{" "}
          {status?.llm_enabled ? (
            <span style={{ color: "green" }}>
              Enabled ({status?.config?.provider}/{status?.config?.model})
            </span>
          ) : (
            <span style={{ color: "#ff9800" }}>Disabled (deterministic mode)</span>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {["protocol", "error", "qc-report", "parameters", "docs-qa"].map((t) => (
          <button
            key={t}
            onClick={() => setAdvisorType(t)}
            style={{
              ...tabStyle,
              background: advisorType === t ? "#2196f3" : "#e0e0e0",
              color: advisorType === t ? "#fff" : "#333",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <h3>Input</h3>
            <button onClick={loadPreset} style={smallBtn}>
              Load Preset
            </button>
          </div>
          <textarea
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            style={{
              width: "100%",
              height: 200,
              fontFamily: "monospace",
              fontSize: 12,
              padding: 8,
              borderRadius: 4,
              border: "1px solid #ccc",
            }}
          />
          <button onClick={runAdvisor} disabled={loading} style={{ ...btnStyle, marginTop: 8 }}>
            {loading ? "Running..." : `Ask ${advisorType} Advisor`}
          </button>
        </div>

        <div>
          <h3>Response</h3>

          {result && flags.length > 0 && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
              {flags.map((f) => (
                <span
                  key={f}
                  style={{
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    background: result[f] ? "#e8f5e9" : "#fff3e0",
                    color: result[f] ? "#2e7d32" : "#e65100",
                  }}
                >
                  {f}: {String(result[f])}
                </span>
              ))}
            </div>
          )}

          {result?.fallback && (
            <div
              style={{
                padding: 8,
                marginBottom: 8,
                background: "#fff3e0",
                borderRadius: 4,
                fontSize: 13,
              }}
            >
              Deterministic fallback mode (LLM not configured)
            </div>
          )}

          <pre
            style={{
              background: "#f5f5f5",
              padding: 12,
              borderRadius: 4,
              overflow: "auto",
              maxHeight: 400,
              fontSize: 12,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {result ? JSON.stringify(result, null, 2) : "No result yet"}
          </pre>
        </div>
      </div>
    </div>
  );
}

const tabStyle: React.CSSProperties = {
  padding: "6px 14px",
  border: "none",
  borderRadius: 16,
  cursor: "pointer",
  fontWeight: 500,
  fontSize: 13,
};
const btnStyle: React.CSSProperties = {
  padding: "8px 20px",
  border: "none",
  borderRadius: 4,
  background: "#2196f3",
  color: "white",
  cursor: "pointer",
  fontWeight: 600,
  width: "100%",
};
const smallBtn: React.CSSProperties = {
  padding: "4px 12px",
  border: "1px solid #ccc",
  borderRadius: 4,
  background: "#f5f5f5",
  cursor: "pointer",
  fontSize: 12,
};
