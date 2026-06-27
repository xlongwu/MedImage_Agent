import { useState, type ReactNode } from "react";

import {
  getLatestRsfmriReportExport,
  listRsfmriReportExports,
  runRsfmriReportExport,
} from "../lib/api/legacy";
import { deriveReportExportEvidence } from "../lib/reportEvidence";
import { EvidenceBadge } from "./domain/EvidenceBadge";
import { JsonBlock } from "./JsonBlock";
import styles from "./ReportEvidence.module.css";
import { TextViewer } from "./TextViewer";
import { Badge, Button, Card } from "./ui";

type Props = { baseUrl: string };
type RequestStatus = "IDLE" | "RUNNING" | "LOADING" | "REQUEST_COMPLETE" | "ERROR";

function requestLabel(status: RequestStatus): string {
  if (status === "RUNNING") return "Request running";
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

export function RsfmriReportExporterPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [list, setList] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState<RequestStatus>("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");
    try {
      setResult(
        await runRsfmriReportExport(baseUrl, {
          project_config_path: "examples/project_config_dataset.yaml",
          pipeline_path: "examples/pipeline_rsfmri_report_exporter.yaml",
        }),
      );
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
          <h2>Report package export</h2>
          <p>Backend requests are metadata until package evidence is present.</p>
        </div>
        <div className={styles.evidenceGroup}>
          <EvidenceBadge level={evidence.level} />
          <Badge tone={requestTone(status)}>{requestLabel(status)}</Badge>
        </div>
      </div>
      <p className={styles.evidenceDetail}>{evidence.detail}</p>

      <div className={styles.toolbar}>
        <Button onClick={handleRun} disabled={status === "RUNNING"} variant="primary">
          Generate Report Package
        </Button>
        <Button onClick={loadLatest} disabled={status === "LOADING"} variant="secondary">
          Load Latest
        </Button>
        <Button onClick={loadList} disabled={status === "LOADING"} variant="secondary">
          List Exports
        </Button>
      </div>

      {error ? (
        <div className={styles.errorLine} role="alert">
          <strong>Export error</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <div className={styles.metricGrid}>
        <Metric label="Export ID" value={latest?.export_id} />
        <Metric label="Subjects" value={es?.exported_subjects_total} />
        <Metric label="Files" value={es?.exported_files_total} />
        <Metric label="ZIP Size" value={es?.zip_size_bytes} />
        <Metric label="Manifest Files" value={Array.isArray(m?.files) ? m.files.length : "-"} />
      </div>

      <EvidenceSection title="Run Summary">
        <JsonBlock value={result} emptyText="Not yet run" />
      </EvidenceSection>
      <EvidenceSection title="Export Summary">
        <JsonBlock value={latest?.export_summary} emptyText="No summary" />
      </EvidenceSection>
      <EvidenceSection title="Manifest">
        <JsonBlock value={latest?.manifest} emptyText="No manifest" />
      </EvidenceSection>
      <EvidenceSection title="Paths">
        <JsonBlock
          value={{ zip_path: latest?.zip_path, package_dir: latest?.package_dir }}
          emptyText="No paths"
        />
      </EvidenceSection>
      <EvidenceSection title="README">
        <TextViewer
          text={typeof latest?.readme_md === "string" ? latest.readme_md : null}
          emptyText="No README"
        />
      </EvidenceSection>
      <EvidenceSection title="Index">
        <TextViewer
          text={typeof latest?.index_md === "string" ? latest.index_md : null}
          emptyText="No index"
        />
      </EvidenceSection>
      <EvidenceSection title="Export List">
        <JsonBlock value={list} emptyText="No exports" />
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
