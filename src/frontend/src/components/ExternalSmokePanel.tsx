import { useCallback, useEffect, useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { getExternalSmokeStatus, runExternalSmoke } from "../lib/api/external";
import { JsonBlock } from "./JsonBlock";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

const DPABI_FUNCTIONS = [
  "y_Smooth",
  "y_Filter",
  "y_RegressOutImgCovariates",
  "y_alff_falff",
  "y_Reho",
  "y_ROItseries",
  "y_FC",
];

export default function ExternalSmokePanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const [target, setTarget] = useState("all");
  const [mode, setMode] = useState("manual_package");
  const [configPath, setConfigPath] = useState("examples/project_config.yaml");
  const [approved, setApproved] = useState(false);
  const [approvedBy, setApprovedBy] = useState("local-user");
  const [dpabiFunction, setDpabiFunction] = useState("y_Smooth");
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const payload = await getExternalSmokeStatus(baseUrl);
      setStatus(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [baseUrl]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Load backend-owned smoke status when the endpoint changes.
    void refresh();
  }, [refresh]);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const payload = await runExternalSmoke(baseUrl, {
        target,
        mode,
        config_path: configPath,
        approved,
        approved_by: approvedBy,
        dpabi_function: dpabiFunction,
      });
      setResult(payload);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const reportText = String(status?.report_text || "");
  const checklistText = String(status?.checklist_text || "");
  const commandsText = String(status?.commands_text || "");

  return (
    <div>
      {error ? <div className="errorBox">{error}</div> : null}
      <div className="formGrid">
        <label>
          {t("settings.smoke.target")}
          <select value={target} onChange={(event) => setTarget(event.target.value)}>
            <option value="all">SPM + DPABI</option>
            <option value="spm">SPM</option>
            <option value="dpabi">DPABI</option>
          </select>
        </label>
        <label>
          {t("settings.smoke.mode")}
          <select value={mode} onChange={(event) => setMode(event.target.value)}>
            <option value="manual_package">{t("settings.smoke.manualPackage")}</option>
            <option value="preflight">{t("settings.smoke.preflight")}</option>
            <option value="approved_smoke">{t("settings.smoke.approvedSmoke")}</option>
          </select>
        </label>
        <label>
          {t("settings.smoke.configPath")}
          <input value={configPath} onChange={(event) => setConfigPath(event.target.value)} />
        </label>
        <label>
          {t("settings.smoke.dpabiFunction")}
          <select value={dpabiFunction} onChange={(event) => setDpabiFunction(event.target.value)}>
            {DPABI_FUNCTIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("settings.smoke.approvedBy")}
          <input value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} />
        </label>
      </div>
      <div className="row">
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={approved}
            onChange={(event) => setApproved(event.target.checked)}
          />
          {t("settings.smoke.approveMatlab")}
        </label>
        <button onClick={run} disabled={busy}>
          {busy ? t("settings.smoke.running") : t("settings.smoke.run")}
        </button>
        <button onClick={refresh} disabled={busy}>
          {t("settings.smoke.refresh")}
        </button>
      </div>
      <h3>{t("settings.smoke.latest")}</h3>
      <JsonBlock value={status} emptyText={t("settings.smoke.noStatus")} />
      <h3>{t("settings.smoke.lastResult")}</h3>
      <JsonBlock value={result} emptyText={t("settings.smoke.noRun")} />
      <h3>{t("settings.smoke.checklist")}</h3>
      <TextViewer text={checklistText || t("settings.smoke.noChecklist")} />
      <h3>{t("settings.smoke.commands")}</h3>
      <TextViewer text={commandsText || t("settings.smoke.noCommands")} />
      <h3>{t("settings.smoke.report")}</h3>
      <TextViewer text={reportText || t("settings.smoke.noReport")} />
    </div>
  );
}
