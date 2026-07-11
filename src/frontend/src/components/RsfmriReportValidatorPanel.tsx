import { useState, type ReactNode } from "react";

import {
  getLatestRsfmriReportValidation,
  listRsfmriReportValidations,
  runRsfmriReportValidation,
} from "../lib/api/legacy";
import { deriveReportValidationEvidence } from "../lib/reportEvidence";
import { EvidenceBadge } from "./domain/EvidenceBadge";
import { JsonBlock } from "./JsonBlock";
import styles from "./ReportEvidence.module.css";
import { TextViewer } from "./TextViewer";
import { Badge, Button, Card } from "./ui";

type Props = { baseUrl: string };
type RequestStatus = "IDLE" | "RUNNING" | "LOADING" | "REQUEST_COMPLETE" | "ERROR";

function requestLabel(status: RequestStatus): string {
  if (status === "RUNNING") return "Validation requested";
  if (status === "LOADING") return "Loading metadata";
  if (status === "REQUEST_COMPLETE") return "Request complete";
  if (status === "ERROR") return "Request failed";
  return "On demand";
}

function requestTone(status: RequestStatus): "neutral" | "info" | "danger" {
  if (status === "ERROR") return "danger";
  if (status === "RUNNING" || status === "LOADING" || status === "REQUEST_COMPLETE") {
    return "info";
  }
  return "neutral";
}

export function RsfmriReportValidatorPanel({ baseUrl }: Props) {
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
          <h2>Report package validation</h2>
          <p>Validation is shown only when backend validation evidence is complete.</p>
        </div>
        <div className={styles.evidenceGroup}>
          <EvidenceBadge level={evidence.level} />
          <Badge tone={requestTone(status)}>{requestLabel(status)}</Badge>
        </div>
      </div>
      <p className={styles.evidenceDetail}>{evidence.detail}</p>

      <div className={styles.toolbar}>
        <Button onClick={handleRun} disabled={status === "RUNNING"} variant="primary">
          Validate Latest Package
        </Button>
        <Button onClick={loadLatest} disabled={status === "LOADING"} variant="secondary">
          Load Latest Validation
        </Button>
        <Button onClick={loadList} disabled={status === "LOADING"} variant="secondary">
          List Validations
        </Button>
      </div>

      {error ? (
        <div className={styles.errorLine} role="alert">
          <strong>Validation error</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <div className={styles.metricGrid}>
        <Metric label="Status" value={vr?.validation_status} />
        <Metric label="Checksum Mismatches" value={st?.checksum_mismatch_total} />
        <Metric label="Missing Files" value={st?.missing_files_total} />
        <Metric label="ZIP Test OK" value={st?.zip_test_ok} />
        <Metric label="Safety Violations" value={st?.safety_violations_total} />
      </div>

      <EvidenceSection title="Validation Result">
        <JsonBlock value={vr} emptyText="No result" />
      </EvidenceSection>
      <EvidenceSection title="Validation Checks">
        <JsonBlock value={vr?.checks} emptyText="No checks" />
      </EvidenceSection>
      <EvidenceSection title="Validation Report">
        <TextViewer
          text={typeof latest?.validation_report === "string" ? latest.validation_report : null}
          emptyText="No report"
        />
      </EvidenceSection>
      <EvidenceSection title="Validation List">
        <JsonBlock value={vlist} emptyText="No list" />
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
