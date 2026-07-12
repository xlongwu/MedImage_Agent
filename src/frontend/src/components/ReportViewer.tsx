import { useState } from "react";

import { useI18n } from "../i18n/useI18n";
import { localizeReportEvidenceDetail } from "../i18n/reportEvidence";
import { getDatasetEvaluationReport } from "../lib/api/qc";
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

export function ReportViewer({ baseUrl }: Props) {
  const { t } = useI18n();
  const [report, setReport] = useState<DatasetEvaluationReport | null>(null);
  const [activeTab, setActiveTab] = useState<ReportTab>("summary");
  const [error, setError] = useState("");
  const evidence = deriveReportViewerEvidence(report);
  const reportTabs = [
    { label: t("results.report.tab.summary"), value: "summary" },
    { label: t("results.report.tab.markdown"), value: "markdown" },
    { label: t("results.report.tab.csv"), value: "csv" },
    { label: t("results.report.tab.exclusion"), value: "exclusion" },
    { label: t("results.report.tab.html"), value: "html" },
  ];

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
          <h2>{t("results.report.title")}</h2>
          <p>{t("results.report.description")}</p>
        </div>
        <div className={styles.evidenceGroup}>
          <EvidenceBadge level={evidence.level} />
          <Button onClick={refreshReport} variant="secondary">
            {t("results.report.refresh")}
          </Button>
        </div>
      </div>
      <p className={styles.evidenceDetail}>{localizeReportEvidenceDetail(evidence.detail, t)}</p>

      <SegmentedControl
        aria-label={t("results.report.sections")}
        options={reportTabs}
        value={activeTab}
        onChange={(value) => setActiveTab(value as ReportTab)}
      />

      {error ? (
        <div className={styles.errorLine} role="alert">
          <strong>{t("results.report.error")}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {activeTab === "summary" ? (
        <JsonBlock value={report?.dataset_summary} emptyText={t("results.report.emptySummary")} />
      ) : null}

      {activeTab === "markdown" ? (
        <TextViewer text={report?.report_markdown} emptyText={t("results.report.emptyMarkdown")} />
      ) : null}

      {activeTab === "csv" ? (
        <TextViewer text={report?.subject_qc_table} emptyText={t("results.report.emptyCsv")} />
      ) : null}

      {activeTab === "exclusion" ? (
        <TextViewer
          text={report?.exclusion_recommendations}
          emptyText={t("results.report.emptyExclusion")}
        />
      ) : null}

      {activeTab === "html" ? (
        <TextViewer text={report?.report_html} emptyText={t("results.report.emptyHtml")} />
      ) : null}
    </Card>
  );
}
