import { Card } from "../../../components/ui";
import { useI18n } from "../../../i18n/useI18n";
import type { AgentTaskOutcome, AgentTaskPublicState } from "../../../lib/types/agentTask";
import styles from "../AgentWorkspace.module.css";

export function CurrentAction({
  action,
  outcome,
  state,
}: {
  action: string;
  outcome: AgentTaskOutcome | null;
  state: AgentTaskPublicState;
}) {
  const { t } = useI18n();
  const localizedAction =
    outcome === "canceled"
      ? t("agent.action.canceled")
      : state === "preparing"
        ? t("agent.action.preparing")
        : state === "waiting_for_user"
          ? t("agent.action.waiting")
          : state === "running"
            ? t("agent.action.running")
            : state === "completed"
              ? t("agent.action.completed")
              : state === "needs_attention"
                ? t("agent.action.attention")
                : action;
  return (
    <Card className={styles.currentAction} role="status" aria-live="polite">
      <span className={styles.stepNumber}>02</span>
      <div>
        <span className={styles.eyebrow}>{t("agent.currentAction")}</span>
        <h2 tabIndex={-1}>{localizedAction}</h2>
      </div>
      <span className={styles.pulse} aria-hidden="true" />
    </Card>
  );
}
