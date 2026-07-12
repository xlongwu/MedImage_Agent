import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getRsfmriStRealignMotionQc, runRsfmriStRealignMotionQc } from "../lib/api/rsfmri";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriStRealignMotionChainPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(t("technical.chain.confirm"));

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriStRealignMotionQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_st_realign_motion_qc.yaml",
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
      const response = await getRsfmriStRealignMotionQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const chainSummary = loaded?.chain_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          {t("technical.chain.run")}
        </button>
        <button onClick={handleLoad}>{t("technical.chain.load")}</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>{t("technical.subjects")}</span>
          <strong>{String(chainSummary?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.pass")}</span>
          <strong>{String(chainSummary?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.warning")}</span>
          <strong>{String(chainSummary?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.fail")}</span>
          <strong>{String(chainSummary?.subjects_fail ?? "-")}</strong>
        </div>
      </div>

      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />

      <h3>{t("technical.chain.summary")}</h3>
      <JsonBlock value={loaded?.chain_summary} emptyText={t("technical.chain.noSummary")} />

      <h3>{t("technical.chain.sliceSummary")}</h3>
      <JsonBlock
        value={loaded?.slice_timing_qc_summary}
        emptyText={t("technical.chain.noSliceSummary")}
      />

      <h3>{t("technical.motion.summary")}</h3>
      <JsonBlock value={loaded?.motion_qc_summary} emptyText={t("technical.motion.noSummary")} />

      <h3>{t("technical.slice.subject")}</h3>
      <JsonBlock
        value={loaded?.subject_slice_timing_qc}
        emptyText={t("technical.slice.noSubject")}
      />

      <h3>{t("technical.motion.subject")}</h3>
      <JsonBlock value={loaded?.subject_motion_qc} emptyText={t("technical.motion.noSubject")} />

      <h3>{t("technical.chain.report")}</h3>
      <TextViewer
        text={typeof loaded?.chain_report === "string" ? loaded.chain_report : null}
        emptyText={t("technical.chain.noReport")}
      />
    </div>
  );
}
