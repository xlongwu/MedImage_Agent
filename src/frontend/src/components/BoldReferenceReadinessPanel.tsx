import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, getProjectBoldReferenceReadiness } from "../lib/api/legacy";
import type { BoldReferenceCandidate, BoldReferenceReadinessResponse } from "../types";

type Props = { baseUrl?: string; projectId: string | null };

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};
const pill: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 22,
  padding: "0 7px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 10,
  fontWeight: 900,
};
const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

export default function BoldReferenceReadinessPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<BoldReferenceReadinessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const reqRef = useRef(0);

  useEffect(() => {
    if (!projectId) {
      setData(null);
      return;
    }
    const id = reqRef.current + 1;
    reqRef.current = id;
    setLoading(true);
    setError("");
    getProjectBoldReferenceReadiness(effectiveBase, projectId)
      .then((r) => {
        if (id === reqRef.current) setData(r);
      })
      .catch((e) => {
        if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (id === reqRef.current) setLoading(false);
      });
  }, [effectiveBase, projectId]);

  if (!projectId)
    return (
      <Sec>
        <H3>BOLD Reference Readiness</H3>
        <div className="empty">Select a project.</div>
      </Sec>
    );
  if (loading)
    return (
      <Sec>
        <H3>BOLD Reference Readiness</H3>
        <div className="empty">Inspecting...</div>
      </Sec>
    );
  if (error)
    return (
      <Sec>
        <H3>BOLD Reference Readiness</H3>
        <div className="errorBox">{error}</div>
      </Sec>
    );
  if (!data) return null;

  return (
    <Sec>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10,
          marginBottom: 12,
        }}
      >
        <div>
          <H3>BOLD Reference Readiness</H3>
          <Sub>Inspect BOLD NIfTI files and propose reference strategy.</Sub>
        </div>
        <span style={{ ...pill, ...statusBadge[data.status] }}>{data.status.toUpperCase()}</span>
      </div>
      <div
        style={{
          padding: 8,
          border: "1px solid rgba(242, 153, 74, 0.28)",
          borderRadius: 6,
          background: "rgba(255, 251, 242, 0.94)",
          fontSize: 11,
          color: "#9a5a15",
          marginBottom: 12,
        }}
      >
        Read-only planning. No reference image is computed or written.
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(80px, 1fr))",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <M label="total" value={data.candidate_count} />
        <M label="ready" value={data.ready_count} />
        <M label="warning" value={data.warning_count} />
        <M label="blocked" value={data.blocked_count} />
      </div>

      {data.safety_flags && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
          {Object.entries(data.safety_flags).map(([k, v]) => (
            <span
              key={k}
              style={{
                ...pill,
                background: v ? "#e8f5e9" : "#ffebee",
                color: v ? "#176b3b" : "#b53b3b",
                borderColor: v ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)",
              }}
            >
              {k}: {String(v)}
            </span>
          ))}
        </div>
      )}

      {data.candidates.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>BOLD Candidates</h4>
          <div style={{ display: "grid", gap: 6 }}>
            {data.candidates.map((c, i) => (
              <CandidateRow key={i} candidate={c} />
            ))}
          </div>
        </div>
      )}

      {data.warnings.length > 0 && <Warn items={data.warnings} />}
      {data.errors.length > 0 && (
        <div className="errorBox" style={{ marginBottom: 10 }}>
          {data.errors.join("\n")}
        </div>
      )}

      {data.next_actions.length > 0 && (
        <div>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Next Actions</h4>
          <div style={{ display: "grid", gap: 5 }}>
            {data.next_actions.map((a, i) => (
              <div
                key={i}
                style={{
                  padding: "6px 10px",
                  border: "1px solid rgba(56, 103, 214, 0.22)",
                  borderRadius: 6,
                  background: "rgba(239, 246, 255, 0.82)",
                  color: "#2450a6",
                  fontSize: 12,
                }}
              >
                {i + 1}. {a}
              </div>
            ))}
          </div>
        </div>
      )}
    </Sec>
  );
}

