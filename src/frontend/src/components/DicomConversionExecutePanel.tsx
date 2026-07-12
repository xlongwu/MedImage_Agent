import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import type { MessageKey } from "../i18n/messages/en";
import {
  registerProjectDicomConversionResult,
  runProjectDicomConversionExecute,
} from "../lib/api/dicom";
import { useDicomConversionWorkflow } from "../hooks/useDicomConversionWorkflow";
import type {
  DicomConversionExecutionUiState,
  DicomConversionPrepareResponse,
  DicomConversionPublicExecutionResponse,
  DicomConversionPublicExecutionSafetyFlags,
  DicomConversionReleaseReadinessReport,
} from "../types";
import styles from "./DicomConversionExecutePanel.module.css";

type Props = {
  baseUrl: string;
  projectId: string;
  conversionRunId: string;
  readiness: DicomConversionReleaseReadinessReport | null;
  onPrepared?: (response: DicomConversionPrepareResponse) => void;
  onConversionRegistered?: () => void | Promise<void>;
};

type MappingExecutionResult = {
  subject_id?: string;
  modality?: string;
  status?: string;
  error?: string;
  output_file?: string;
};

const CONFIRMATIONS: { key: string }[] = [
  { key: "confirm_research_use_only" },
  { key: "confirm_no_clinical_use" },
  { key: "confirm_rawdata_readonly" },
  { key: "confirm_rollback_available" },
  { key: "confirm_disk_space_checked" },
  { key: "confirm_public_execution_risk" },
  { key: "confirm_spm_disabled" },
  { key: "confirm_dicom_only" },
];

// 实现dcm2nii任务方案.md §16.4 — Prepare-flow confirmation labels.
// These mirror the backend DicomConversionPrepareConfirmations schema.
const PREPARE_CONFIRMATIONS: {
  key: keyof import("../types").DicomConversionPrepareConfirmations;
}[] = [
  { key: "mappings_reviewed" },
  { key: "rawdata_readonly" },
  { key: "research_use_only" },
  { key: "no_clinical_use" },
  { key: "external_converter" },
  { key: "rollback_policy" },
  { key: "risk_acknowledgement" },
  { key: "approval_audit" },
  { key: "public_endpoint" },
  { key: "frontend_execute" },
  { key: "spm_dpabi_matlab_disabled" },
  { key: "confirm_execution" },
];

