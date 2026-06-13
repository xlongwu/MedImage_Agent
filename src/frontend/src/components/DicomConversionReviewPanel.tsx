import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, getProjectDicomConversionReleaseReadiness, persistProjectDicomConversionPlan, runProjectDicomConversionPreflight } from "../lib/api/legacy";
import type {
  Dcm2niixCommandTemplate,
  DicomConversionMapping,
  DicomConversionPlanPersistenceResponse,
  DicomConversionPreflightResponse,
  DicomConversionReleaseReadinessReport,
  DicomConversionSafetyFlags,
} from "../types";
import DicomConversionReleaseReadinessPanel from "./DicomConversionReleaseReadinessPanel";
import DicomConversionExecutePanel from "./DicomConversionExecutePanel";
import { CollapsibleDetails, MetricTile, SafetyBanner, StatusPill } from "./dashboardUi";
import styles from "./DicomConversionReviewPanel.module.css";

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
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [releaseReadiness, setReleaseReadiness] = useState<DicomConversionReleaseReadinessReport | null>(null);
  const reqRef = useRef(0);
  const canPersistReview = Boolean(data && data.mapping_count > 0);

  useEffect(() => {
    setData(null);
    setPersistResult(null);
    setReleaseReadiness(null);
    if (projectId) {
      handleRun();
    }
  }, [projectId]);

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
    if (data.mapping_count <= 0) {
      setPersistError("Run conversion preflight and review at least one mapping before saving.");
      return;
    }
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
      <div className={styles.style001}>
        <div><H3>DICOM Conversion Review</H3><Sub>Readiness inspection, command-template review, and safety validation only.</Sub></div>
        {data && <StatusPill status={data.status} />}
      </div>

      <SafetyBanner tone="warning">
        <strong>Real DICOM-to-NIfTI conversion for user data is not enabled in this release.</strong>{" "}
        This panel is for readiness review, command-template inspection, and safety validation only.
        No files are written. No rawdata is modified. No external tools are executed.
      </SafetyBanner>

      <div className={styles.style002}>
        <button onClick={handleRun} disabled={loading} className={styles.style003}>
          {loading ? "Running preflight..." : "Run conversion preflight"}
        </button>
        {data && (
          <button
            onClick={handlePersist}
            disabled={persisting || !canPersistReview}
            title={!canPersistReview ? "Run preflight until at least one DICOM mapping is available." : undefined}
            style={{
              padding: "8px 18px",
              background: canPersistReview ? "#4caf50" : "#a8b1c3",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: canPersistReview && !persisting ? "pointer" : "not-allowed",
              fontWeight: 600,
              opacity: canPersistReview ? 1 : 0.82,
            }}
          >
            {persisting ? "Saving..." : "Persist review package"}
          </button>
        )}
      </div>

      {loading && <div className={`empty ${styles.style049}`}>Running conversion preflight...</div>}
      {!data && !loading && <div className={`empty ${styles.style050}`}>Click the button above to run a conversion readiness preflight.</div>}
      {data && data.mapping_count <= 0 && (
        <div className={`empty ${styles.style051}`}>
          No conversion mappings were found. Generate the conversion dry-run or re-run preflight after selecting a raw DICOM project.
        </div>
      )}

      {/* Persist result */}
      {persistError && <div className={`errorBox ${styles.style052}`}>{persistError}</div>}
      {persistResult && (
        <div className={styles.style004}>
          <div className={styles.style005}>
            Review package persisted - status: {persistResult.status}
          </div>
          <div className={styles.style006}>
            This saves review metadata only. It does not run conversion.
          </div>
          {persistResult.conversion_run_id && (
            <div style={mono}>run: {persistResult.conversion_run_id}</div>
          )}
          {persistResult.reservation && (
            <div className={styles.style007}>
              {persistResult.reservation.run_dir && <div style={mono}>dir: {persistResult.reservation.run_dir}</div>}
              {persistResult.written_files.length > 0 && (
                <div className={styles.style008}>{persistResult.written_files.length} file(s) written</div>
              )}
            </div>
          )}
        </div>
      )}

      {data && (
        <>
          {/* A. Conversion readiness summary */}
          <div className={styles.style009}>
            <h4 style={subH}>Conversion Readiness</h4>
            <div className={styles.style010}>
              <MetricTile label="Status" value={data.status} />
              <MetricTile label="Disabled by default" value={String(data.conversion_disabled_by_default)} tone={data.conversion_disabled_by_default ? "amber" : "green"} />
              <MetricTile label="Mapping count" value={data.mapping_count} tone={data.mapping_count > 0 ? "blue" : "neutral"} />
              <MetricTile label="Approval required" value={String(data.approval_required)} tone={data.approval_required ? "amber" : "neutral"} />
              <MetricTile label="Audit required" value={String(data.audit_required)} tone={data.audit_required ? "amber" : "neutral"} />
            </div>
          </div>

          {data.blocking_issues.length > 0 && (
            <div className={styles.style011}>
              <div className={styles.style012}>
                <span>
                  <strong>Conversion is blocked by safety gates.</strong>{" "}
                  {data.blocking_issues.length} prerequisite(s) missing.
                </span>
                <span className={styles.style013}>
                  Next safe action: <strong>Run conversion preflight</strong>
                </span>
              </div>
              <details className={styles.style014}>
                <summary className={styles.style015}>Why blocked? Show technical details</summary>
                <div className={styles.style016}>
                  {data.blocking_issues.map((b, i) => <span key={i} className={styles.style017}>- {b}</span>)}
                </div>
              </details>
            </div>
          )}

          {data.errors.length > 0 && <div className={`errorBox ${styles.style053}`}>{data.errors.join("\n")}</div>}
          {data.warnings.length > 0 && <Warn items={data.warnings} />}

          <div className={styles.style018}>
            <label className={styles.style019}>
              <input
                type="checkbox"
                checked={showTechDetails}
                onChange={(e) => setShowTechDetails(e.target.checked)}
              />
              Show technical details
            </label>
          </div>

          {showTechDetails && (
            <>
              {/* B. dcm2niix availability */}
              <div className={styles.style020}>
                <h4 style={subH}>dcm2niix Availability</h4>
                <div className={styles.style021}>
                  <span style={{ ...pill, ...dcm2niixStatusBadge[data.dcm2niix_status] || dcm2niixStatusBadge.unknown }}>
                    {data.dcm2niix_status}
                  </span>
                  {data.dcm2niix_path && <span style={mono}>{data.dcm2niix_path}</span>}
                  {data.dcm2niix_version && <span className={styles.style022}>v{data.dcm2niix_version}</span>}
                </div>
                <div className={styles.style023}>
                  env enabled: {String(data.env_enabled)}
                  {data.missing_env_flags.length > 0 && (
                    <span className={styles.style024}> - missing flags: {data.missing_env_flags.join(", ")}</span>
                  )}
                </div>
              </div>

              {/* C. Command templates */}
              {data.command_templates.length > 0 && (
                <CollapsibleDetails title="Command templates" summary={`${data.command_templates.length} template(s)`}>
                  <div className={styles.style025}>
                    Command preview only - not executed for user rawdata in this release.
                  </div>
                  <div className={styles.style026}>
                    {data.command_templates.map((t, i) => <TemplateRow key={i} template={t} />)}
                  </div>
                </CollapsibleDetails>
              )}

              {/* D. Safety flags */}
              {data.safety_flags && (
                <CollapsibleDetails title="Safety flags" summary="Approval and rawdata protections">
                  <div className={styles.style027}>
                    {Object.entries(data.safety_flags as Record<string, boolean>).map(([k, v]) => (
                      <span key={k} style={{ ...pill, background: v ? "#e8f5e9" : "#ffebee", color: v ? "#176b3b" : "#b53b3b", borderColor: v ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)" }}>
                        {k.replace(/_/g, " ")}: {String(v)}
                      </span>
                    ))}
                  </div>
                </CollapsibleDetails>
              )}

              {/* E. Output root */}
              {data.output_root_preview && (
                <div className={styles.style028}>
                  <h4 style={subH}>Output Root</h4>
                  <div style={mono}>{data.output_root_preview}</div>
                  <span style={{ color: data.output_dir_safe ? "#176b3b" : "#b53b3b" }}>
                    {data.output_dir_safe ? "safe" : "unsafe"}
                  </span>
                </div>
              )}

              {/* Mappings */}
              {data.mappings.length > 0 && (
                <CollapsibleDetails title="DICOM mapping preview" summary={`${data.mappings.length} mapping(s)`}>
                  <div className={styles.style029}>
                    {data.mappings.slice(0, 20).map((m, i) => (
                      <div key={i} className={styles.style030}>
                        <span className={styles.style031}>{m.subject_id}</span>
                        <span className={styles.style032}>{m.modality}/{m.suffix}</span>
                        {m.suggested_relative_path && <span style={{ ...mono, fontSize: 10, color: "#888" }}>{m.suggested_relative_path}</span>}
                      </div>
                    ))}
                  </div>
                </CollapsibleDetails>
              )}

              {/* F. Approval Gate Requirements (read-only checklist) */}
              <CollapsibleDetails title="Show approval requirements" summary="17 preconditions, NO-GO">
                <div className={styles.style033}>
                  All 17 preconditions below must be satisfied before real user-data conversion can be enabled.
                  <strong> Real conversion remains disabled in this release.</strong>
                </div>
                <div className={styles.style034}>
                  {APPROVAL_CHECKLIST.map((item, i) => (
                    <div key={i} className={styles.style035}>
                      <span className={styles.style036}>x</span>
                      <span className={styles.style037}>{item}</span>
                    </div>
                  ))}
                </div>
              </CollapsibleDetails>

              {/* No smoke results notice */}
              <div className={styles.style038}>
                No conversion smoke results have been generated. Real user-data conversion remains disabled.
              </div>
            </>
          )}
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

    </Sect>
  );
}

function TemplateRow({ template }: { template: Dcm2niixCommandTemplate }) {
  return (
    <div className={styles.style039}>
      <div className={styles.style040}>
        <span className={styles.style041}>{template.executable}</span>
        <span className={styles.style042}>-&gt; {template.output_dir}</span>
      </div>
      <div style={mono}>{template.command_preview}</div>
      <div className={styles.style043}>
        <span>compress: {template.compress}</span>
        <span>bids_sidecar: {String(template.bids_sidecar)}</span>
        <span>create_bids: {String(template.create_bids)}</span>
      </div>
    </div>
  );
}

function Warn({ items }: { items: string[] }) { return <div className={styles.style044}>{items.slice(0, 3).map((w,i)=><div key={i}>{w}</div>)}</div>; }
function M({ label, value }: { label: string; value: number | string }) { return <div className={styles.style045}><span>{label}</span><strong>{value}</strong></div>; }

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

const Sect: React.FC<{ children: React.ReactNode }> = ({ children }) => <section className={styles.style046}>{children}</section>;
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 className={styles.style047}>{children}</h3>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <span className={styles.style048}>{children}</span>;

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