function CandidateRow({ candidate }: { candidate: BoldReferenceCandidate }) {
  return (
    <div
      style={{
        display: "grid",
        gap: 4,
        padding: 8,
        border: "1px solid rgba(137, 150, 171, 0.22)",
        borderRadius: 6,
        background: "#fff",
      }}
    >
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        {candidate.subject_id && (
          <span style={{ fontSize: 12, fontWeight: 700 }}>{candidate.subject_id}</span>
        )}
        <span
          style={{
            ...pill,
            background: candidate.is_4d ? "#e8f5e9" : "#fff7ed",
            color: candidate.is_4d ? "#176b3b" : "#9a5a15",
            borderColor: candidate.is_4d ? "rgba(33, 150, 83, 0.24)" : "rgba(242, 153, 74, 0.28)",
          }}
        >
          {candidate.is_4d ? "4D" : "3D"}
        </span>
        <span style={{ fontSize: 11, color: "#667085" }}>
          {candidate.volume_count ?? "?"} vol(s)
        </span>
        {candidate.dimensions.length > 0 && (
          <span style={{ fontSize: 11, color: "#667085" }}>{candidate.dimensions.join("×")}</span>
        )}
        <span
          style={{
            ...pill,
            background: candidate.has_sidecar ? "#e8f5e9" : "#ffebee",
            color: candidate.has_sidecar ? "#176b3b" : "#b53b3b",
            borderColor: candidate.has_sidecar
              ? "rgba(33, 150, 83, 0.24)"
              : "rgba(235, 87, 87, 0.26)",
          }}
        >
          sidecar: {String(candidate.has_sidecar)}
        </span>
        <span
          style={{
            ...pill,
            background: candidate.reference_strategy === "manual_required" ? "#ffebee" : "#e8f5e9",
            color: candidate.reference_strategy === "manual_required" ? "#b53b3b" : "#176b3b",
            borderColor:
              candidate.reference_strategy === "manual_required"
                ? "rgba(235, 87, 87, 0.26)"
                : "rgba(33, 150, 83, 0.24)",
          }}
        >
          {candidate.reference_strategy.replace(/_/g, " ")}
        </span>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
          gap: "2px 8px",
          fontSize: 11,
          color: "#667085",
        }}
      >
        {candidate.repetition_time != null && (
          <div>
            <span>TR: </span>
            <b>{candidate.repetition_time}s</b>
          </div>
        )}
        {candidate.task_name && (
          <div>
            <span>Task: </span>
            <b>{candidate.task_name}</b>
          </div>
        )}
        {candidate.has_slice_timing && (
          <div>
            <b>SliceTiming ✓</b>
          </div>
        )}
        {candidate.phase_encoding_direction && (
          <div>
            <span>PE: </span>
            <b>{candidate.phase_encoding_direction}</b>
          </div>
        )}
      </div>
      <div style={mono}>{candidate.bold_path}</div>
      {candidate.warnings.length > 0 && <Warn items={candidate.warnings} />}
    </div>
  );
}

function Warn({ items }: { items: string[] }) {
  return (
    <div
      style={{
        padding: 6,
        border: "1px solid rgba(242, 153, 74, 0.24)",
        borderRadius: 4,
        background: "rgba(255, 251, 242, 0.94)",
        color: "#9a5a15",
        fontSize: 11,
      }}
    >
      {items.slice(0, 3).map((w, i) => (
        <div key={i}>{w}</div>
      ))}
    </div>
  );
}
function M({ label, value }: { label: string; value: number }) {
  return (
    <div
      style={{
        padding: "8px 10px",
        border: "1px solid rgba(137, 150, 171, 0.24)",
        borderRadius: 6,
        background: "#fff",
        display: "grid",
        gap: 2,
        color: "#667085",
        fontSize: 11,
        fontWeight: 850,
      }}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <section
    style={{
      padding: 16,
      border: "1px solid rgba(137, 150, 171, 0.28)",
      borderRadius: 8,
      background: "rgba(255, 255, 255, 0.88)",
      marginTop: 4,
    }}
  >
    {children}
  </section>
);
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>
);
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>
);
