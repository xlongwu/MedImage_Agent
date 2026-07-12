import { Badge, Card } from "../../components/ui";
import type { ConversionDryRunResponse } from "../../types";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import { useI18n } from "../../i18n/useI18n";
import type { I18nContextValue } from "../../i18n/context";
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
  const { t } = useI18n();
  const steps = buildSteps(inventory, dryRun, t);

  return (
    <Card className={styles.card}>
      <div className={styles.header}>
        <div>
          <h3>{t("data.stepper.title")}</h3>
          <p>{t("data.stepper.description")}</p>
        </div>
      </div>

      {!dryRun && inventory.hasRawDicom ? (
        <div className={styles.note}>{t("data.stepper.startNote")}</div>
      ) : null}
      {error ? (
        <div className={styles.error} role="alert">
          {error}
        </div>
      ) : null}
      {dryRun ? (
        <div className={styles.statusNote} aria-label={t("data.stepper.statusAria")}>
          <strong>{t("data.stepper.dryRunStatus", { status: dryRun.status })}</strong>
          <span>
            {dryRun.blocking_issues.length > 0
              ? t("data.stepper.blockerCount", { count: dryRun.blocking_issues.length })
              : dryRun.warnings.length > 0
                ? t("data.stepper.warningCount", { count: dryRun.warnings.length })
                : t("data.stepper.ready")}
          </span>
        </div>
      ) : null}

      <ol className={styles.stepList} aria-label={t("data.stepper.steps")}>
        {steps.map((step, index) => (
          <li className={styles.step} data-state={step.state} key={step.label}>
            <span className={styles.stepIndex}>{index + 1}</span>
            <span className={styles.stepBody}>
              <span className={styles.stepTitle}>
                <strong>{step.label}</strong>
                <Badge tone={stepTone(step.state)} size="sm">
                  {stepStateLabel(step.state, t)}
                </Badge>
              </span>
              <dl className={styles.facts}>
                <div className={styles.fact}>
                  <dt>{t("data.stepper.input")}</dt>
                  <dd title={step.input}>{step.input}</dd>
                </div>
                <div className={styles.fact}>
                  <dt>{t("data.stepper.output")}</dt>
                  <dd title={step.output}>{step.output}</dd>
                </div>
                <div className={styles.fact}>
                  <dt>{t("data.stepper.writes")}</dt>
                  <dd>{step.writes}</dd>
                </div>
                <div className={styles.fact}>
                  <dt>{t("data.stepper.approval")}</dt>
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
  t: I18nContextValue["t"],
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
  const outputRoot =
    dryRun?.output_root_preview || dryRun?.output_root_name || t("data.stepper.bidsOutputRoot");
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
      label: t("data.stepper.sourceDetection"),
      state: inventory.hasRawDicom ? "completed" : "current",
      input: t("data.stepper.sourceInput"),
      output: t("data.stepper.sourceOutput", {
        subjects: inventory.rawDicomCandidates,
        series: inventory.dicomSeriesCount,
      }),
      writes: t("data.stepper.noWrites"),
      approval: t("data.stepper.notRequired"),
      blocker: inventory.hasRawDicom ? "" : t("data.stepper.importRaw"),
    },
    {
      label: t("data.stepper.seriesMapping"),
      state: mappingState,
      input: t("data.stepper.mappingPreview"),
      output: hasMappings
        ? t("data.stepper.suggestedMappings", { count: dryRun?.mapping_preview.length ?? 0 })
        : t("data.stepper.mappingNotGenerated"),
      writes: t("data.stepper.noWrites"),
      approval: t("data.stepper.mappingReviewRequired"),
      blocker: hasManualMappings
        ? t("data.stepper.manualMappingBlocker")
        : hasMappings
          ? ""
          : t("data.stepper.generatePreviewBlocker"),
    },
    {
      label: t("data.stepper.dryRunPreview"),
      state: dryRunState,
      input: t("data.stepper.readOnlySources"),
      output: hasDryRun ? outputRoot : t("data.stepper.previewPending"),
      writes: t("data.stepper.noWrites"),
      approval: t("data.stepper.notExecutionApproval"),
      blocker: firstBlockingIssue,
    },
    {
      label: t("data.stepper.safetyReview"),
      state: hasDryRun && !hasBlocking ? "current" : "blocked",
      input: t("data.stepper.safetyInput"),
      output: t("data.stepper.safetyOutput"),
      writes: t("data.stepper.auditMetadataOnly"),
      approval: t("data.stepper.required"),
      blocker: hasBlocking ? firstBlockingIssue : hasDryRun ? "" : t("data.stepper.dryRunRequired"),
    },
    {
      label: t("data.stepper.approvedConversion"),
      state: "blocked",
      input: t("data.stepper.approvedPackage"),
      output: t("data.stepper.converterOutput"),
      writes: t("data.stepper.writesAfterGate"),
      approval: t("data.stepper.approvalGate"),
      blocker: t("data.stepper.externalDisabled"),
    },
    {
      label: t("data.stepper.outputRegistration"),
      state: inventory.hasConvertedData ? "completed" : "blocked",
      input: t("data.stepper.generatedManifest"),
      output: t("data.stepper.registeredInventory"),
      writes: t("data.stepper.projectMetadata"),
      approval: t("data.stepper.afterConversion"),
      blocker: inventory.hasConvertedData ? "" : t("data.stepper.noOutputs"),
    },
  ];
}

function stepTone(state: StepState): "neutral" | "info" | "success" | "warning" {
  if (state === "completed") return "success";
  if (state === "current") return "info";
  if (state === "blocked") return "warning";
  return "neutral";
}

function stepStateLabel(state: StepState, t: I18nContextValue["t"]): string {
  if (state === "completed") return t("common.completed");
  if (state === "current") return t("common.current");
  if (state === "blocked") return t("common.blocked");
  return t("common.available");
}
