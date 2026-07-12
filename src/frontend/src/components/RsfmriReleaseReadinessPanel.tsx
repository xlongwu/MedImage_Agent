import { useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getReleaseReadiness, runReleaseReadiness } from "../lib/api/deployment";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";
type Props = { baseUrl: string };
export function RsfmriReleaseReadinessPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  async function handleRun() {
    setStatus("RUNNING");
    try {
      setResult(
        await runReleaseReadiness(baseUrl, {
          project_config_path: "examples/project_config_dataset.yaml",
          pipeline_path: "examples/pipeline_rsfmri_release_readiness.yaml",
        }),
      );
      setStatus("SUCCESS");
    } catch {
      setStatus("ERROR");
    }
  }
  async function handleLoad() {
    setStatus("LOADING");
    try {
      setLoaded(await getReleaseReadiness(baseUrl));
      setStatus("LOADED");
    } catch {
      setStatus("ERROR");
    }
  }
  const r = loaded?.result as Record<string, unknown> | undefined;
  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>{t("technical.release.run")}</button>
        <button onClick={handleLoad}>{t("technical.release.load")}</button>
        <StatusBadge status={status} />
      </div>
      <div className="metricGrid">
        <div className="metricCard">
          <span>{t("technical.release.status")}</span>
          <strong>{String(r?.release_readiness_status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.release.checks")}</span>
          <strong>{String(r?.checks_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.pass")}</span>
          <strong>{String(r?.checks_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>{t("technical.fail")}</span>
          <strong>{String(r?.checks_fail ?? "-")}</strong>
        </div>
      </div>
      <h3>{t("technical.release.result")}</h3>
      <JsonBlock value={loaded?.result ?? result} emptyText={t("technical.release.noResult")} />
      <h3>{t("technical.release.checks")}</h3>
      <JsonBlock value={r?.checks} emptyText={t("technical.release.noChecks")} />
      <h3>{t("technical.report")}</h3>
      <TextViewer
        text={typeof loaded?.report === "string" ? loaded.report : null}
        emptyText={t("technical.noReport")}
      />
      <h3>{t("technical.release.dashboard")}</h3>
      <JsonBlock value={loaded?.dashboard} emptyText={t("technical.release.noDashboard")} />
    </div>
  );
}
