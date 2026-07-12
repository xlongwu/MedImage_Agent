import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getRsfmriAlffFalff, runRsfmriAlffFalff } from "../lib/api/rsfmri";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = { baseUrl: string };
export function RsfmriAlffFalffPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");
  async function handleRun() {
    if (!window.confirm(t("technical.alff.confirm"))) return;
    setStatus("RUNNING");
    setError("");
    try {
      const r = await runRsfmriAlffFalff(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_alff_falff.yaml",
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
      const r = await getRsfmriAlffFalff(baseUrl);
      setLoaded(r);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  const s = loaded?.alff_falff_qc_summary as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          {t("technical.alff.run")}
        </button>
        <button onClick={handleLoad}>{t("technical.alff.load")}</button>
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
          <span>{t("technical.alff.mean")}</span>
          <strong>{s?.mean_falff_mean == null ? "-" : Number(s.mean_falff_mean).toFixed(4)}</strong>
        </div>
      </div>
      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />
      <h3>{t("technical.alff.summary")}</h3>
      <JsonBlock value={loaded?.alff_falff_qc_summary} emptyText={t("technical.noSummary")} />
      <h3>{t("technical.subjectQc")}</h3>
      <JsonBlock value={loaded?.subject_alff_falff_qc} emptyText={t("technical.noSubjectQc")} />
      <h3>{t("technical.subjectResults")}</h3>
      <JsonBlock value={loaded?.subject_alff_falff_results} emptyText={t("technical.noResults")} />
      <h3>{t("technical.gpuContract")}</h3>
      <JsonBlock value={loaded?.gpu_candidate_contract} emptyText={t("technical.noGpuContract")} />
      <h3>{t("technical.dpabiContract")}</h3>
      <JsonBlock
        value={loaded?.dpabi_backend_contract}
        emptyText={t("technical.noDpabiContract")}
      />
      <h3>{t("technical.report")}</h3>
      <TextViewer
        text={typeof loaded?.alff_falff_qc_report === "string" ? loaded.alff_falff_qc_report : null}
        emptyText={t("technical.noReport")}
      />
    </div>
  );
}
