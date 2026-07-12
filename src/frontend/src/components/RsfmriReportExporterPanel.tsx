import { useState, type ReactNode } from "react";

import {
  getLatestRsfmriReportExport,
  listRsfmriReportExports,
  runRsfmriReportExport,
} from "../lib/api/rsfmri";
import { useI18n } from "../i18n/useI18n";
import { localizeReportEvidenceDetail } from "../i18n/reportEvidence";
import { deriveReportExportEvidence } from "../lib/reportEvidence";
import { EvidenceBadge } from "./domain/EvidenceBadge";
import { JsonBlock } from "./JsonBlock";
import styles from "./ReportEvidence.module.css";
import { TextViewer } from "./TextViewer";
import { Badge, Button, Card } from "./ui";

type Props = { baseUrl: string };
type RequestStatus = "IDLE" | "RUNNING" | "LOADING" | "REQUEST_COMPLETE" | "ERROR";

type Translate = ReturnType<typeof useI18n>["t"];

function requestLabel(status: RequestStatus, t: Translate): string {
  if (status === "RUNNING") return t("report.request.running");
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

export function RsfmriReportExporterPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [list, setList] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState<RequestStatus>("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");
    try {
      const runResult = await runRsfmriReportExport(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_report_exporter.yaml",
      });
      setResult(runResult);
      setStatus("LOADING");
      setLatest(await getLatestRsfmriReportExport(baseUrl));
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
      setLatest(await getLatestRsfmriReportExport(baseUrl));
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
      setList(await listRsfmriReportExports(baseUrl));
      setStatus("REQUEST_COMPLETE");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const evidence = deriveReportExportEvidence(latest, result);
  const es = latest?.export_summary as Record<string, unknown> | undefined;
  const m = latest?.manifest as Record<string, unknown> | undefined;

  return (
    <Card className={styles.panel} tone="muted">
      <div className={styles.header}>
        <div className={styles.headerText}>
          <h2>{t("report.export.title")}</h2>
          <p>{t("report.export.description")}</p>
        </div>
        <div className={styles.evidenceGroup}>
          <EvidenceBadge level={evidence.level} />
          <Badge tone={requestTone(status)}>{requestLabel(status, t)}</Badge>
        </div>
      </div>
      <p className={styles.evidenceDetail}>{localizeReportEvidenceDetail(evidence.detail, t)}</p>

      <div className={styles.toolbar}>
        <Button onClick={handleRun} disabled={status === "RUNNING"} variant="primary">
          {t("report.export.generate")}
        </Button>
        <Button onClick={loadLatest} disabled={status === "LOADING"} variant="secondary">
          {t("report.export.loadLatest")}
        </Button>
        <Button onClick={loadList} disabled={status === "LOADING"} variant="secondary">
          {t("report.export.list")}
        </Button>
      </div>

      {error ? (
        <div className={styles.errorLine} role="alert">
          <strong>{t("report.export.error")}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <div className={styles.metricGrid}>
        <Metric label={t("report.export.id")} value={latest?.export_id} />
        <Metric label={t("technical.subjects")} value={es?.exported_subjects_total} />
        <Metric label={t("report.export.files")} value={es?.exported_files_total} />
        <Metric
          label={t("report.export.zipSize")}
          value={es?.zip_size_bytes ?? latest?.zip_size_bytes}
        />
        <Metric
          label={t("report.export.manifestFiles")}
          value={Array.isArray(m?.files) ? m.files.length : "-"}
        />
      </div>

      <EvidenceSection title={t("technical.runSummary")}>
        <JsonBlock value={result} emptyText={t("technical.notRun")} />
      </EvidenceSection>
      <EvidenceSection title={t("report.export.summary")}>
        <JsonBlock value={latest?.export_summary} emptyText={t("technical.noSummary")} />
      </EvidenceSection>
      <EvidenceSection title={t("report.export.manifest")}>
        <JsonBlock value={latest?.manifest} emptyText={t("report.export.noManifest")} />
      </EvidenceSection>
      <EvidenceSection title={t("report.export.paths")}>
        <JsonBlock
          value={{ zip_path: latest?.zip_path, package_dir: latest?.package_dir }}
          emptyText={t("report.export.noPaths")}
        />
      </EvidenceSection>
      <EvidenceSection title={t("report.export.readme")}>
        <TextViewer
          text={typeof latest?.readme_md === "string" ? latest.readme_md : null}
          emptyText={t("report.export.noReadme")}
        />
      </EvidenceSection>
      <EvidenceSection title={t("report.export.index")}>
        <TextViewer
          text={typeof latest?.index_md === "string" ? latest.index_md : null}
          emptyText={t("report.export.noIndex")}
        />
      </EvidenceSection>
      <EvidenceSection title={t("report.export.listTitle")}>
        <JsonBlock value={list} emptyText={t("report.export.noExports")} />
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
