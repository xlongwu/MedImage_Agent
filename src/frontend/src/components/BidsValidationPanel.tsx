import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, getProjectBidsValidation } from "../api";
import type { BidsValidationIssue, BidsRepairSuggestion, BidsValidationResponse } from "../types";

type Props = {
  baseUrl?: string;
  projectId: string | null;
};

const statusBadge: Record<string, React.CSSProperties> = {
  pass: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  fail: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};

const severityPill: Record<string, React.CSSProperties> = {
  info: { background: "#e3f2fd", color: "#1565c0", borderColor: "rgba(33, 150, 243, 0.28)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  error: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
};

const actionTypePill: Record<string, React.CSSProperties> = {
  rename_suggestion: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  move_suggestion: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  metadata_suggestion: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  missing_file_suggestion: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  manual_review: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
  conversion_required: { background: "#eff6ff", color: "#2450a6", borderColor: "rgba(56, 103, 214, 0.24)" },
};

const pill: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", minHeight: 22, padding: "0 7px",
  border: "1px solid", borderRadius: 999, fontSize: 10, fontWeight: 900,
};

const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace', fontSize: 11, overflowWrap: "anywhere",
};

export default function BidsValidationPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<BidsValidationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestRef = useRef(0);

  useEffect(() => {
    if (!projectId) { setData(null); setError(""); return; }
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoading(true); setError("");
    getProjectBidsValidation(effectiveBase, projectId)
      .then((res) => { if (requestId !== requestRef.current) return; setData(res); })
      .catch((err) => { if (requestId !== requestRef.current) return; setError(err instanceof Error ? err.message : String(err)); })
      .finally(() => { if (requestId === requestRef.current) setLoading(false); });
  }, [effectiveBase, projectId]);

  if (!projectId) return <section style={sectionStyle}><h3 style={h3Style}>BIDS Validation</h3><div className="empty">Select a project.</div></section>;
  if (loading) return <section style={sectionStyle}><h3 style={h3Style}>BIDS Validation</h3><div className="empty">Validating BIDS structure...</div></section>;
  if (error) return <section style={sectionStyle}><h3 style={h3Style}>BIDS Validation</h3><div className="errorBox">{error}</div></section>;
  if (!data) return null;

  return (
    <section style={sectionStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div><h3 style={h3Style}>BIDS Validation</h3><span style={{ color: "#667085", fontSize: 12 }}>Read-only structural checks and repair suggestions.</span></div>
        <span style={{ ...pill, ...statusBadge[data.status] }}>{data.status.toUpperCase()}</span>
      </div>

      <div style={{ padding: 8, border: "1px solid rgba(56, 103, 214, 0.18)", borderRadius: 6, background: "rgba(239, 246, 255, 0.72)", fontSize: 11, color: "#2450a6", marginBottom: 12 }}>
        All suggestions are non-destructive. Rawdata will not be modified. Auto-apply is not available in this version.
      </div>

      {data.status === "fail" && data.nifti_file_count === 0 && (
        <div style={{ padding: 8, border: "1px solid rgba(56, 103, 214, 0.22)", borderRadius: 6, background: "rgba(239, 246, 255, 0.88)", fontSize: 11, color: "#2450a6", marginBottom: 12, lineHeight: 1.5 }}>
          <strong>Note:</strong> This is a raw DICOM dataset, not yet converted to BIDS.
          BIDS validation failure is expected before DICOM-to-NIfTI conversion.
          Run <strong>Conversion Dry-Run</strong> to review the BIDS mapping plan.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: 8, marginBottom: 12 }}>
        <Metric label="roots" value={data.roots.length} />
        <Metric label="subjects" value={data.subject_count} />
        <Metric label="sessions" value={data.session_count} />
        <Metric label="NIfTI files" value={data.nifti_file_count} />
        <Metric label="JSON sidecars" value={data.sidecar_json_count} />
        <Metric label="TSV files" value={data.tsv_file_count} />
      </div>

      {data.errors.length > 0 && <div className="errorBox" style={{ marginBottom: 10 }}>{data.errors.join("\n")}</div>}
      {data.warnings.length > 0 && <WarnList items={data.warnings} />}

      {data.issues.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <h4 style={subH}>Issues ({data.issues.length})</h4>
          <div style={{ display: "grid", gap: 6 }}>
            {data.issues.map((issue, i) => (
              <IssueRow key={`${issue.code}-${i}`} issue={issue} />
            ))}
          </div>
        </div>
      )}

      {data.repair_suggestions.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <h4 style={subH}>Repair Suggestions ({data.repair_suggestions.length})</h4>
          <div style={{ display: "grid", gap: 6 }}>
            {data.repair_suggestions.map((sug, i) => (
              <RepairRow key={`repair-${i}`} suggestion={sug} />
            ))}
          </div>
        </div>
      )}

      {data.next_actions.length > 0 && (
        <div>
          <h4 style={subH}>Next Actions</h4>
          <div style={{ display: "grid", gap: 5 }}>
            {data.next_actions.map((a, i) => <div key={i} style={{ padding: "6px 10px", border: "1px solid rgba(56, 103, 214, 0.22)", borderRadius: 6, background: "rgba(239, 246, 255, 0.82)", color: "#2450a6", fontSize: 12 }}>{i + 1}. {a}</div>)}
          </div>
        </div>
      )}
    </section>
  );
}

