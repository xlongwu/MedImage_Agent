import { useState } from "react";

import { getDatasetEvaluationReport } from "../lib/api/legacy";
import { deriveReportViewerEvidence } from "../lib/reportEvidence";
import type { DatasetEvaluationReport } from "../types";
import { EvidenceBadge } from "./domain/EvidenceBadge";
import { JsonBlock } from "./JsonBlock";
import styles from "./ReportEvidence.module.css";
import { TextViewer } from "./TextViewer";
import { Button, Card, SegmentedControl } from "./ui";

type Props = {
  baseUrl: string;
};

type ReportTab = "summary" | "markdown" | "csv" | "exclusion" | "html";

const reportTabs = [
  { label: "Summary", value: "summary" },
  { label: "Markdown", value: "markdown" },
  { label: "QC CSV", value: "csv" },
  { label: "Exclusion", value: "exclusion" },
  { label: "HTML Source", value: "html" },
];

export function ReportViewer({ baseUrl }: Props) {
  const [report, setReport] = useState<DatasetEvaluationReport | null>(null);
  const [activeTab, setActiveTab] = useState<ReportTab>("summary");
  const [error, setError] = useState("");
  const evidence = deriveReportViewerEvidence(report);

  async function refreshReport() {
    setError("");
    try {
      const result = await getDatasetEvaluationReport(baseUrl);
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <Card className={styles.panel} tone="muted">
      <div className={styles.header}>
        <div className={styles.headerText}>
          <h2>Dataset report</h2>
          <p>Report tabs reflect backend-loaded content and do not imply validation.</p>
        </div>
        <div className={styles.evidenceGroup}>
          <EvidenceBadge level={evidence.level} />
          <Button onClick={refreshReport} variant="secondary">
            Refresh report
          </Button>
        </div>
      </div>
      <p className={styles.evidenceDetail}>{evidence.detail}</p>

      <SegmentedControl
        aria-label="Report sections"
        options={reportTabs}
        value={activeTab}
        onChange={(value) => setActiveTab(value as ReportTab)}
      />

      {error ? (
        <div className={styles.errorLine} role="alert">
          <strong>Report error</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {activeTab === "summary" ? (
        <JsonBlock value={report?.dataset_summary} emptyText="No dataset summary loaded." />
      ) : null}

      {activeTab === "markdown" ? (
        <TextViewer text={report?.report_markdown} emptyText="No Markdown report content." />
      ) : null}

      {activeTab === "csv" ? (
        <TextViewer text={report?.subject_qc_table} emptyText="No subject QC table content." />
      ) : null}

      {activeTab === "exclusion" ? (
        <TextViewer
          text={report?.exclusion_recommendations}
          emptyText="No exclusion recommendations content."
        />
      ) : null}

      {activeTab === "html" ? (
        <TextViewer text={report?.report_html} emptyText="No HTML report content." />
      ) : null}
    </Card>
  );
}
