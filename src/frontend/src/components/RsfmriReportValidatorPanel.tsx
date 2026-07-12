import { useState, type ReactNode } from "react";

import {
  getLatestRsfmriReportValidation,
  listRsfmriReportValidations,
  runRsfmriReportValidation,
} from "../lib/api/rsfmri";
import { useI18n } from "../i18n/useI18n";
import { localizeReportEvidenceDetail } from "../i18n/reportEvidence";
import { deriveReportValidationEvidence } from "../lib/reportEvidence";
import { EvidenceBadge } from "./domain/EvidenceBadge";
import { JsonBlock } from "./JsonBlock";
import styles from "./ReportEvidence.module.css";
import { TextViewer } from "./TextViewer";
import { Badge, Button, Card } from "./ui";

type Props = { baseUrl: string };
type RequestStatus = "IDLE" | "RUNNING" | "LOADING" | "REQUEST_COMPLETE" | "ERROR";

type Translate = ReturnType<typeof useI18n>["t"];

function requestLabel(status: RequestStatus, t: Translate): string {
  if (status === "RUNNING") return t("report.validation.requested");
  if (status === "LOADING") return t("report.request.loading");
  if (status === "REQUEST_COMPLETE") return t("report.request.complete");
  if (status === "ERROR") return t("report.request.failed");
  return t("report.request.onDemand");
}

function requestTone(status: RequestStatus): "neutral" | "info" | "danger" {
  if (status === "ERROR") return "danger";
  if (status === "RUNNING" || status === "LOADING" || status === "REQUEST_COMPLETE") {
    return "info";
  }
  return "neutral";
}

export function RsfmriReportValidatorPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [vlist, setVlist] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState<RequestStatus>("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");
    try {
      const runResult = await runRsfmriReportValidation(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_report_validator.yaml",
      });
      setResult(runResult);
      setStatus("LOADING");
      setLatest(await getLatestRsfmriReportValidation(baseUrl));
      setStatus("REQUEST_COMPLETE");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function loadLatest() {
    setStatus("LOADING");
    setError("");
    try {
      setLatest(await getLatestRsfmriReportValidation(baseUrl));
      setStatus("REQUEST_COMPLETE");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function loadList() {
    setStatus("LOADING");
    setError("");
    try {
      setVlist(await listRsfmriReportValidations(baseUrl));
      setStatus("REQUEST_COMPLETE");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const evidence = deriveReportValidationEvidence(latest ?? result);
  const displayedValidation = latest ?? result;
  const vr = displayedValidation?.validation_result as Record<string, unknown> | undefined;
  const st = vr?.stats as Record<string, unknown> | undefined;

  return (
    <Card className={styles.panel} tone="muted">
      <div className={styles.header}>
        <div className={styles.headerText}>
          <h2>{t("report.validation.title")}</h2>
          <p>{t("report.validation.description")}</p>
        </div>
        <div className={styles.evidenceGroup}>
          <EvidenceBadge level={evidence.level} />
          <Badge tone={requestTone(status)}>{requestLabel(status, t)}</Badge>
        </div>
      </div>
      <p className={styles.evidenceDetail}>{localizeReportEvidenceDetail(evidence.detail, t)}</p>

      <div className={styles.toolbar}>
        <Button onClick={handleRun} disabled={status === "RUNNING"} variant="primary">
          {t("report.validation.validate")}
        </Button>
        <Button onClick={loadLatest} disabled={status === "LOADING"} variant="secondary">
          {t("report.validation.loadLatest")}
        </Button>
        <Button onClick={loadList} disabled={status === "LOADING"} variant="secondary">
          {t("report.validation.list")}
        </Button>
      </div>

      {error ? (
        <div className={styles.errorLine} role="alert">
          <strong>{t("report.validation.error")}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <div className={styles.metricGrid}>
        <Metric label={t("technical.release.status")} value={vr?.validation_status} />
        <Metric label={t("report.validation.checksum")} value={st?.checksum_mismatch_total} />
        <Metric label={t("report.validation.missing")} value={st?.missing_files_total} />
        <Metric label={t("report.validation.zipOk")} value={st?.zip_test_ok} />
        <Metric label={t("report.validation.safety")} value={st?.safety_violations_total} />
      </div>

      <EvidenceSection title={t("report.validation.result")}>
        <JsonBlock value={vr} emptyText={t("technical.release.noResult")} />
      </EvidenceSection>
      <EvidenceSection title={t("report.validation.checks")}>
        <JsonBlock value={vr?.checks} emptyText={t("technical.release.noChecks")} />
      </EvidenceSection>
      <EvidenceSection title={t("report.validation.report")}>
        <TextViewer
          text={typeof latest?.validation_report === "string" ? latest.validation_report : null}
          emptyText={t("technical.noReport")}
        />
      </EvidenceSection>
      <EvidenceSection title={t("report.validation.listTitle")}>
        <JsonBlock value={vlist} emptyText={t("report.validation.noList")} />
      </EvidenceSection>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className={styles.metricCard}>
      <span>{label}</span>
      <strong>{String(value ?? "-")}</strong>
    </div>
  );
}

function EvidenceSection({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className={styles.section}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}
