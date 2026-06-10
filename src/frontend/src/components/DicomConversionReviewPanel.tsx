import { useRef, useState } from "react";
import { DEFAULT_API_BASE, getPreprocessingPlanPreview, getProjectDicomConversionReleaseReadiness, persistProjectDicomConversionPlan, registerConvertedPreprocessingInput, runProjectDicomConversionPreflight } from "../api";
import type {
  Dcm2niixCommandTemplate,
  DicomConversionMapping,
  DicomConversionPlanPersistenceResponse,
  DicomConversionPreflightResponse,
  DicomConversionReleaseReadinessReport,
  DicomConversionSafetyFlags,
  PreprocessingInputRegistrationResponse,
  PreprocessingPlanPreviewResponse,
} from "../types";
import DicomConversionReleaseReadinessPanel from "./DicomConversionReleaseReadinessPanel";
import DicomConversionExecutePanel from "./DicomConversionExecutePanel";

type Props = { baseUrl?: string; projectId: string | null };

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  disabled: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};

const dcm2niixStatusBadge: Record<string, React.CSSProperties> = {
  available: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  missing: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  version_failed: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  disabled: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};

const pill: React.CSSProperties = { display: "inline-flex", alignItems: "center", minHeight: 22, padding: "0 7px", border: "1px solid", borderRadius: 999, fontSize: 10, fontWeight: 900 };
const mono: React.CSSProperties = { fontFamily: '"Cascadia Mono", "Consolas", monospace', fontSize: 11, overflowWrap: "anywhere" };
const subH: React.CSSProperties = { margin: "0 0 6px", fontSize: 13 };

