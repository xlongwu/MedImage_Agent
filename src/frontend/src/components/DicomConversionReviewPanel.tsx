import { useEffect, useRef, useState } from "react";
import type { MessageKey } from "../i18n/messages/en";
import { useI18n } from "../i18n/useI18n";
import { DEFAULT_API_BASE } from "../lib/api/client";
import {
  getProjectDicomConversionReleaseReadiness,
  persistProjectDicomConversionPlan,
  runProjectDicomConversionPreflight,
} from "../lib/api/dicom";
import type {
  Dcm2niixCommandTemplate,
  DicomConversionPlanPersistenceResponse,
  DicomConversionPrepareResponse,
  DicomConversionPreflightResponse,
  DicomConversionReleaseReadinessReport,
} from "../types";
import DicomConversionReleaseReadinessPanel from "./DicomConversionReleaseReadinessPanel";
import DicomConversionExecutePanel from "./DicomConversionExecutePanel";
import { CollapsibleDetails, MetricTile, SafetyBanner, StatusPill } from "./dashboardUi";
import styles from "./DicomConversionReviewPanel.module.css";

type Props = {
  baseUrl?: string;
  projectId: string | null;
  onConversionRegistered?: () => void | Promise<void>;
};

const dcm2niixStatusBadge: Record<string, React.CSSProperties> = {
  available: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  missing: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  version_failed: {
    background: "#fff7ed",
    color: "#9a5a15",
    borderColor: "rgba(242, 153, 74, 0.28)",
  },
  disabled: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
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
const subH: React.CSSProperties = { margin: "0 0 6px", fontSize: 13 };

export default function DicomConversionReviewPanel({
  baseUrl,
  projectId,
  onConversionRegistered,
}: Props) {
  const { t } = useI18n();
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<DicomConversionPreflightResponse | null>(null);
  const [persistResult, setPersistResult] = useState<DicomConversionPlanPersistenceResponse | null>(
    null,
  );
  const [persisting, setPersisting] = useState(false);
  const [persistError, setPersistError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [releaseReadiness, setReleaseReadiness] =
    useState<DicomConversionReleaseReadinessReport | null>(null);
  const [preparedConversionRunId, setPreparedConversionRunId] = useState("");
  const reqRef = useRef(0);
  const canPersistReview = Boolean(data && data.mapping_count > 0);
  const activeConversionRunId = preparedConversionRunId || persistResult?.conversion_run_id || "";

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Reset stale conversion state before loading a new project.
    setData(null);
    setPersistResult(null);
    setReleaseReadiness(null);
    setPreparedConversionRunId("");
    if (projectId) {
      handleRun();
    }
    // handleRun is intentionally scoped to this project transition.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleRun() {
    if (!projectId) return;
    const id = reqRef.current + 1;
    reqRef.current = id;
    setLoading(true);
    setError("");
    try {
      const res = await runProjectDicomConversionPreflight(effectiveBase, projectId);
      if (id === reqRef.current) setData(res as DicomConversionPreflightResponse);
    } catch (e) {
      if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (id === reqRef.current) setLoading(false);
    }
  }

  async function handlePersist() {
    if (!projectId || !data) return;
    if (data.mapping_count <= 0) {
      setPersistError(t("technical.DicomConversionReview.persist.mappingRequired"));
      return;
    }
    setPersisting(true);
    setPersistError("");
    setPersistResult(null);
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
    } catch (e) {
      setPersistError(e instanceof Error ? e.message : String(e));
    } finally {
      setPersisting(false);
    }
  }

  function handlePrepared(response: DicomConversionPrepareResponse) {
    if (response.conversion_run_id) {
      setPreparedConversionRunId(response.conversion_run_id);
      setReleaseReadiness(null);
    }
  }

  if (!projectId)
    return (
      <Sect>
        <H3>{t("technical.DicomConversionReview.001")}</H3>
        <div className="empty">{t("technical.BoldReferenceReadiness.002")}</div>
      </Sect>
    );
  if (error)
    return (
      <Sect>
        <H3>{t("technical.DicomConversionReview.001")}</H3>
        <div className="errorBox">{error}</div>
      </Sect>
    );

  return (
    <Sect>
      <div className={styles.style001}>
        <div>
          <H3>{t("technical.DicomConversionReview.001")}</H3>
          <Sub>{t("technical.DicomConversionReview.002")}</Sub>
        </div>
        {data && <StatusPill status={data.status} />}
      </div>

      <SafetyBanner tone="warning">
        <strong>{t("technical.DicomConversionReview.safety.disabled")}</strong>{" "}
        {t("technical.DicomConversionReview.safety.description")}
      </SafetyBanner>

      <div className={styles.style002}>
        <button onClick={handleRun} disabled={loading} className={styles.style003}>
          {loading
            ? t("technical.DicomConversionReview.action.checking")
            : data
              ? t("technical.DicomConversionReview.action.refresh")
              : t("technical.DicomConversionReview.action.check")}
        </button>
        {data && (
          <button
            onClick={handlePersist}
            disabled={persisting || !canPersistReview}
            title={
              !canPersistReview
                ? t("technical.DicomConversionReview.persist.mappingUnavailable")
                : undefined
            }
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
            {persisting
              ? t("technical.DicomConversionReview.action.saving")
              : t("technical.DicomConversionReview.action.saveDraft")}
          </button>
        )}
      </div>

      {loading && (
        <div className={`empty ${styles.style049}`}>{t("technical.DicomConversionReview.003")}</div>
      )}
      {!data && !loading && (
        <div className={`empty ${styles.style050}`}>
          {t("technical.DicomConversionReview.empty.checkReadiness")}
        </div>
      )}
      {data && data.mapping_count <= 0 && (
        <div className={`empty ${styles.style051}`}>
          {t("technical.DicomConversionReview.empty.noMappings")}
        </div>
      )}

      {/* Persist result */}
      {persistError && <div className={`errorBox ${styles.style052}`}>{persistError}</div>}
      {persistResult && (
        <div className={styles.style004}>
          <div className={styles.style005}>
            {t("technical.DicomConversionReview.persist.saved", {
              status: persistResult.status,
            })}
          </div>
          <div className={styles.style006}>
            {t("technical.DicomConversionReview.persist.metadataOnly")}
          </div>
          {persistResult.conversion_run_id && (
            <div style={mono}>
              {t("technical.DicomConversionReview.label.run")}: {persistResult.conversion_run_id}
            </div>
          )}
          {persistResult.reservation && (
            <div className={styles.style007}>
              {persistResult.reservation.run_dir && (
                <div style={mono}>
                  {t("technical.DicomConversionReview.label.directory")}:{" "}
                  {persistResult.reservation.run_dir}
                </div>
              )}
              {persistResult.written_files.length > 0 && (
                <div className={styles.style008}>
                  {t("technical.DicomConversionReview.persist.filesWritten", {
                    count: persistResult.written_files.length,
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {data && (
        <>
          {/* A. Conversion readiness summary */}
          <div className={styles.style009}>
            <h4 style={subH}>{t("technical.DicomConversionReview.004")}</h4>
            <div className={styles.style010}>
              <MetricTile
                label={t("technical.DicomConversionReview.label.status")}
                value={data.status}
              />
              <MetricTile
                label={t("technical.DicomConversionReview.label.disabledByDefault")}
                value={String(data.conversion_disabled_by_default)}
                tone={data.conversion_disabled_by_default ? "amber" : "green"}
              />
              <MetricTile
                label={t("technical.DicomConversionReview.label.mappingCount")}
                value={data.mapping_count}
                tone={data.mapping_count > 0 ? "blue" : "neutral"}
              />
              <MetricTile
                label={t("technical.DicomConversionReview.label.approvalRequired")}
                value={String(data.approval_required)}
                tone={data.approval_required ? "amber" : "neutral"}
              />
              <MetricTile
                label={t("technical.DicomConversionReview.label.auditRequired")}
                value={String(data.audit_required)}
                tone={data.audit_required ? "amber" : "neutral"}
              />
            </div>
          </div>

          {data.blocking_issues.length > 0 && (
            <div className={styles.style011}>
              <div className={styles.style012}>
                <span>
                  <strong>{t("technical.DicomConversionReview.005")}</strong>{" "}
                  {t("technical.DicomConversionReview.blocked.prerequisites", {
                    count: data.blocking_issues.length,
                  })}
                </span>
                <span className={styles.style013}>
                  {t("technical.DicomConversionReview.006")}{" "}
                  <strong>{t("technical.DicomConversionReview.007")}</strong>
                </span>
              </div>
              <details className={styles.style014}>
                <summary className={styles.style015}>
                  {t("technical.DicomConversionReview.008")}
                </summary>
                <div className={styles.style016}>
                  {data.blocking_issues.map((b, i) => (
                    <span key={i} className={styles.style017}>
                      - {b}
                    </span>
                  ))}
                </div>
              </details>
            </div>
          )}

          {data.errors.length > 0 && (
            <div className={`errorBox ${styles.style053}`}>{data.errors.join("\n")}</div>
          )}
          {data.warnings.length > 0 && <Warn items={data.warnings} />}

          <div className={styles.style018}>
            <label className={styles.style019}>
              <input
                type="checkbox"
                checked={showTechDetails}
                onChange={(e) => setShowTechDetails(e.target.checked)}
              />
              {t("technical.DicomConversionReview.action.showTechnicalDetails")}
            </label>
          </div>

          {showTechDetails && (
            <>
              {/* B. In-project native converter availability */}
              <div className={styles.style020}>
                <h4 style={subH}>{t("technical.DicomConversionReview.dcm2niix.title")}</h4>
                <div className={styles.style021}>
                  <span
                    style={{
                      ...pill,
                      ...(dcm2niixStatusBadge[data.native_converter_status] ||
                        dcm2niixStatusBadge.unknown),
                    }}
                  >
                    {data.native_converter_status}
                  </span>
                  {data.native_converter_version && (
                    <span className={styles.style022}>v{data.native_converter_version}</span>
                  )}
                </div>
                <div className={styles.style023}>
                  {t("technical.DicomConversionReview.dcm2niix.envEnabled")}:{" "}
                  {String(data.env_enabled)}
                  {data.missing_env_flags.length > 0 && (
                    <span className={styles.style024}>
                      {" "}
                      - {t("technical.DicomConversionReview.dcm2niix.missingFlags")}:{" "}
                      {data.missing_env_flags.join(", ")}
                    </span>
                  )}
                </div>
              </div>

              {/* C. Command templates */}
              {data.command_templates.length > 0 && (
                <CollapsibleDetails
                  title={t("technical.DicomConversionReview.templates.title")}
                  summary={t("technical.DicomConversionReview.templates.count", {
                    count: data.command_templates.length,
                  })}
                >
                  <div className={styles.style025}>
                    {t("technical.DicomConversionReview.templates.previewOnly")}
                  </div>
                  <div className={styles.style026}>
                    {data.command_templates.map((t, i) => (
                      <TemplateRow key={i} template={t} />
                    ))}
                  </div>
                </CollapsibleDetails>
              )}

              {/* D. Safety flags */}
              {data.safety_flags && (
                <CollapsibleDetails
                  title={t("technical.DicomConversionReview.safetyFlags.title")}
                  summary={t("technical.DicomConversionReview.safetyFlags.summary")}
                >
                  <div className={styles.style027}>
                    {Object.entries(data.safety_flags as Record<string, boolean>).map(([k, v]) => (
                      <span
                        key={k}
                        style={{
                          ...pill,
                          background: v ? "#e8f5e9" : "#ffebee",
                          color: v ? "#176b3b" : "#b53b3b",
                          borderColor: v ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)",
                        }}
                      >
                        {k.replace(/_/g, " ")}: {String(v)}
                      </span>
                    ))}
                  </div>
                </CollapsibleDetails>
              )}

              {/* E. Output root */}
              {data.output_root_preview && (
                <div className={styles.style028}>
                  <h4 style={subH}>{t("technical.DicomConversionReview.009")}</h4>
                  <div style={mono}>{data.output_root_preview}</div>
                  <span style={{ color: data.output_dir_safe ? "#176b3b" : "#b53b3b" }}>
                    {data.output_dir_safe
                      ? t("technical.DicomConversionReview.output.safe")
                      : t("technical.DicomConversionReview.output.unsafe")}
                  </span>
                </div>
              )}

              {/* Mappings */}
              {data.mappings.length > 0 && (
                <CollapsibleDetails
                  title={t("technical.DicomConversionReview.mappings.title")}
                  summary={t("technical.DicomConversionReview.mappings.count", {
                    count: data.mappings.length,
                  })}
                >
                  <div className={styles.style029}>
                    {data.mappings.slice(0, 20).map((m, i) => (
                      <div key={i} className={styles.style030}>
                        <span className={styles.style031}>{m.subject_id}</span>
                        <span className={styles.style032}>
                          {m.modality}/{m.suffix}
                        </span>
                        {m.suggested_relative_path && (
                          <span style={{ ...mono, fontSize: 10, color: "#888" }}>
                            {m.suggested_relative_path}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </CollapsibleDetails>
              )}

              {/* F. Approval Gate Requirements (read-only checklist) */}
              <CollapsibleDetails
                title={t("technical.DicomConversionReview.approval.title")}
                summary={t("technical.DicomConversionReview.approval.summary")}
              >
                <div className={styles.style033}>
                  {t("technical.DicomConversionReview.approval.description")}{" "}
                  <strong>{t("technical.DicomConversionReview.approval.disabled")}</strong>
                </div>
                <div className={styles.style034}>
                  {APPROVAL_CHECKLIST.map((item, i) => (
                    <div key={i} className={styles.style035}>
                      <span className={styles.style036}>x</span>
                      <span className={styles.style037}>{t(item)}</span>
                    </div>
                  ))}
                </div>
              </CollapsibleDetails>

              {/* No smoke results notice */}
              <div className={styles.style038}>
                {t("technical.DicomConversionReview.smoke.none")}
              </div>
            </>
          )}
        </>
      )}

      {/* Phase 4K-1: Release Readiness Panel */}
      {activeConversionRunId && (
        <ReleaseReadinessSection
          baseUrl={effectiveBase}
          projectId={projectId!}
          conversionRunId={activeConversionRunId}
          readiness={releaseReadiness}
          onReadinessChange={setReleaseReadiness}
        />
      )}

      {/* Phase 4L-4: Flag-gated DICOM Conversion Execute Panel */}
      {(activeConversionRunId || (data && data.mapping_count > 0)) && (
        <DicomConversionExecutePanel
          baseUrl={effectiveBase}
          projectId={projectId!}
          conversionRunId={activeConversionRunId}
          readiness={releaseReadiness}
          preflight={data}
          onPrepared={handlePrepared}
          onConversionRegistered={onConversionRegistered}
        />
      )}
    </Sect>
  );
}

function TemplateRow({ template }: { template: Dcm2niixCommandTemplate }) {
  const { t } = useI18n();
  return (
    <div className={styles.style039}>
      <div className={styles.style040}>
        <span className={styles.style041}>{template.executable}</span>
        <span className={styles.style042}>-&gt; {template.output_dir}</span>
      </div>
      <div style={mono}>{template.command_preview}</div>
      <div className={styles.style043}>
        <span>
          {t("technical.DicomConversionReview.template.compress")}: {template.compress}
        </span>
        <span>
          {t("technical.DicomConversionReview.template.bidsSidecar")}:{" "}
          {String(template.bids_sidecar)}
        </span>
        <span>
          {t("technical.DicomConversionReview.template.createBids")}: {String(template.create_bids)}
        </span>
      </div>
    </div>
  );
}

function Warn({ items }: { items: string[] }) {
  return (
    <div className={styles.style044}>
      {items.slice(0, 3).map((w, i) => (
        <div key={i}>{w}</div>
      ))}
    </div>
  );
}
const APPROVAL_CHECKLIST: MessageKey[] = [
  "technical.DicomConversionReview.approval.item.userApproval",
  "technical.DicomConversionReview.approval.item.auditBeforeExecution",
  "technical.DicomConversionReview.approval.item.confirmExecution",
  "technical.DicomConversionReview.approval.item.approvalId",
  "technical.DicomConversionReview.approval.item.mappingsReviewed",
  "technical.DicomConversionReview.approval.item.outputUnderProject",
  "technical.DicomConversionReview.approval.item.outputOutsideRawdata",
  "technical.DicomConversionReview.approval.item.overwritePolicy",
  "technical.DicomConversionReview.approval.item.rawdataReadonly",
  "technical.DicomConversionReview.approval.item.templatesReviewed",
  "technical.DicomConversionReview.approval.item.noShellString",
  "technical.DicomConversionReview.approval.item.dcm2niixAvailable",
  "technical.DicomConversionReview.approval.item.environmentFlags",
  "technical.DicomConversionReview.approval.item.artifactPaths",
  "technical.DicomConversionReview.approval.item.logPaths",
  "technical.DicomConversionReview.approval.item.rollbackPolicy",
  "technical.DicomConversionReview.approval.item.nonClinical",
];

const Sect: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <section className={styles.style046}>{children}</section>
);
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 className={styles.style047}>{children}</h3>
);
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className={styles.style048}>{children}</span>
);

function ReleaseReadinessSection({
  baseUrl,
  projectId,
  conversionRunId,
  readiness,
  onReadinessChange,
}: {
  baseUrl: string;
  projectId: string;
  conversionRunId: string;
  readiness: DicomConversionReleaseReadinessReport | null;
  onReadinessChange: (readiness: DicomConversionReleaseReadinessReport | null) => void;
}) {
  const [rrLoading, setRrLoading] = useState(false);
  const [rrError, setRrError] = useState("");

  async function handleCheck() {
    setRrLoading(true);
    setRrError("");
    try {
      const res = await getProjectDicomConversionReleaseReadiness(
        baseUrl,
        projectId,
        conversionRunId,
      );
      onReadinessChange(res as DicomConversionReleaseReadinessReport);
    } catch (e) {
      setRrError(e instanceof Error ? e.message : String(e));
    } finally {
      setRrLoading(false);
    }
  }

  return (
    <DicomConversionReleaseReadinessPanel
      readiness={readiness}
      loading={rrLoading}
      error={rrError}
      onRefresh={handleCheck}
    />
  );
}
