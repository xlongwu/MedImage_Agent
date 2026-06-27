import { Badge, Card } from "../../components/ui";
import type { ConversionDryRunResponse } from "../../types";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import styles from "./ConversionStepper.module.css";

type StepState = "completed" | "current" | "available" | "blocked";

type ConversionStep = {
  approval: string;
  blocker: string;
  input: string;
  label: string;
  output: string;
  state: StepState;
  writes: string;
};

export interface ConversionStepperProps {
  dryRun: ConversionDryRunResponse | null;
  error: string;
  inventory: ProjectInventory;
}

export function ConversionStepper({ dryRun, error, inventory }: ConversionStepperProps) {
  const steps = buildSteps(inventory, dryRun);

  return (
    <Card className={styles.card}>
      <div className={styles.header}>
        <div>
          <h3>Conversion stepper</h3>
          <p>Six reviewed stages from source detection to output registration.</p>
        </div>
      </div>

      {!dryRun && inventory.hasRawDicom ? (
        <div className={styles.note}>
          Start the no-write dry-run from the DICOM series browser. This stepper then tracks the
          reviewed mapping, safety review, and output registration stages without running external
          converters.
        </div>
      ) : null}
      {error ? (
        <div className={styles.error} role="alert">
          {error}
        </div>
      ) : null}
      {dryRun ? (
        <div className={styles.statusNote} aria-label="Dry-run stepper status">
          <strong>Dry-run status: {dryRun.status}</strong>
          <span>
            {dryRun.blocking_issues.length > 0
              ? `${dryRun.blocking_issues.length} blocking issue(s) must be resolved before safety review.`
              : dryRun.warnings.length > 0
                ? `${dryRun.warnings.length} warning(s) require human review.`
                : "Mappings are ready for human review; no conversion has run."}
          </span>
        </div>
      ) : null}

      <ol className={styles.stepList} aria-label="DICOM conversion steps">
        {steps.map((step, index) => (
          <li className={styles.step} key={step.label}>
            <span className={styles.stepIndex}>{index + 1}</span>
            <span className={styles.stepBody}>
              <span className={styles.stepTitle}>
                <strong>{step.label}</strong>
                <Badge tone={stepTone(step.state)} size="sm">
                  {step.state}
                </Badge>
              </span>
              <dl className={styles.facts}>
                <div className={styles.fact}>
                  <dt>Input</dt>
                  <dd title={step.input}>{step.input}</dd>
                </div>
                <div className={styles.fact}>
                  <dt>Output</dt>
                  <dd title={step.output}>{step.output}</dd>
                </div>
                <div className={styles.fact}>
                  <dt>Writes</dt>
                  <dd>{step.writes}</dd>
                </div>
                <div className={styles.fact}>
                  <dt>Approval</dt>
                  <dd>{step.approval}</dd>
                </div>
              </dl>
              {step.blocker ? <span className={styles.blocking}>{step.blocker}</span> : null}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function buildSteps(
  inventory: ProjectInventory,
  dryRun: ConversionDryRunResponse | null,
): ConversionStep[] {
  const hasDryRun = Boolean(dryRun);
  const dryRunReady = dryRun?.status === "ready" || dryRun?.status === "warning";
  const hasMappings = (dryRun?.mapping_preview.length ?? 0) > 0;
  const hasManualMappings = Boolean(
    dryRun?.mapping_preview.some(
      (mapping) => mapping.confidence === "manual_required" || mapping.confidence === "low",
    ),
  );
  const hasBlocking = (dryRun?.blocking_issues.length ?? 0) > 0;
  const firstBlockingIssue = dryRun?.blocking_issues[0] ?? "";
  const outputRoot = dryRun?.output_root_preview || dryRun?.output_root_name || "BIDS output root";
  const mappingState: StepState = hasMappings
    ? hasManualMappings
      ? "current"
      : "completed"
    : inventory.hasRawDicom
      ? "current"
      : "blocked";
  const dryRunState: StepState = hasBlocking
    ? "blocked"
    : dryRunReady
      ? "completed"
      : inventory.hasRawDicom
        ? "available"
        : "blocked";

  return [
    {
      label: "Source Detection",
      state: inventory.hasRawDicom ? "completed" : "current",
      input: "Project rawdata and readiness diagnostics",
      output: `${inventory.rawDicomCandidates} subject candidate(s), ${inventory.dicomSeriesCount} series`,
      writes: "No writes",
      approval: "Not required",
      blocker: inventory.hasRawDicom ? "" : "Import or reference raw DICOM data first.",
    },
    {
      label: "Series Mapping",
      state: mappingState,
      input: "Dry-run mapping preview",
      output: hasMappings
        ? `${dryRun?.mapping_preview.length ?? 0} suggested mapping(s)`
        : "Mapping not generated",
      writes: "No writes",
      approval: "Mapping review required",
      blocker: hasManualMappings
        ? "Low confidence or manual-required mappings need human review before approval material is prepared."
        : hasMappings
          ? ""
          : "Generate a dry-run preview before approving mappings.",
    },
    {
      label: "Dry Run Preview",
      state: dryRunState,
      input: "Read-only DICOM / loose NIfTI sources",
      output: hasDryRun ? outputRoot : "Preview package pending",
      writes: "No writes",
      approval: "Not execution approval",
      blocker: firstBlockingIssue,
    },
    {
      label: "Safety Review",
      state: hasDryRun && !hasBlocking ? "current" : "blocked",
      input: "Mappings, output root, overwrite policy, safety flags",
      output: "Approval package and operator confirmations",
      writes: "Plan/audit metadata only",
      approval: "Required",
      blocker: hasBlocking
        ? firstBlockingIssue
        : hasDryRun
          ? ""
          : "Dry-run preview is required first.",
    },
    {
      label: "Approved Conversion",
      state: "blocked",
      input: "Approved review package",
      output: "BIDS/NIfTI files from external converter",
      writes: "Writes outputs only after gate",
      approval: "Approval Gate",
      blocker:
        "External conversion remains disabled by default until explicitly enabled and approved.",
    },
    {
      label: "Output Registration",
      state: inventory.hasConvertedData ? "completed" : "blocked",
      input: "Generated outputs and manifest",
      output: "Registered BIDS/NIfTI inventory",
      writes: "Project metadata",
      approval: "After successful conversion",
      blocker: inventory.hasConvertedData ? "" : "No converted outputs registered yet.",
    },
  ];
}

function stepTone(state: StepState): "neutral" | "info" | "success" | "warning" {
  if (state === "completed") return "success";
  if (state === "current") return "info";
  if (state === "blocked") return "warning";
  return "neutral";
}