const CONFIRMATION_MESSAGE_KEYS: Record<string, MessageKey> = {
  confirm_research_use_only: "technical.DicomConversionExecute.confirm.confirm_research_use_only",
  confirm_no_clinical_use: "technical.DicomConversionExecute.confirm.confirm_no_clinical_use",
  confirm_rawdata_readonly: "technical.DicomConversionExecute.confirm.confirm_rawdata_readonly",
  confirm_rollback_available: "technical.DicomConversionExecute.confirm.confirm_rollback_available",
  confirm_disk_space_checked: "technical.DicomConversionExecute.confirm.confirm_disk_space_checked",
  confirm_public_execution_risk:
    "technical.DicomConversionExecute.confirm.confirm_public_execution_risk",
  confirm_spm_disabled: "technical.DicomConversionExecute.confirm.confirm_spm_disabled",
  confirm_dicom_only: "technical.DicomConversionExecute.confirm.confirm_dicom_only",
  mappings_reviewed: "technical.DicomConversionExecute.confirm.mappings_reviewed",
  rawdata_readonly: "technical.DicomConversionExecute.confirm.rawdata_readonly",
  research_use_only: "technical.DicomConversionExecute.confirm.research_use_only",
  no_clinical_use: "technical.DicomConversionExecute.confirm.no_clinical_use",
  external_converter: "technical.DicomConversionExecute.confirm.external_converter",
  rollback_policy: "technical.DicomConversionExecute.confirm.rollback_policy",
  risk_acknowledgement: "technical.DicomConversionExecute.confirm.risk_acknowledgement",
  approval_audit: "technical.DicomConversionExecute.confirm.approval_audit",
  public_endpoint: "technical.DicomConversionExecute.confirm.public_endpoint",
  frontend_execute: "technical.DicomConversionExecute.confirm.frontend_execute",
  spm_dpabi_matlab_disabled: "technical.DicomConversionExecute.confirm.spm_dpabi_matlab_disabled",
  confirm_execution: "technical.DicomConversionExecute.confirm.confirm_execution",
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

export default function DicomConversionExecutePanel({
  baseUrl,
  projectId,
  conversionRunId,
  readiness,
  onPrepared,
  onConversionRegistered,
}: Props) {
  const { t } = useI18n();
  const featureEnabled = import.meta.env.VITE_ENABLE_DICOM_EXECUTE_UI === "1";

  const [uiState, setUiState] = useState<DicomConversionExecutionUiState>(
    featureEnabled ? "disabled_info" : "hidden",
  );
  const [confirmChecks, setConfirmChecks] = useState<Record<string, boolean>>({});
  const [response, setResponse] = useState<DicomConversionPublicExecutionResponse | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 实现dcm2nii任务方案.md §16 — unified prepare workflow hook.
  // The hook manages operator confirmations and the prepare API call.
  const workflow = useDicomConversionWorkflow(baseUrl, projectId, conversionRunId);

  // Determine if readiness allows execution
  const readinessReady = readiness?.status === "ready_for_human_release_review";
  const gatesFull = readiness != null && readiness.gates_met >= readiness.gates_total;

  // Show the confirm button only after the prepare workflow has produced the
  // release approval decision consumed by the execute endpoint.
  const canShowConfirm = featureEnabled && workflow.executionReady;

  function toggleConfirm(key: string) {
    setConfirmChecks((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const allConfirmed = CONFIRMATIONS.every((c) => confirmChecks[c.key] === true);

  async function handlePrepare() {
    const resp = await workflow.prepare();
    if (resp) {
      onPrepared?.(resp);
      if (resp.execution_ready) {
        setUiState("confirming");
      }
    }
  }

  async function handleExecute() {
    if (!allConfirmed || submitting) return;
    setSubmitting(true);
    setUiState("submitting");
    setError("");
    setResponse(null);

    try {
      // 实现dcm2nii任务方案.md §16.5 — prefer the conversion_run_id
      // reserved by the prepare workflow; fall back to the prop value.
      const runId = workflow.conversionRunId || conversionRunId;
      const releaseApprovalId =
        workflow.prepareResponse?.release_approval_id || `frontend-${Date.now()}`;
      const body: Record<string, unknown> = {
        conversion_run_id: runId,
        release_approval_id: releaseApprovalId,
        confirm_user_data_conversion: confirmChecks.confirm_dicom_only ?? false,
        confirm_rawdata_readonly: confirmChecks.confirm_rawdata_readonly ?? false,
        confirm_research_use_only: confirmChecks.confirm_research_use_only ?? false,
        confirm_no_clinical_use: confirmChecks.confirm_no_clinical_use ?? false,
        confirm_rollback_available: confirmChecks.confirm_rollback_available ?? false,
        confirm_disk_space_checked: confirmChecks.confirm_disk_space_checked ?? false,
        confirm_public_execution_risk: confirmChecks.confirm_public_execution_risk ?? false,
        requested_by: "operator",
        reason: "Research DICOM-to-NIfTI conversion via frontend execute UI",
        dry_run_first: true,
        rollback_mode_on_failure: "quarantine",
      };

      const resp = (await runProjectDicomConversionExecute(
        baseUrl,
        projectId,
        body,
      )) as DicomConversionPublicExecutionResponse;

      setResponse(resp);
      if (resp.ok && resp.status === "succeeded") {
        setUiState("succeeded");
      } else if (resp.status === "partial") {
        setUiState("partial");
      } else if (resp.status === "blocked" || resp.status === "disabled") {
        setUiState("blocked");
      } else {
        setUiState("failed");
      }

      // 实现dcm2nii任务方案.md §17 — register conversion result into
      // project metadata so Dashboard/Viewer/project state can refresh.
      // Fire-and-forget; failures here do not block the UI flow.
      if (resp.ok && (resp.status === "succeeded" || resp.status === "partial")) {
        try {
          await registerProjectDicomConversionResult(baseUrl, projectId, {
            conversion_run_id: runId,
            output_root: resp.output_root,
            execution_status: resp.status,
            manifest_path: resp.output_manifest_path ?? resp.manifest_path,
            provenance_path: resp.execution_provenance_path ?? resp.provenance_path,
            checksum_verified: resp.checksum_verified,
          });
          await onConversionRegistered?.();
        } catch {
          // Registration failure is non-fatal; the conversion itself succeeded.
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setUiState("failed");
    } finally {
      setSubmitting(false);
    }
  }

  // ── Hidden state ──
  if (uiState === "hidden") {
    return null;
  }

  // ── Disabled info state ──
  if (
    uiState === "disabled_info" ||
    (!canShowConfirm &&
      uiState !== "submitting" &&
      uiState !== "succeeded" &&
      uiState !== "partial" &&
      uiState !== "failed" &&
      uiState !== "blocked")
  ) {
    const missing: string[] = [];
    if (!featureEnabled) missing.push(t("technical.DicomConversionExecute.missing.featureFlag"));
    const preparedExecutionReady = workflow.executionReady;
    if (!readinessReady && !preparedExecutionReady) {
      missing.push(t("technical.DicomConversionExecute.missing.releaseReadiness"));
    }
    if (!gatesFull && !preparedExecutionReady) {
      missing.push(
        t("technical.DicomConversionExecute.missing.safetyGates", {
          met: readiness?.gates_met ?? 0,
          total: readiness?.gates_total ?? 32,
        }),
      );
    }

    return (
      <section className={styles.style001}>
        <h3 className={styles.style002}>{t("technical.DicomConversionExecute.001")}</h3>
        <div className={styles.style003}>
          <strong>{t("technical.DicomConversionExecute.002")}</strong>{" "}
          {t("technical.DicomConversionExecute.disabled.requirements")}
        </div>
        {missing.length > 0 && (
          <div className={styles.style004}>
            <h4 className={styles.style005}>{t("technical.DicomConversionExecute.003")}</h4>
            {missing.map((m, i) => (
              <div key={i} className={styles.style006}>
                {m}
              </div>
            ))}
          </div>
        )}
        {canShowConfirm && (
          <button
            onClick={() => setUiState("confirming")}
            style={{
              padding: "8px 18px",
              background: "#1976d2",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            {t("technical.DicomConversionExecute.action.approveRequest")}
          </button>
        )}

        {/* 实现dcm2nii任务方案.md §16.3 — Prepare workflow entry point.
            The prepare button is shown whenever the feature flag is on,
            allowing the operator to validate preconditions and reserve a
            conversion run even before traditional release readiness is met. */}
        {featureEnabled && (
          <div style={{ marginTop: 12, padding: 10, border: "1px solid #e0e0e0", borderRadius: 4 }}>
            <h4 style={{ margin: "0 0 6px 0", fontSize: 12, fontWeight: 700 }}>
              {t("technical.DicomConversionExecute.prepare.title")}
            </h4>
            <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>
              {t("technical.DicomConversionExecute.prepare.description")}
            </div>
            {PREPARE_CONFIRMATIONS.map((c) => (
              <label
                key={c.key}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 11,
                  marginBottom: 4,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={workflow.confirmations[c.key]}
                  onChange={() => workflow.toggleConfirmation(c.key)}
                />
                {t(CONFIRMATION_MESSAGE_KEYS[c.key])}
              </label>
            ))}
            {workflow.missingConfirmations.length > 0 && (
              <div style={{ fontSize: 10, color: "#b53b3b", marginTop: 4 }}>
                {t("technical.DicomConversionExecute.label.missing")}:{" "}
                {workflow.missingConfirmations.join(", ")}
              </div>
            )}
            {workflow.blockingIssues.length > 0 && (
              <div style={{ fontSize: 10, color: "#b53b3b", marginTop: 4 }}>
                {t("technical.DicomConversionExecute.label.blocking")}:{" "}
                {workflow.blockingIssues.join("; ")}
              </div>
            )}
            {workflow.error && (
              <div style={{ fontSize: 10, color: "#b53b3b", marginTop: 4 }}>
                {t("technical.DicomConversionExecute.label.error")}: {workflow.error}
              </div>
            )}
            {workflow.prepareResponse && (
              <div style={{ fontSize: 10, color: "#176b3b", marginTop: 4 }}>
                {t("technical.DicomConversionExecute.label.status")}: {workflow.status} |{" "}
                {t("technical.DicomConversionExecute.label.next")}: {workflow.nextAction}
                {workflow.conversionRunId && (
                  <>
                    {" "}
                    | {t("technical.DicomConversionExecute.label.run")}: {workflow.conversionRunId}
                  </>
                )}
              </div>
            )}
            <button
              onClick={handlePrepare}
              disabled={workflow.submitting}
              style={{
                marginTop: 8,
                padding: "6px 14px",
                background: workflow.submitting ? "#ccc" : "#1976d2",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                cursor: workflow.submitting ? "not-allowed" : "pointer",
                fontWeight: 600,
                fontSize: 11,
              }}
            >
              {workflow.submitting
                ? t("technical.DicomConversionExecute.action.preparing")
                : t("technical.DicomConversionExecute.action.prepare")}
            </button>
          </div>
        )}
      </section>
    );
  }

  // ── Blocked response ──
  if (uiState === "blocked") {
    const safety = response?.safety_flags as DicomConversionPublicExecutionSafetyFlags | undefined;
    return (
      <section className={styles.style007}>
        <h3 className={styles.style008}>{t("technical.DicomConversionExecute.004")}</h3>
        <div className={styles.style009}>
          {t("technical.DicomConversionExecute.blocked.description")}
        </div>
        {(response?.blocking_issues ?? []).map((b, i) => (
          <div key={i} className={styles.style010}>
            {b}
          </div>
        ))}
        {safety && (
          <div className={styles.style011}>
            {Object.entries(safety).map(([k, v]) => (
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
        )}
        <button
          onClick={() => {
            setUiState("disabled_info");
            setResponse(null);
            setConfirmChecks({});
          }}
          style={{
            marginTop: 12,
            padding: "6px 14px",
            background: "#1976d2",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          {t("technical.DicomConversionExecute.action.backToReadiness")}
        </button>
      </section>
    );
  }

  // ── Failed response ──
  if (uiState === "failed") {
    return (
      <section className={styles.style012}>
        <h3 className={styles.style013}>{t("technical.DicomConversionExecute.005")}</h3>
        {error && <div className={styles.style014}>{error}</div>}
        {(response?.errors ?? []).map((e, i) => (
          <div key={i} className={styles.style015}>
            {e}
          </div>
        ))}
        {response?.warnings && response.warnings.length > 0 && (
          <div className={styles.style016}>
            {response.warnings.map((w, i) => (
              <div key={i} className={styles.style017}>
                {w}
              </div>
            ))}
          </div>
        )}
        {response?.rollback_result_path && (
          <div className={styles.style018}>
            <strong className={styles.style019}>{t("technical.DicomConversionExecute.006")}</strong>{" "}
            <span style={mono}>{response.rollback_result_path}</span>
          </div>
        )}
        <div className={styles.style020}>
          {t("technical.DicomConversionExecute.failed.rawdataUnchanged")}
        </div>
        <button
          onClick={() => {
            setUiState("disabled_info");
            setResponse(null);
            setConfirmChecks({});
          }}
          style={{
            marginTop: 12,
            padding: "6px 14px",
            background: "#1976d2",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          {t("technical.DicomConversionExecute.action.backToReadiness")}
        </button>
      </section>
    );
  }

  // ── Submitting / progress ──
  if (uiState === "submitting") {
    return (
      <section className={styles.style021}>
        <h3 className={styles.style022}>{t("technical.DicomConversionExecute.007")}</h3>
        <div className={styles.style023}>
          {t("technical.DicomConversionExecute.submitting.description")}
        </div>
        <div className={styles.style024}>
          <div className={styles.style025}>
            <div className={styles.style026} />
          </div>
        </div>
        <div className={styles.style027}>
          {t("technical.DicomConversionExecute.label.status")}:{" "}
          {response?.status ?? t("technical.DicomConversionExecute.submitting.requesting")}
        </div>
      </section>
    );
  }

  // ── Succeeded / Partial response ──
  if ((uiState === "succeeded" || uiState === "partial") && response) {
    const mappingResults =
      (
        response as DicomConversionPublicExecutionResponse & {
          mapping_results?: MappingExecutionResult[];
        }
      ).mapping_results ?? [];
    return (
      <section className={styles.style028}>
        <h3 className={styles.style029}>
          {uiState === "partial"
            ? t("technical.DicomConversionExecute.result.partialTitle")
            : t("technical.DicomConversionExecute.result.completeTitle")}
        </h3>
        <div className={styles.style030}>
          <KV label={t("technical.DicomConversionExecute.label.status")} value={response.status} />
          {response.execution_id && (
            <KV
              label={t("technical.DicomConversionExecute.label.executionId")}
              value={response.execution_id}
            />
          )}
          {response.started_at && (
            <KV
              label={t("technical.DicomConversionExecute.label.started")}
              value={response.started_at}
            />
          )}
          {response.finished_at && (
            <KV
              label={t("technical.DicomConversionExecute.label.finished")}
              value={response.finished_at}
            />
          )}
          {response.checksum_verified !== undefined && (
            <KV
              label={t("technical.DicomConversionExecute.label.checksumVerified")}
              value={String(response.checksum_verified)}
            />
          )}
          {response.output_root && (
            <KV
              label={t("technical.DicomConversionExecute.label.outputRoot")}
              value={response.output_root}
            />
          )}
        </div>

        {uiState === "partial" && (
          <div className={styles.style031} style={{ background: "#fff3e0", color: "#8d6300" }}>
            {t("technical.DicomConversionExecute.result.partialDescription")}
          </div>
        )}

        {mappingResults.length > 0 && (
          <div className={styles.style004}>
            <h4 className={styles.style005}>{t("technical.DicomConversionExecute.008")}</h4>
            {mappingResults.map((mr, i) => (
              <div
                key={i}
                className={styles.style006}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
              >
                <span>
                  <strong>
                    {mr.subject_id}/{mr.modality}
                  </strong>
                  : {mr.status}
                </span>
                {mr.error && <span style={{ color: "#b53b3b", fontSize: 11 }}>{mr.error}</span>}
                {mr.output_file && (
                  <span style={{ ...mono, fontSize: 10, color: "#555" }}>{mr.output_file}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {response.output_manifest_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.outputManifest")}
            path={response.output_manifest_path}
          />
        )}
        {response.execution_provenance_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.executionProvenance")}
            path={response.execution_provenance_path}
          />
        )}
        {response.audit_execution_start_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.auditStart")}
            path={response.audit_execution_start_path}
          />
        )}
        {response.audit_execution_final_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.auditFinal")}
            path={response.audit_execution_final_path}
          />
        )}
        {response.checksum_comparison_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.checksumComparison")}
            path={response.checksum_comparison_path}
          />
        )}
        {response.rollback_plan_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.rollbackPlan")}
            path={response.rollback_plan_path}
          />
        )}
        {response.manifest_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.conversionManifest")}
            path={response.manifest_path}
          />
        )}
        {response.provenance_path && (
          <PathRow
            label={t("technical.DicomConversionExecute.path.provenance")}
            path={response.provenance_path}
          />
        )}

        <div className={styles.style031}>
          {t("technical.DicomConversionExecute.result.safetySummary")}
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button
            onClick={() => {
              setUiState("disabled_info");
              setResponse(null);
              setConfirmChecks({});
            }}
            style={{
              padding: "6px 14px",
              background: "#1976d2",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 11,
            }}
          >
            {t("technical.DicomConversionExecute.action.backToReadiness")}
          </button>
        </div>
      </section>
    );
  }

  // ── Confirmation dialog ──
  return (
    <section className={styles.style032}>
      <h3 className={styles.style033}>
        <span
          role="img"
          aria-label={t("technical.DicomConversionExecute.label.warning")}
          className={styles.style034}
        >
          &#9888;
        </span>
        {t("technical.DicomConversionExecute.confirm.title")}
      </h3>
      <div className={styles.style035}>
        {t("technical.DicomConversionExecute.confirm.description")}
      </div>

      {CONFIRMATIONS.map((c) => (
        <label key={c.key} className={styles.style036}>
          <input
            type="checkbox"
            checked={confirmChecks[c.key] ?? false}
            onChange={() => toggleConfirm(c.key)}
          />
          {t(CONFIRMATION_MESSAGE_KEYS[c.key])}
        </label>
      ))}

      <div className={styles.style037}>
        <button
          onClick={() => {
            setUiState("disabled_info");
            setConfirmChecks({});
          }}
          style={{
            padding: "8px 18px",
            background: "#667085",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: 12,
          }}
        >
          {t("common.cancel")}
        </button>
        <button
          onClick={handleExecute}
          disabled={!allConfirmed || submitting}
          style={{
            padding: "8px 18px",
            background: allConfirmed ? "#4caf50" : "#ccc",
            color: allConfirmed ? "#fff" : "#98a2b3",
            border: "none",
            borderRadius: 4,
            cursor: allConfirmed ? "pointer" : "not-allowed",
            fontWeight: 600,
            fontSize: 12,
          }}
        >
          {submitting
            ? t("technical.DicomConversionExecute.action.submitting")
            : t("technical.DicomConversionExecute.action.approveRequest")}
        </button>
      </div>

      <div className={styles.style038}>
        {t("technical.DicomConversionExecute.confirm.researchDisclaimer")}
      </div>
    </section>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.style039}>
      <div className={styles.style040}>{label}</div>
      <div className={styles.style041}>{value || "—"}</div>
    </div>
  );
}

function PathRow({ label, path }: { label: string; path: string }) {
  return (
    <div className={styles.style042}>
      <span className={styles.style043}>{label}:</span>{" "}
      <span className={styles.style044}>{path}</span>
    </div>
  );
}
