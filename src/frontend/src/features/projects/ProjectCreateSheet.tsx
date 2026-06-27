import { useEffect, useMemo, useState } from "react";
import type { ProjectCreateResponse } from "../../types";
import { Button, Sheet } from "../../components/ui";
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

const steps = [
  { title: "Basics", description: "Name" },
  { title: "Source", description: "Inspect" },
  { title: "Confirm", description: "Review" },
];

export function ProjectCreateSheet({
  error,
  loading,
  onCreate,
  onOpenChange,
  onSelectDirectory,
  open,
}: ProjectCreateSheetProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [projectName, setProjectName] = useState("");
  const [inspectionFocus, setInspectionFocus] = useState<InspectionFocus>("raw_dicom");
  const [selectedPath, setSelectedPath] = useState("");
  const [localError, setLocalError] = useState("");
  const [selecting, setSelecting] = useState(false);

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

  const displayName = useMemo(
    () => projectName.trim() || directoryBasename(selectedPath) || "New research project",
    [projectName, selectedPath],
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
      setLocalError("Select a local data directory before review.");
      return;
    }
    setStepIndex((current) => Math.min(current + 1, steps.length - 1));
  };

  const handleCreate = async () => {
    if (!selectedPath.trim()) {
      setLocalError("Select a local data directory before creating a project.");
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
      description="Create a research project by referencing an existing local data directory. Source files remain read-only."
      footer={
        <div className={styles.footer}>
          <Button
            disabled={loading || selecting}
            onClick={() => onOpenChange(false)}
            variant="ghost"
          >
            Cancel
          </Button>
          <div className={styles.footerGroup}>
            {stepIndex > 0 ? (
              <Button
                disabled={loading || selecting}
                onClick={() => setStepIndex((current) => Math.max(current - 1, 0))}
                variant="secondary"
              >
                Back
              </Button>
            ) : null}
            {stepIndex < steps.length - 1 ? (
              <Button disabled={loading || selecting} onClick={handleNext} variant="primary">
                Continue
              </Button>
            ) : (
              <Button disabled={loading || selecting} onClick={handleCreate} variant="primary">
                {loading ? "Creating..." : "Create project"}
              </Button>
            )}
          </div>
        </div>
      }
      onOpenChange={onOpenChange}
      open={open}
      title="Create research project"
    >
      <div className={styles.steps} aria-label="Project creation steps">
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
              <label htmlFor="project-create-name">Project name</label>
              <input
                id="project-create-name"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                placeholder="Derived from selected folder if left blank"
              />
            </div>
            <p className={styles.hint}>
              The project listing will point to your selected source directory. Rawdata and source
              research files are not modified by this import flow.
            </p>
            <div className={styles.noteBox}>
              <strong>Naming source</strong>
              <span>
                Leave the name blank to derive it from the selected folder. Duplicate names are
                checked by the backend; if creation fails, this sheet stays open for review.
              </span>
            </div>
          </>
        ) : null}

        {stepIndex === 1 ? (
          <>
            <div className={styles.sectionLabel}>Inspection focus</div>
            <div className={styles.sourceGrid}>
              <button
                type="button"
                className={styles.sourceOption}
                aria-pressed={inspectionFocus === "raw_dicom"}
                onClick={() => setInspectionFocus("raw_dicom")}
              >
                <strong>Raw DICOM</strong>
                <span>Expect series detection, conversion readiness, and safety review.</span>
              </button>
              <button
                type="button"
                className={styles.sourceOption}
                aria-pressed={inspectionFocus === "bids_or_derivatives"}
                onClick={() => setInspectionFocus("bids_or_derivatives")}
              >
                <strong>BIDS or derivatives</strong>
                <span>Expect BIDS/NIfTI inventory checks before workflow routing.</span>
              </button>
            </div>
            <p className={styles.hint}>
              This choice only guides the review copy. The backend inspection remains authoritative
              and determines the actual project data state.
            </p>
            <div className={styles.pathBox}>
              <Button disabled={selecting || loading} onClick={handleSelectDirectory}>
                {selecting ? "Selecting..." : "Select directory"}
              </Button>
              <span className={styles.pathValue}>{selectedPath || "No directory selected"}</span>
            </div>
          </>
        ) : null}

        {stepIndex === 2 ? (
          <dl className={styles.confirmList}>
            <div>
              <dt>Name</dt>
              <dd>{displayName}</dd>
            </div>
            <div>
              <dt>Inspection focus</dt>
              <dd>{inspectionFocus === "raw_dicom" ? "Raw DICOM" : "BIDS or derivatives"}</dd>
            </div>
            <div>
              <dt>Directory</dt>
              <dd>{selectedPath}</dd>
            </div>
            <div>
              <dt>Copy mode</dt>
              <dd>Reference existing files</dd>
            </div>
            <div>
              <dt>Inspection</dt>
              <dd>Required; backend determines project data state</dd>
            </div>
            <div>
              <dt>Safety</dt>
              <dd>
                Source data is referenced read-only; no conversion or preprocessing is executed
              </dd>
            </div>
          </dl>
        ) : null}

        {visibleError ? (
          <div className={styles.error} role="alert">
            Project was not created. Review the selected directory and name, then retry.{" "}
            {visibleError}
          </div>
        ) : null}
      </div>
    </Sheet>
  );
}

function directoryBasename(path: string): string {
  return path.replace(/\\/g, "/").split("/").filter(Boolean).pop() ?? "";
}
