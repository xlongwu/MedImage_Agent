import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getRsfmriSpmRealignMotionQc, runRsfmriSpmRealignMotionQc } from "../lib/api/rsfmri";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriMotionQcPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(t("technical.motion.confirm"));

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriSpmRealignMotionQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_spm_realign_motion_qc.yaml",
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
      const response = await getRsfmriSpmRealignMotionQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = loaded?.motion_qc_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          {t("technical.motion.run")}
        </button>
        <button onClick={handleLoad}>{t("technical.motion.load")}</button>
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
          <span>{t("technical.motion.meanFd")}</span>
          <strong>
            {summary?.group_mean_fd == null ? "-" : Number(summary.group_mean_fd).toFixed(4)}
          </strong>
        </div>
      </div>

      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />

      <h3>{t("technical.motion.summary")}</h3>
      <JsonBlock value={loaded?.motion_qc_summary} emptyText={t("technical.motion.noSummary")} />

      <h3>{t("technical.motion.subject")}</h3>
      <JsonBlock value={loaded?.subject_motion_qc} emptyText={t("technical.motion.noSubject")} />

      <h3>{t("technical.motion.report")}</h3>
      <TextViewer
        text={typeof loaded?.motion_qc_report === "string" ? loaded.motion_qc_report : null}
        emptyText={t("technical.motion.noReport")}
      />
    </div>
  );
}
