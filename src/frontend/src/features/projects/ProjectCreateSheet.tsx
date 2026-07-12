import { useEffect, useMemo, useState } from "react";
import type { ProjectCreateResponse } from "../../types";
import { Button, Sheet } from "../../components/ui";
import { useI18n } from "../../i18n/useI18n";
import styles from "./ProjectCreateSheet.module.css";

type InspectionFocus = "raw_dicom" | "bids_or_derivatives";

export interface ProjectCreateSheetProps {
  error: string;
  loading: boolean;
  onCreate: (
    path: string,
    options?: { projectName?: string },
  ) => Promise<ProjectCreateResponse | null>;
  onOpenChange: (open: boolean) => void;
  onSelectDirectory: () => Promise<string | null>;
  open: boolean;
}

export function ProjectCreateSheet({
  error,
  loading,
  onCreate,
  onOpenChange,
  onSelectDirectory,
  open,
}: ProjectCreateSheetProps) {
  const { t } = useI18n();
  const steps = [
    { title: t("projects.create.step.basics"), description: t("projects.create.step.name") },
    { title: t("projects.create.step.source"), description: t("projects.create.step.inspect") },
    { title: t("projects.create.step.confirm"), description: t("projects.create.step.review") },
  ];
  const [stepIndex, setStepIndex] = useState(0);
  const [projectName, setProjectName] = useState("");
  const [inspectionFocus, setInspectionFocus] = useState<InspectionFocus>("raw_dicom");
  const [selectedPath, setSelectedPath] = useState("");
  const [localError, setLocalError] = useState("");
  const [selecting, setSelecting] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect -- A controlled Sheet close is the reset boundary for this multi-step form. */
  useEffect(() => {
    if (!open) {
      setStepIndex(0);
      setProjectName("");
      setInspectionFocus("raw_dicom");
      setSelectedPath("");
      setLocalError("");
      setSelecting(false);
    }
  }, [open]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const displayName = useMemo(
    () => projectName.trim() || directoryBasename(selectedPath) || t("projects.create.defaultName"),
    [projectName, selectedPath, t],
  );
  const visibleError = localError || error;
  const canContinueFromSource = Boolean(selectedPath.trim());

  const handleSelectDirectory = async () => {
    setLocalError("");
    setSelecting(true);
    try {
      const path = await onSelectDirectory();
      if (!path) return;
      setSelectedPath(path);
      if (!projectName.trim()) {
        setProjectName(directoryBasename(path));
      }
    } finally {
      setSelecting(false);
    }
  };

  const handleNext = () => {
    setLocalError("");
    if (stepIndex === 1 && !canContinueFromSource) {
      setLocalError(t("projects.create.reviewDirectoryError"));
      return;
    }
    setStepIndex((current) => Math.min(current + 1, steps.length - 1));
  };

  const handleCreate = async () => {
    if (!selectedPath.trim()) {
      setLocalError(t("projects.create.createDirectoryError"));
      setStepIndex(1);
      return;
    }
    const result = await onCreate(selectedPath, { projectName: projectName.trim() || undefined });
    if (result) {
      onOpenChange(false);
    }
  };

  return (
    <Sheet
      description={t("projects.create.description")}
      footer={
        <div className={styles.footer}>
          <Button
            disabled={loading || selecting}
            onClick={() => onOpenChange(false)}
            variant="ghost"
          >
            {t("projects.create.cancel")}
          </Button>
          <div className={styles.footerGroup}>
            {stepIndex > 0 ? (
              <Button
                disabled={loading || selecting}
                onClick={() => setStepIndex((current) => Math.max(current - 1, 0))}
                variant="secondary"
              >
                {t("projects.create.back")}
              </Button>
            ) : null}
            {stepIndex < steps.length - 1 ? (
              <Button disabled={loading || selecting} onClick={handleNext} variant="primary">
                {t("projects.create.continue")}
              </Button>
            ) : (
              <Button disabled={loading || selecting} onClick={handleCreate} variant="primary">
                {loading ? t("projects.create.creating") : t("projects.create.submit")}
              </Button>
            )}
          </div>
        </div>
      }
      onOpenChange={onOpenChange}
      open={open}
      title={t("projects.create.title")}
    >
      <div className={styles.steps} aria-label={t("projects.create.steps")}>
        {steps.map((step, index) => (
          <div
            key={step.title}
            className={`${styles.step} ${index === stepIndex ? styles.stepActive : ""}`}
            aria-current={index === stepIndex ? "step" : undefined}
          >
            <strong>{step.title}</strong>
            <span>{step.description}</span>
          </div>
        ))}
      </div>

      <div className={styles.body}>
        {stepIndex === 0 ? (
          <>
            <div className={styles.field}>
              <label htmlFor="project-create-name">{t("projects.create.projectName")}</label>
              <input
                id="project-create-name"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                placeholder={t("projects.create.namePlaceholder")}
              />
            </div>
            <p className={styles.hint}>{t("projects.create.nameHint")}</p>
            <div className={styles.noteBox}>
              <strong>{t("projects.create.namingSource")}</strong>
              <span>{t("projects.create.namingDescription")}</span>
            </div>
          </>
        ) : null}

        {stepIndex === 1 ? (
          <>
            <div className={styles.sectionLabel}>{t("projects.create.inspectionFocus")}</div>
            <div className={styles.sourceGrid}>
              <button
                type="button"
                className={styles.sourceOption}
                aria-pressed={inspectionFocus === "raw_dicom"}
                onClick={() => setInspectionFocus("raw_dicom")}
              >
                <strong>{t("projects.create.rawDicom")}</strong>
                <span>{t("projects.create.rawDicomDescription")}</span>
              </button>
              <button
                type="button"
                className={styles.sourceOption}
                aria-pressed={inspectionFocus === "bids_or_derivatives"}
                onClick={() => setInspectionFocus("bids_or_derivatives")}
              >
                <strong>{t("projects.create.bids")}</strong>
                <span>{t("projects.create.bidsDescription")}</span>
              </button>
            </div>
            <p className={styles.hint}>{t("projects.create.inspectionHint")}</p>
            <div className={styles.pathBox}>
              <Button disabled={selecting || loading} onClick={handleSelectDirectory}>
                {selecting ? t("projects.create.selecting") : t("projects.create.selectDirectory")}
              </Button>
              <span className={styles.pathValue}>
                {selectedPath || t("projects.create.noDirectory")}
              </span>
            </div>
          </>
        ) : null}

        {stepIndex === 2 ? (
          <dl className={styles.confirmList}>
            <div>
              <dt>{t("projects.create.step.name")}</dt>
              <dd>{displayName}</dd>
            </div>
            <div>
              <dt>{t("projects.create.inspectionFocus")}</dt>
              <dd>
                {inspectionFocus === "raw_dicom"
                  ? t("projects.create.rawDicom")
                  : t("projects.create.bids")}
              </dd>
            </div>
            <div>
              <dt>{t("projects.create.directory")}</dt>
              <dd>{selectedPath}</dd>
            </div>
            <div>
              <dt>{t("projects.create.copyMode")}</dt>
              <dd>{t("projects.create.referenceFiles")}</dd>
            </div>
            <div>
              <dt>{t("projects.create.inspection")}</dt>
              <dd>{t("projects.create.inspectionAuthority")}</dd>
            </div>
            <div>
              <dt>{t("projects.create.safety")}</dt>
              <dd>{t("projects.create.safetyDescription")}</dd>
            </div>
          </dl>
        ) : null}

        {visibleError ? (
          <div className={styles.error} role="alert">
            {t("projects.create.failure")} {visibleError}
          </div>
        ) : null}
      </div>
    </Sheet>
  );
}

function directoryBasename(path: string): string {
  return path.replace(/\\/g, "/").split("/").filter(Boolean).pop() ?? "";
}
