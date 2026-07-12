import { Badge, Button, Card, EmptyState } from "../../components/ui";
import { useI18n } from "../../i18n/useI18n";
import { formatDate, formatNumber } from "../../i18n/format";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { TaskLogEntry } from "../../lib/types/task";
import type { ProjectWorkspace } from "../navigation/workspaceModel";
import styles from "./OverviewWorkspace.module.css";

export function OverviewWorkspace({
  inventory,
  onNavigate,
  tasks,
}: {
  inventory: ProjectInventory | null;
  onNavigate: (workspace: ProjectWorkspace) => void;
  tasks: TaskLogEntry[];
}) {
  const { locale, t } = useI18n();

  if (!inventory) {
    return (
      <EmptyState description={t("common.loading")} title={t("overview.projectUnavailable")} />
    );
  }

  const completed = tasks.filter((task) => task.status === "completed").length;
  const failed = tasks.filter((task) => task.status === "failed").length;
  const running = tasks.filter((task) => task.status === "running").length;
  const recommendation = getRecommendation(inventory, tasks);

  return (
    <section className={styles.workspace} aria-labelledby="overview-title">
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>{t("overview.title")}</p>
          <h1 id="overview-title">{inventory.projectName}</h1>
          <div className={styles.contextLine}>
            <Badge tone={dataTone(inventory)}>{inventory.dataStateLabel}</Badge>
            <span>{inventory.modality}</span>
            <span>{inventory.stateSentence}</span>
          </div>
        </div>
      </header>

      <Card className={styles.nextStep}>
        <div>
          <span className={styles.kicker}>{t("overview.nextStep")}</span>
          <h2>{recommendation.title}</h2>
          <p>{recommendation.description}</p>
        </div>
        <Button onClick={() => onNavigate(recommendation.workspace)} variant="primary">
          {recommendation.action}
        </Button>
      </Card>

      <div className={styles.metrics} aria-label={t("overview.inventory")}>
        <Metric
          label={t("projects.subjects")}
          value={formatNumber(locale, inventory.convertedSubjects)}
        />
        <Metric label="DICOM series" value={formatNumber(locale, inventory.dicomSeriesCount)} />
        <Metric label="NIfTI files" value={formatNumber(locale, inventory.niftiFileCount)} />
        <Metric label={t("overview.runTotals")} value={formatNumber(locale, tasks.length)} />
        <Metric
          label={t("common.completed")}
          tone="success"
          value={formatNumber(locale, completed)}
        />
        <Metric label="Running" tone="info" value={formatNumber(locale, running)} />
        <Metric
          label="Failed"
          tone={failed ? "danger" : "neutral"}
          value={formatNumber(locale, failed)}
        />
      </div>

      <Card className={styles.activity}>
        <div className={styles.sectionHeading}>
          <h2>{t("overview.activity")}</h2>
          <Button onClick={() => onNavigate("runs")} size="sm" variant="ghost">
            {t("nav.runs")}
          </Button>
        </div>
        {tasks.length ? (
          <ol className={styles.activityList}>
            {tasks.slice(0, 5).map((task) => (
              <li key={task.id}>
                <span className={styles.activityDot} data-status={task.status} />
                <div>
                  <strong>{task.run_name || task.pipeline || task.id}</strong>
                  <span>{task.pipeline}</span>
                </div>
                <Badge tone={taskTone(task.status)}>{task.status}</Badge>
                <time dateTime={task.started_at}>{formatDate(locale, task.started_at)}</time>
              </li>
            ))}
          </ol>
        ) : (
          <p className={styles.emptyActivity}>{t("overview.noActivity")}</p>
        )}
      </Card>
    </section>
  );
}

function Metric({
  label,
  tone = "neutral",
  value,
}: {
  label: string;
  tone?: "neutral" | "info" | "success" | "danger";
  value: string;
}) {
  return (
    <Card className={styles.metric} data-tone={tone}>
      <span>{label}</span>
      <strong>{value}</strong>
    </Card>
  );
}

function getRecommendation(inventory: ProjectInventory, tasks: TaskLogEntry[]) {
  const activeOrFailed = tasks.some(
    (task) => task.status === "running" || task.status === "failed",
  );
  if (activeOrFailed) {
    return {
      action: "Review runs",
      description: "A running or failed task has backend evidence that may need attention.",
      title: "Inspect current run activity",
      workspace: "runs" as const,
    };
  }
  if (inventory.dataState === "raw_dicom" || inventory.dataState === "mixed") {
    return {
      action: "Review data",
      description:
        "Prepare a read-only conversion plan and verify release readiness before execution.",
      title: "Review detected DICOM data",
      workspace: "data" as const,
    };
  }
  if (inventory.dataState === "converted_bids") {
    return {
      action: "Review plan",
      description: "Review and save the preprocessing plan before any approved execution.",
      title: "Configure the reviewed preprocessing plan",
      workspace: "plan" as const,
    };
  }
  return {
    action: "Open data workspace",
    description:
      "Reference verified local data before planning preprocessing or scientific analysis.",
    title: "Add project data",
    workspace: "data" as const,
  };
}

function dataTone(inventory: ProjectInventory): "neutral" | "success" | "warning" {
  if (inventory.dataState === "converted_bids") return "success";
  if (inventory.dataState === "raw_dicom" || inventory.dataState === "mixed") return "warning";
  return "neutral";
}

function taskTone(status: TaskLogEntry["status"]): "neutral" | "info" | "success" | "danger" {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "running") return "info";
  return "neutral";
}
