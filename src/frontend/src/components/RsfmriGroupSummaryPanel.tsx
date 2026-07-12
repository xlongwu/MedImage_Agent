import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getRsfmriGroupSummary, runRsfmriGroupSummary } from "../lib/api/rsfmri";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
function fmt(v: unknown, d = 4) {
  if (v === null || v === undefined) return "-";
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(d) : String(v);
}
export function RsfmriGroupSummaryPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");
  async function handleRun() {
    setStatus("RUNNING");
    setError("");
    try {
      const r = await runRsfmriGroupSummary(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_group_summary.yaml",
      });
      setResult(r);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  async function handleLoad() {
    setStatus("LOADING");
    setError("");
    try {
      setLoaded(await getRsfmriGroupSummary(baseUrl));
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  const dd = loaded?.dashboard_data as Record<string, unknown> | undefined;
  const cc = dd?.summary_cards as Record<string, unknown> | undefined;
  const mm = dd?.metric_means as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>{t("technical.group.generate")}</button>
        <button onClick={handleLoad}>{t("technical.group.load")}</button>
        <StatusBadge status={status} />
      </div>
      {error ? <div className="errorBox">{error}</div> : null}
      <div className="metricGrid">
        <div className="metricCard">
          <span>{t("technical.subjects")}</span>
          <strong>{String(cc?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.group.withQc")}</span>
          <strong>{String(cc?.subjects_with_any_qc ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.group.warnings")}</span>
          <strong>{String(cc?.warnings_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.group.errors")}</span>
          <strong>{String(cc?.errors_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.group.contracts")}</span>
          <strong>{String(cc?.contracts_total ?? "-")}</strong>
        </div>
      </div>
      <div className="metricGrid">
        <div className="metricCard">
          <span>{t("technical.group.meanFd")}</span>
          <strong>{fmt(mm?.mean_fd)}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.group.meanFalff")}</span>
          <strong>{fmt(mm?.falff_mean)}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.group.meanReho")}</span>
          <strong>{fmt(mm?.reho_mean)}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.group.meanFc")}</span>
          <strong>{fmt(mm?.fc_roi_count, 2)}</strong>
        </div>
      </div>
      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />
      <h3>{t("technical.group.datasetSummary")}</h3>
      <JsonBlock value={loaded?.dataset_summary} emptyText={t("technical.noSummary")} />
      <h3>{t("technical.group.dashboard")}</h3>
      <JsonBlock value={loaded?.dashboard_data} emptyText={t("technical.group.noDashboard")} />
      <h3>{t("technical.group.completeness")}</h3>
      <JsonBlock
        value={loaded?.pipeline_completeness}
        emptyText={t("technical.group.noCompleteness")}
      />
      <h3>{t("technical.group.contractsOverview")}</h3>
      <JsonBlock value={loaded?.contracts_overview} emptyText={t("technical.group.noContracts")} />
      <h3>{t("technical.group.csv")}</h3>
      <JsonBlock
        value={{ path: loaded?.subject_metrics_table_path }}
        emptyText={t("technical.group.noCsv")}
      />
      <h3>{t("technical.report")}</h3>
      <TextViewer
        text={
          typeof loaded?.dataset_summary_report === "string" ? loaded.dataset_summary_report : null
        }
        emptyText={t("technical.noReport")}
      />
    </div>
  );
}
