import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getRsfmriSmoothingQc, runRsfmriSmoothingQc } from "../lib/api/rsfmri";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = { baseUrl: string };

export function RsfmriSmoothingQcPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const operation = t("technical.smoothing.operation");
  const name = t("technical.smoothing.name");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(t("technical.syntheticConfirm", { operation }));
    if (!confirmed) return;
    setStatus("RUNNING");
    setError("");
    try {
      const response = await runRsfmriSmoothingQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_smoothing_qc.yaml",
        approved: true,
      });
      setResult(response);
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
      const response = await getRsfmriSmoothingQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.smoothing_qc_summary as Record<string, unknown> | undefined;

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
          <strong>{String(summary?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.pass")}</span>
          <strong>{String(summary?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.warning")}</span>
          <strong>{String(summary?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.fail")}</span>
          <strong>{String(summary?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.smoothing.metric")}</span>
          <strong>
            {summary?.mean_variance_reduction_ratio == null
              ? "-"
              : Number(summary.mean_variance_reduction_ratio).toFixed(4)}
          </strong>
        </div>
      </div>
      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />
      <h3>{t("technical.namedSummary", { name })}</h3>
      <JsonBlock
        value={loaded?.smoothing_qc_summary}
        emptyText={t("technical.noNamedSummary", { name })}
      />
      <h3>{t("technical.namedSubject", { name })}</h3>
      <JsonBlock
        value={loaded?.subject_smoothing_qc}
        emptyText={t("technical.noNamedSubject", { name })}
      />
      <h3>{t("technical.namedReport", { name })}</h3>
      <TextViewer
        text={typeof loaded?.smoothing_qc_report === "string" ? loaded.smoothing_qc_report : null}
        emptyText={t("technical.noNamedReport", { name })}
      />
    </div>
  );
}
