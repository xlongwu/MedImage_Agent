import { useI18n } from "../i18n/useI18n";
import type {
  DicomConversionPreflightResponse,
  DicomConversionPrepareResponse,
  DicomConversionReleaseReadinessReport,
} from "../types";
import styles from "./DicomConversionExecutePanel.module.css";

type Props = {
  baseUrl: string;
  projectId: string;
  conversionRunId: string;
  readiness: DicomConversionReleaseReadinessReport | null;
  preflight: DicomConversionPreflightResponse | null;
  onPrepared?: (response: DicomConversionPrepareResponse) => void;
  onConversionRegistered?: () => void | Promise<void>;
};

/**
 * Production DICOM execution boundary.
 *
 * Direct execution from the Data workspace was retired because its legacy
 * endpoint is not an execution authority. Conversion must be planned and
 * approved through the canonical Agent lifecycle so the backend can bind an
 * Approval Summary, Execution Ticket and Execution Gateway dispatch. This
 * panel deliberately contains no prepare or execute action.
 */
export default function DicomConversionExecutePanel({
  conversionRunId,
  readiness,
  preflight,
}: Props) {
  const { t } = useI18n();
  const featureEnabled = import.meta.env.VITE_ENABLE_DICOM_EXECUTE_UI === "1";

  if (!featureEnabled) {
    return null;
  }

  const dependencyState =
    preflight == null
      ? "checking"
      : preflight.native_converter_available
        ? "available"
        : "unavailable";
  const dependencyVersions = Object.entries(preflight?.native_dependency_versions ?? {});

  return (
    <section className={styles.style001} aria-labelledby="dicom-controlled-execution-title">
      <h3 id="dicom-controlled-execution-title" className={styles.style002}>
        {t("technical.DicomConversionExecute.001")}
      </h3>

      <div className={styles.style003} role="status">
        <strong>{t("technical.DicomConversionExecute.controlled.title")}</strong>{" "}
        {t("technical.DicomConversionExecute.controlled.description")}
      </div>

      <div className={styles.controlledGrid}>
        <div className={styles.controlledItem}>
          <span className={styles.controlledLabel}>
            {t("technical.DicomConversionExecute.controlled.routeLabel")}
          </span>
          <strong>{t("technical.DicomConversionExecute.controlled.routeValue")}</strong>
          <span>{t("technical.DicomConversionExecute.controlled.routeDescription")}</span>
        </div>

        <div className={styles.controlledItem}>
          <span className={styles.controlledLabel}>
            {t("technical.DicomConversionExecute.controlled.dependenciesLabel")}
          </span>
          <strong
            className={
              dependencyState === "available"
                ? styles.dependencyAvailable
                : dependencyState === "unavailable"
                  ? styles.dependencyUnavailable
                  : styles.dependencyChecking
            }
          >
            {t(`technical.DicomConversionExecute.controlled.dependencies.${dependencyState}`)}
          </strong>
          <span>{t("technical.DicomConversionExecute.controlled.dependenciesRequired")}</span>
          {dependencyState === "unavailable" && (
            <span className={styles.dependencyNotice}>
              {t("technical.DicomConversionExecute.controlled.dependenciesMissing")}
            </span>
          )}
          {dependencyVersions.length > 0 && (
            <span className={styles.dependencyVersions}>
              {dependencyVersions.map(([name, version]) => `${name} ${version}`).join(" · ")}
            </span>
          )}
        </div>
      </div>

      <div className={styles.style004}>
        <h4 className={styles.style005}>
          {t("technical.DicomConversionExecute.controlled.safetyTitle")}
        </h4>
        <div className={styles.style006}>
          {t("technical.DicomConversionExecute.controlled.noDirectAction")}
        </div>
        <div className={styles.style006}>
          {t("technical.DicomConversionExecute.controlled.rawdataReadonly")}
        </div>
        <div className={styles.style006}>
          {t("technical.DicomConversionExecute.missing.safetyGates", {
            met: readiness?.gates_met ?? 0,
            total: readiness?.gates_total ?? 32,
          })}
        </div>
        {conversionRunId && (
          <div className={styles.runContext}>
            {t("technical.DicomConversionExecute.label.run")}: <code>{conversionRunId}</code>
          </div>
        )}
      </div>
    </section>
  );
}
