import { Button } from "../../../components/ui";
import { useI18n } from "../../../i18n/useI18n";
import type { AgentTaskResponse } from "../../../lib/types/agentTask";
import type { LegacyWorkspace } from "../../navigation/workspaceModel";
import styles from "../AgentWorkspace.module.css";
import { TechnicalEvidence } from "./TechnicalEvidence";

export function TaskDetails({
  advancedMode,
  onOpenLegacyWorkspace,
  onOpenReviewedPlan,
  onOpenRuns,
  task,
}: {
  advancedMode: boolean;
  onOpenLegacyWorkspace: (workspace: LegacyWorkspace) => void;
  onOpenReviewedPlan: (reviewedPlanId: string) => void;
  onOpenRuns: () => void;
  task: AgentTaskResponse;
}) {
  const { t } = useI18n();
  const reviewedPlanId = task.technical_details?.reviewed_plan_id ?? null;
  return (
    <details className={styles.taskDetails}>
      <summary>{t("agent.taskDetails")}</summary>
      <div className={styles.taskDetailsBody}>
        <section>
          <h3>{t("agent.evidence")}</h3>
          {task.evidence_links.length ? (
            <ul className={styles.evidenceList}>
              {task.evidence_links.map((link) => (
                <li key={link.id}>
                  <BadgeLike available={link.available} />
                  <span>{link.label}</span>
                  <code>{link.uri}</code>
                </li>
              ))}
            </ul>
          ) : (
            <p>{t("agent.noEvidence")}</p>
          )}
          <div className={styles.detailActions}>
            <Button onClick={onOpenRuns} variant="secondary">
              {t("agent.openRuns")}
            </Button>
            <Button onClick={() => onOpenLegacyWorkspace("overview")} variant="ghost">
              {t("agent.compatOverview")}
            </Button>
            <Button onClick={() => onOpenLegacyWorkspace("data")} variant="ghost">
              {t("agent.compatData")}
            </Button>
            <Button
              onClick={() =>
                reviewedPlanId ? onOpenReviewedPlan(reviewedPlanId) : onOpenLegacyWorkspace("plan")
              }
              variant="ghost"
            >
              {t("agent.compatPlan")}
            </Button>
            <Button onClick={() => onOpenLegacyWorkspace("preprocessing")} variant="ghost">
              {t("agent.compatPreprocessing")}
            </Button>
            <Button onClick={() => onOpenLegacyWorkspace("qc")} variant="ghost">
              {t("agent.compatQc")}
            </Button>
            <Button onClick={() => onOpenLegacyWorkspace("results")} variant="ghost">
              {t("agent.compatResults")}
            </Button>
          </div>
        </section>
        {advancedMode && task.technical_details ? (
          <TechnicalEvidence details={task.technical_details} />
        ) : null}
      </div>
    </details>
  );
}

function BadgeLike({ available }: { available: boolean }) {
  const { t } = useI18n();
  return (
    <span className={available ? styles.evidenceAvailable : styles.evidenceMissing}>
      {available ? t("common.available") : t("common.unavailable")}
    </span>
  );
}