export default function DicomConversionReviewPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<DicomConversionPreflightResponse | null>(null);
  const [persistResult, setPersistResult] = useState<DicomConversionPlanPersistenceResponse | null>(null);
  const [persisting, setPersisting] = useState(false);
  const [persistError, setPersistError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [releaseReadiness, setReleaseReadiness] = useState<DicomConversionReleaseReadinessReport | null>(null);
  const reqRef = useRef(0);

  async function handleRun() {
    if (!projectId) return;
    const id = reqRef.current + 1; reqRef.current = id;
    setLoading(true); setError("");
    try {
      const res = await runProjectDicomConversionPreflight(effectiveBase, projectId);
      if (id === reqRef.current) setData(res as DicomConversionPreflightResponse);
    } catch (e) { if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e)); }
    finally { if (id === reqRef.current) setLoading(false); }
  }

  async function handlePersist() {
    if (!projectId || !data) return;
    setPersisting(true); setPersistError(""); setPersistResult(null);
    try {
      const body: Record<string, unknown> = {
        approval_id: "review-" + Date.now(),
        status: "ready_for_review",
        approved: false,
        overwrite_policy: "fail_if_exists",
        preflight_snapshot: data,
        mappings: data.mappings,
        command_templates: data.command_templates,
        safety_flags: data.safety_flags,
      };
      const res = await persistProjectDicomConversionPlan(effectiveBase, projectId, body);
      setPersistResult(res as DicomConversionPlanPersistenceResponse);
    } catch (e) { setPersistError(e instanceof Error ? e.message : String(e)); }
    finally { setPersisting(false); }
  }

  if (!projectId) return <Sect><H3>DICOM Conversion Review</H3><div className="empty">Select a project.</div></Sect>;
  if (error) return <Sect><H3>DICOM Conversion Review</H3><div className="errorBox">{error}</div></Sect>;

  return (
    <Sect>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div><H3>DICOM Conversion Review</H3><Sub>Readiness inspection, command-template review, and safety validation only.</Sub></div>
        {data && <span style={{ ...pill, ...statusBadge[data.status] || statusBadge.unknown }}>{data.status.toUpperCase()}</span>}
      </div>

      {/* Safety callout */}
      <div style={{ padding: 10, border: "1px solid rgba(242, 153, 74, 0.28)", borderRadius: 6, background: "rgba(255, 251, 242, 0.94)", fontSize: 11, color: "#9a5a15", marginBottom: 12, lineHeight: 1.5 }}>
        <strong>Real DICOM-to-NIfTI conversion for user data is not enabled in this release.</strong>{" "}
        This panel is for readiness review, command-template inspection, and safety validation only.
        No files are written. No rawdata is modified. No external tools are executed.
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <button onClick={handleRun} disabled={loading} style={{ padding: "8px 18px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
          {loading ? "Running preflight..." : "Run conversion preflight"}
        </button>
        {data && (
          <button onClick={handlePersist} disabled={persisting} style={{ padding: "8px 18px", background: "#4caf50", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
            {persisting ? "Saving..." : "Persist review package"}
          </button>
        )}
      </div>

      {loading && <div className="empty" style={{ marginBottom: 12 }}>Running conversion preflight...</div>}
      {!data && !loading && <div className="empty" style={{ marginBottom: 12 }}>Click the button above to run a conversion readiness preflight.</div>}

      {/* Persist result */}
      {persistError && <div className="errorBox" style={{ marginBottom: 10, fontSize: 11 }}>{persistError}</div>}
      {persistResult && (
        <div style={{ marginBottom: 12, padding: 10, border: "1px solid rgba(56, 103, 214, 0.22)", borderRadius: 6, background: "rgba(239, 246, 255, 0.88)", fontSize: 11 }}>
          <div style={{ fontWeight: 700, marginBottom: 6, color: "#2450a6" }}>
            Review package persisted · status: {persistResult.status}
          </div>
          <div style={{ color: "#9a5a15", marginBottom: 6 }}>
            This saves review metadata only. It does not run conversion.
          </div>
          {persistResult.conversion_run_id && (
            <div style={mono}>run: {persistResult.conversion_run_id}</div>
          )}
          {persistResult.reservation && (
            <div style={{ display: "grid", gap: 2, marginTop: 4 }}>
              {persistResult.reservation.run_dir && <div style={mono}>dir: {persistResult.reservation.run_dir}</div>}
              {persistResult.written_files.length > 0 && (
                <div style={{ color: "#667085" }}>{persistResult.written_files.length} file(s) written</div>
              )}
            </div>
          )}
        </div>
      )}

      {data && (
        <>
          {/* A. Conversion readiness summary */}
          <div style={{ marginBottom: 12 }}>
            <h4 style={subH}>Conversion Readiness</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: 8 }}>
              <M label="status" value={data.status} />
              <M label="disabled by default" value={String(data.conversion_disabled_by_default)} />
              <M label="mapping count" value={data.mapping_count} />
              <M label="approval required" value={String(data.approval_required)} />
              <M label="audit required" value={String(data.audit_required)} />
            </div>
          </div>

          {/* B. dcm2niix availability */}
          <div style={{ marginBottom: 12 }}>
            <h4 style={subH}>dcm2niix Availability</h4>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginBottom: 4 }}>
              <span style={{ ...pill, ...dcm2niixStatusBadge[data.dcm2niix_status] || dcm2niixStatusBadge.unknown }}>
                {data.dcm2niix_status}
              </span>
              {data.dcm2niix_path && <span style={mono}>{data.dcm2niix_path}</span>}
              {data.dcm2niix_version && <span style={{ fontSize: 11, color: "#667085" }}>v{data.dcm2niix_version}</span>}
            </div>
            <div style={{ fontSize: 11, color: "#667085" }}>
              env enabled: {String(data.env_enabled)}
              {data.missing_env_flags.length > 0 && (
                <span style={{ color: "#9a5a15" }}> · missing flags: {data.missing_env_flags.join(", ")}</span>
              )}
            </div>
          </div>

          {/* C. Command templates */}
          {data.command_templates.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={subH}>Command Templates ({data.command_templates.length})</h4>
              <div style={{ fontSize: 10, color: "#9a5a15", marginBottom: 6 }}>
                Command preview only — not executed for user rawdata in this release.
              </div>
              <div style={{ display: "grid", gap: 6, maxHeight: 280, overflow: "auto" }}>
                {data.command_templates.map((t, i) => <TemplateRow key={i} template={t} />)}
              </div>
            </div>
          )}

          {/* D. Safety flags */}
          {data.safety_flags && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={subH}>Safety Flags</h4>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {Object.entries(data.safety_flags as Record<string, boolean>).map(([k, v]) => (
                  <span key={k} style={{ ...pill, background: v ? "#e8f5e9" : "#ffebee", color: v ? "#176b3b" : "#b53b3b", borderColor: v ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)" }}>
                    {k.replace(/_/g, " ")}: {String(v)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* E. Output root */}
          {data.output_root_preview && (
            <div style={{ marginBottom: 12, fontSize: 11 }}>
              <h4 style={subH}>Output Root</h4>
              <div style={mono}>{data.output_root_preview}</div>
              <span style={{ color: data.output_dir_safe ? "#176b3b" : "#b53b3b" }}>
                {data.output_dir_safe ? "safe" : "unsafe"}
              </span>
            </div>
          )}

          {/* Mappings */}
          {data.mappings.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={subH}>Conversion Mappings ({data.mappings.length})</h4>
              <div style={{ display: "grid", gap: 4 }}>
                {data.mappings.slice(0, 20).map((m, i) => (
                  <div key={i} style={{ padding: "4px 8px", border: "1px solid rgba(137, 150, 171, 0.18)", borderRadius: 4, background: "#fff", fontSize: 11 }}>
                    <span style={{ fontWeight: 600 }}>{m.subject_id}</span>
                    <span style={{ color: "#667085", margin: "0 6px" }}>{m.modality}/{m.suffix}</span>
                    {m.suggested_relative_path && <span style={{ ...mono, fontSize: 10, color: "#888" }}>{m.suggested_relative_path}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.blocking_issues.length > 0 && (
            <div className="errorBox" style={{ marginBottom: 10, fontSize: 11 }}>
              {data.blocking_issues.map((b, i) => <div key={i}>{b}</div>)}
            </div>
          )}
          {data.errors.length > 0 && <div className="errorBox" style={{ marginBottom: 10, fontSize: 11 }}>{data.errors.join("\n")}</div>}
          {data.warnings.length > 0 && <Warn items={data.warnings} />}

          {/* F. Approval Gate Requirements (read-only checklist) */}
          <div style={{ marginTop: 12, marginBottom: 12 }}>
            <h4 style={{ ...subH, display: "flex", alignItems: "center", gap: 8 }}>
              Approval Gate Requirements
              <span style={{ ...pill, background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" }}>NO-GO</span>
            </h4>
            <div style={{ padding: 8, border: "1px solid rgba(242, 153, 74, 0.28)", borderRadius: 6, background: "rgba(255, 251, 242, 0.94)", fontSize: 11, color: "#9a5a15", marginBottom: 8, lineHeight: 1.5 }}>
              All 17 preconditions below must be satisfied before real user-data conversion can be enabled.
              <strong> Real conversion remains disabled in this release.</strong>
            </div>
            <div style={{ display: "grid", gap: 3, fontSize: 11, maxHeight: 220, overflow: "auto" }}>
              {APPROVAL_CHECKLIST.map((item, i) => (
                <div key={i} style={{ display: "flex", gap: 6, alignItems: "center", padding: "3px 6px", border: "1px solid rgba(137, 150, 171, 0.14)", borderRadius: 3, background: "#fff" }}>
                  <span style={{ color: "#b53b3b", fontWeight: 700, width: 14 }}>☐</span>
                  <span style={{ color: "#667085" }}>{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* No smoke results notice */}
          <div style={{ padding: 8, border: "1px solid rgba(137, 150, 171, 0.18)", borderRadius: 6, background: "#f9f9fb", fontSize: 11, color: "#667085", marginTop: 8 }}>
            No conversion smoke results have been generated. Real user-data conversion remains disabled.
          </div>
        </>
      )}

      {/* Phase 4K-1: Release Readiness Panel */}
      {persistResult?.conversion_run_id && (
        <ReleaseReadinessSection
          projectId={projectId!}
          conversionRunId={persistResult.conversion_run_id}
        />
      )}

      {/* Phase 4L-4: Flag-gated DICOM Conversion Execute Panel */}
      {persistResult?.conversion_run_id && (
        <DicomConversionExecutePanel
          baseUrl={effectiveBase}
          projectId={projectId!}
          conversionRunId={persistResult.conversion_run_id}
          readiness={releaseReadiness}
        />
      )}

      {/* Phase 5A: Converted BIDS → Preprocessing Input handoff */}
      {persistResult?.conversion_run_id && (
        <PreprocessingHandoffSection
          projectId={projectId!}
          conversionRunId={persistResult.conversion_run_id}
        />
      )}
    </Sect>
  );
}

function TemplateRow({ template }: { template: Dcm2niixCommandTemplate }) {
  return (
    <div style={{ padding: 8, border: "1px solid rgba(137, 150, 171, 0.22)", borderRadius: 6, background: "#fff", fontSize: 11 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
        <span style={{ fontWeight: 600 }}>{template.executable}</span>
        <span style={{ color: "#667085" }}>→ {template.output_dir}</span>
      </div>
      <div style={mono}>{template.command_preview}</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4, fontSize: 10, color: "#98a2b3" }}>
        <span>compress: {template.compress}</span>
        <span>bids_sidecar: {String(template.bids_sidecar)}</span>
        <span>create_bids: {String(template.create_bids)}</span>
      </div>
    </div>
  );
}

function Warn({ items }: { items: string[] }) { return <div style={{ marginTop: 4, padding: 6, border: "1px solid rgba(242, 153, 74, 0.24)", borderRadius: 4, background: "rgba(255, 251, 242, 0.94)", color: "#9a5a15", fontSize: 11 }}>{items.slice(0, 3).map((w,i)=><div key={i}>{w}</div>)}</div>; }
function M({ label, value }: { label: string; value: number | string }) { return <div style={{ padding: "8px 10px", border: "1px solid rgba(137, 150, 171, 0.24)", borderRadius: 6, background: "#fff", display: "grid", gap: 2, color: "#667085", fontSize: 11, fontWeight: 850 }}><span>{label}</span><strong>{value}</strong></div>; }

const APPROVAL_CHECKLIST: string[] = [
  "User approval record with all required fields",
  "Audit record persisted before dcm2niix is called",
  "confirm_execution=true",
  "Conversion-specific approval ID",
  "Selected mappings reviewed (operator confirms each mapping)",
  "Output root under project output directory (validated)",
  "Output root NOT under rawdata directory (validated)",
  "Overwrite policy explicitly set",
  "Rawdata read-only acknowledgement",
  "Command templates reviewed",
  "No shell string acknowledgement",
  "dcm2niix availability verified (on PATH, version recorded)",
  "All required environment flags present",
  "Manifest and provenance paths planned",
  "stdout/stderr log paths planned",
  "Rollback/cleanup policy accepted",
  "Clinical-use prohibition acknowledged",
];

function PreprocessingHandoffSection({ projectId, conversionRunId }: { projectId: string; conversionRunId: string }) {
  const [regResult, setRegResult] = useState<PreprocessingInputRegistrationResponse | null>(null);
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState("");
  const [planResult, setPlanResult] = useState<PreprocessingPlanPreviewResponse | null>(null);
  const [planLoading, setPlanLoading] = useState(false);

  async function handleRegister() {
    setRegLoading(true); setRegError(""); setRegResult(null);
    try {
      const res = await registerConvertedPreprocessingInput(DEFAULT_API_BASE, projectId, {
        conversion_run_id: conversionRunId,
        mode: "reference",
        confirm_rawdata_readonly: true,
        confirm_use_converted_outputs: true,
      });
      setRegResult(res as PreprocessingInputRegistrationResponse);
    } catch (e) { setRegError(e instanceof Error ? e.message : String(e)); }
    finally { setRegLoading(false); }
  }

  async function handlePlanPreview() {
    setPlanLoading(true); setPlanResult(null);
    try {
      const res = await getPreprocessingPlanPreview(DEFAULT_API_BASE, projectId);
      setPlanResult(res as PreprocessingPlanPreviewResponse);
    } catch (e) { /* ignore */ }
    finally { setPlanLoading(false); }
  }

  return (
    <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)", marginTop: 12 }}>
      <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>Converted BIDS → Preprocessing Input</h3>
      <span style={{ color: "#667085", fontSize: 12 }}>Register converted NIfTI outputs for preprocessing planning. No preprocessing is executed.</span>

      {/* Safety callout */}
      <div style={{ padding: 8, border: "1px solid rgba(242, 153, 74, 0.22)", borderRadius: 4, background: "rgba(255, 251, 242, 0.94)", fontSize: 11, color: "#9a5a15", margin: "8px 0" }}>
        Preprocessing execution is not enabled in this phase. This panel registers converted outputs for readiness and planning only.
      </div>

      {/* Register button */}
      <div style={{ marginBottom: 8 }}>
        <button onClick={handleRegister} disabled={regLoading} style={{ padding: "6px 14px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 11 }}>
          {regLoading ? "Registering..." : "Register converted outputs for preprocessing"}
        </button>
      </div>

      {regError && <div className="errorBox" style={{ fontSize: 11, marginBottom: 6 }}>{regError}</div>}

      {/* Registration result */}
      {regResult && (
        <div style={{ marginBottom: 12, padding: 10, border: `1px solid ${regResult.ok ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)"}`, borderRadius: 6, background: regResult.ok ? "rgba(232,245,233,0.88)" : "rgba(255,235,238,0.88)", fontSize: 11 }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Status: {regResult.status}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(80px, 1fr))", gap: 4 }}>
            <span>subjects: <strong>{regResult.subject_count}</strong></span>
            <span>BOLD: <strong>{regResult.bold_count}</strong></span>
            <span>T1w: <strong>{regResult.t1w_count}</strong></span>
            <span>NIfTI: <strong>{regResult.nifti_count}</strong></span>
          </div>
          {regResult.missing_t1w_subjects.length > 0 && (
            <div style={{ color: "#b53b3b", marginTop: 4 }}>Missing T1w: {regResult.missing_t1w_subjects.join(", ")}</div>
          )}
          {regResult.missing_bold_subjects.length > 0 && (
            <div style={{ color: "#b53b3b" }}>Missing BOLD: {regResult.missing_bold_subjects.join(", ")}</div>
          )}
          {regResult.warnings.map((w: string, i: number) => <div key={i} style={{ color: "#9a5a15" }}>{w}</div>)}
          {regResult.ok && (
            <div style={{ marginTop: 6 }}>
              <button onClick={handlePlanPreview} disabled={planLoading} style={{ padding: "4px 10px", background: "#4caf50", color: "#fff", border: "none", borderRadius: 3, cursor: "pointer", fontWeight: 600, fontSize: 10 }}>
                {planLoading ? "Loading..." : "Preview preprocessing plan"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Plan preview result */}
      {planResult && (
        <div style={{ padding: 10, border: "1px solid rgba(25,118,210,0.22)", borderRadius: 6, background: "rgba(227,242,253,0.88)", fontSize: 11 }}>
          <div style={{ fontWeight: 700, marginBottom: 4, color: "#0d47a1" }}>
            Preprocessing Plan Preview · {planResult.status}
            {planResult.execution_disabled && <span style={{ color: "#b53b3b", marginLeft: 8 }}>EXECUTION DISABLED</span>}
          </div>
          <div style={{ fontSize: 10, color: "#9a5a15", marginBottom: 4 }}>
            Preprocessing execution is not enabled. This is a preview only.
          </div>
          <div style={{ display: "grid", gap: 2 }}>
            {planResult.stages.map((s, i) => (
              <div key={i} style={{ display: "flex", gap: 6, alignItems: "center", padding: "2px 6px", border: "1px solid rgba(137,150,171,0.14)", borderRadius: 3, background: "#fff" }}>
                <span style={{ color: s.enabled ? "#176b3b" : "#b53b3b", fontWeight: 700, width: 18, textAlign: "center" }}>{s.enabled ? "✓" : "✗"}</span>
                <span style={{ flex: 1 }}>{s.name}</span>
                <span style={{ fontSize: 10, color: "#667085" }}>{s.backend}{s.requires_external_tool ? " (ext)" : ""}{s.optional ? " (opt)" : ""}</span>
              </div>
            ))}
          </div>
          {planResult.warnings.map((w: string, i: number) => <div key={i} style={{ color: "#9a5a15", marginTop: 4, fontSize: 10 }}>{w}</div>)}
        </div>
      )}
    </section>
  );
}

const Sect: React.FC<{ children: React.ReactNode }> = ({ children }) => <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)", marginTop: 4 }}>{children}</section>;
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>;

function ReleaseReadinessSection({ projectId, conversionRunId }: { projectId: string; conversionRunId: string }) {
  const [rr, setRr] = useState<DicomConversionReleaseReadinessReport | null>(null);
  const [rrLoading, setRrLoading] = useState(false);
  const [rrError, setRrError] = useState("");

  async function handleCheck() {
    setRrLoading(true); setRrError("");
    try {
      const res = await getProjectDicomConversionReleaseReadiness(DEFAULT_API_BASE, projectId, conversionRunId);
      setRr(res as DicomConversionReleaseReadinessReport);
    } catch (e) { setRrError(e instanceof Error ? e.message : String(e)); }
    finally { setRrLoading(false); }
  }

  return <DicomConversionReleaseReadinessPanel readiness={rr} loading={rrLoading} error={rrError} onRefresh={handleCheck} />;
}
