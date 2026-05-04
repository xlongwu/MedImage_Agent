import { useState } from "react";
import { getDatasetEvaluationReport } from "../api";
import type { DatasetEvaluationReport } from "../types";
import { JsonBlock } from "./JsonBlock";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function ReportViewer({ baseUrl }: Props) {
  const [report, setReport] = useState<DatasetEvaluationReport | null>(null);
  const [activeTab, setActiveTab] = useState<
    "summary" | "markdown" | "csv" | "exclusion" | "html"
  >("summary");
  const [error, setError] = useState("");

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
    <div>
      <div className="row">
        <button onClick={refreshReport}>刷新报告</button>
        <button onClick={() => setActiveTab("summary")}>Summary</button>
        <button onClick={() => setActiveTab("markdown")}>Markdown</button>
        <button onClick={() => setActiveTab("csv")}>QC CSV</button>
        <button onClick={() => setActiveTab("exclusion")}>Exclusion</button>
        <button onClick={() => setActiveTab("html")}>HTML Source</button>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {activeTab === "summary" ? (
        <JsonBlock value={report?.dataset_summary} emptyText="暂无 dataset summary" />
      ) : null}

      {activeTab === "markdown" ? (
        <TextViewer text={report?.report_markdown} emptyText="暂无 Markdown 报告" />
      ) : null}

      {activeTab === "csv" ? (
        <TextViewer text={report?.subject_qc_table} emptyText="暂无 subject QC table" />
      ) : null}

      {activeTab === "exclusion" ? (
        <TextViewer
          text={report?.exclusion_recommendations}
          emptyText="暂无 exclusion recommendations"
        />
      ) : null}

      {activeTab === "html" ? (
        <TextViewer text={report?.report_html} emptyText="暂无 HTML 报告" />
      ) : null}
    </div>
  );
}