function IssueRow({ issue }: { issue: BidsValidationIssue }) {
  return (
    <div style={{ display: "grid", gap: 4, padding: 8, border: "1px solid rgba(137, 150, 171, 0.22)", borderRadius: 6, background: "#fff" }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ ...pill, ...severityPill[issue.severity] }}>{issue.severity}</span>
        <strong style={{ fontSize: 12, overflowWrap: "anywhere" }}>{issue.code}</strong>
        {issue.subject_id && <span style={{ fontSize: 11, color: "#667085" }}>{issue.subject_id}</span>}
        {issue.modality && <span style={{ ...pill, background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" }}>{issue.modality}</span>}
      </div>
      <div style={{ fontSize: 12, color: "#344054" }}>{issue.message}</div>
      {issue.file_path && <div style={mono}>{issue.file_path}</div>}
    </div>
  );
}

function RepairRow({ suggestion }: { suggestion: BidsRepairSuggestion }) {
  return (
    <div style={{ display: "grid", gap: 5, padding: 10, border: "1px solid rgba(137, 150, 171, 0.22)", borderRadius: 6, background: "#fff" }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ ...pill, ...actionTypePill[suggestion.action_type] }}>{suggestion.action_type.replace(/_/g, " ")}</span>
        <strong style={{ fontSize: 12 }}>{suggestion.title}</strong>
        {suggestion.requires_user_review && <span style={{ ...pill, background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" }}>review required</span>}
      </div>
      <div style={{ fontSize: 12, color: "#344054", lineHeight: 1.5 }}>{suggestion.description}</div>
      {suggestion.source_path && <div style={mono}>source: {suggestion.source_path}</div>}
      {suggestion.suggested_path && <div style={mono}>suggested: {suggestion.suggested_path}</div>}
      {suggestion.command_preview && <pre style={{ margin: 0, padding: 6, background: "#f5f5f5", borderRadius: 4, fontSize: 11, overflowWrap: "anywhere" }}>{suggestion.command_preview}</pre>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <div style={{ padding: "8px 10px", border: "1px solid rgba(137, 150, 171, 0.24)", borderRadius: 6, background: "#fff", display: "grid", gap: 2, color: "#667085", fontSize: 11, fontWeight: 850 }}><span>{label}</span><strong>{value}</strong></div>;
}

function WarnList({ items }: { items: string[] }) {
  return (
    <div style={{ marginBottom: 10, padding: 8, border: "1px solid rgba(242, 153, 74, 0.24)", borderRadius: 6, background: "rgba(255, 251, 242, 0.94)", color: "#9a5a15", fontSize: 12 }}>
      {items.slice(0, 5).map((w, i) => <div key={i}>{w}</div>)}
      {items.length > 5 && <div>+{items.length - 5} more</div>}
    </div>
  );
}

const sectionStyle: React.CSSProperties = { padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)", marginTop: 4 };
const h3Style: React.CSSProperties = { margin: "0 0 4px", fontSize: 15 };
const subH: React.CSSProperties = { margin: "0 0 6px", fontSize: 13 };
