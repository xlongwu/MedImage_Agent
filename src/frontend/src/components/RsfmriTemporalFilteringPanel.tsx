import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getRsfmriTemporalFiltering, runRsfmriTemporalFiltering } from "../lib/api/rsfmri";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = { baseUrl: string };

export function RsfmriTemporalFilteringPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const operation = t("technical.filtering.operation");
  const name = t("technical.filtering.name");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    if (!window.confirm(t("technical.pythonConfirm", { operation }))) return;
    setStatus("RUNNING");
    setError("");
    try {
      const r = await runRsfmriTemporalFiltering(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_temporal_filtering.yaml",
        approved: true,
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
      const r = await getRsfmriTemporalFiltering(baseUrl);
      setLoaded(r);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const s = loaded?.temporal_filtering_qc_summary as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          {t("technical.approveRun", { operation })}
        </button>
        <button onClick={handleLoad}>{t("technical.loadResults", { name })}</button>
        <StatusBadge status={status} />
      </div>
      {error ? <div className="errorBox">{error}</div> : null}
      <div className="metricGrid">
        <div className="metricCard">
          <span>{t("technical.subjects")}</span>
          <strong>{String(s?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.pass")}</span>
          <strong>{String(s?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.warning")}</span>
          <strong>{String(s?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.fail")}</span>
          <strong>{String(s?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.varianceRatio")}</span>
          <strong>
            {s?.mean_variance_ratio == null ? "-" : Number(s.mean_variance_ratio).toFixed(4)}
          </strong>
        </div>
      </div>
      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />
      <h3>{t("technical.namedSummary", { name })}</h3>
      <JsonBlock
        value={loaded?.temporal_filtering_qc_summary}
        emptyText={t("technical.noNamedSummary", { name })}
      />
      <h3>{t("technical.namedSubject", { name })}</h3>
      <JsonBlock
        value={loaded?.subject_temporal_filtering_qc}
        emptyText={t("technical.noNamedSubject", { name })}
      />
      <h3>{t("technical.dpabiBackendContract")}</h3>
      <JsonBlock
        value={loaded?.dpabi_backend_contract}
        emptyText={t("technical.noDpabiBackendContract")}
      />
      <h3>{t("technical.namedReport", { name })}</h3>
      <TextViewer
        text={
          typeof loaded?.temporal_filtering_qc_report === "string"
            ? loaded.temporal_filtering_qc_report
            : null
        }
        emptyText={t("technical.noNamedReport", { name })}
      />
    </div>
  );
}
