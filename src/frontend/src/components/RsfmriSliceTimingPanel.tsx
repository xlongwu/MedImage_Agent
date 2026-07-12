import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getRsfmriSpmSliceTiming, runRsfmriSpmSliceTiming } from "../lib/api/rsfmri";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriSliceTimingPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(t("technical.slice.confirm"));

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriSpmSliceTiming(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_spm_slice_timing.yaml",
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
      const response = await getRsfmriSpmSliceTiming(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.slice_timing_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          {t("technical.slice.run")}
        </button>
        <button onClick={handleLoad}>{t("technical.slice.load")}</button>
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
          <span>{t("technical.fail")}</span>
          <strong>{String(summary?.subjects_fail ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.slice.meanTr")}</span>
          <strong>{summary?.mean_tr == null ? "-" : Number(summary.mean_tr).toFixed(4)}</strong>
        </div>
      </div>

      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />

      <h3>{t("technical.slice.summary")}</h3>
      <JsonBlock
        value={loaded?.slice_timing_qc_summary}
        emptyText={t("technical.slice.noSummary")}
      />

      <h3>{t("technical.slice.subject")}</h3>
      <JsonBlock
        value={loaded?.subject_slice_timing_qc}
        emptyText={t("technical.slice.noSubject")}
      />

      <h3>{t("technical.slice.report")}</h3>
      <TextViewer
        text={
          typeof loaded?.slice_timing_qc_report === "string" ? loaded.slice_timing_qc_report : null
        }
        emptyText={t("technical.slice.noReport")}
      />
    </div>
  );
}
