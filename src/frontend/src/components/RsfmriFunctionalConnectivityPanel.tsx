import { useState } from "react";
import {
  getRsfmriFunctionalConnectivity,
  runRsfmriFunctionalConnectivity,
} from "../lib/api/rsfmri";
import { useI18n } from "../i18n/useI18n";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
export function RsfmriFunctionalConnectivityPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");
  async function handleRun() {
    if (!window.confirm(t("technical.fc.confirm"))) return;
    setStatus("RUNNING");
    setError("");
    try {
      const r = await runRsfmriFunctionalConnectivity(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_functional_connectivity.yaml",
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
      setLoaded(await getRsfmriFunctionalConnectivity(baseUrl));
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }
  const s = loaded?.functional_connectivity_qc_summary as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          {t("technical.fc.run")}
        </button>
        <button onClick={handleLoad}>{t("technical.fc.load")}</button>
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
          <span>{t("technical.fc.mean")}</span>
          <strong>{s?.mean_roi_count == null ? "-" : Number(s.mean_roi_count).toFixed(2)}</strong>
        </div>
      </div>
      <h3>{t("technical.runSummary")}</h3>
      <JsonBlock value={result} emptyText={t("technical.notRun")} />
      <h3>{t("technical.fc.summary")}</h3>
      <JsonBlock
        value={loaded?.functional_connectivity_qc_summary}
        emptyText={t("technical.noSummary")}
      />
      <h3>{t("technical.subjectQc")}</h3>
      <JsonBlock
        value={loaded?.subject_functional_connectivity_qc}
        emptyText={t("technical.noSubjectQc")}
      />
      <h3>{t("technical.subjectResults")}</h3>
      <JsonBlock
        value={loaded?.subject_functional_connectivity_results}
        emptyText={t("technical.noResults")}
      />
      <h3>{t("technical.gpuContract")}</h3>
      <JsonBlock value={loaded?.gpu_candidate_contract} emptyText={t("technical.noContract")} />
      <h3>{t("technical.dpabiContract")}</h3>
      <JsonBlock value={loaded?.dpabi_backend_contract} emptyText={t("technical.noContract")} />
      <h3>{t("technical.report")}</h3>
      <TextViewer
        text={
          typeof loaded?.functional_connectivity_qc_report === "string"
            ? loaded.functional_connectivity_qc_report
            : null
        }
        emptyText={t("technical.noReport")}
      />
    </div>
  );
}
