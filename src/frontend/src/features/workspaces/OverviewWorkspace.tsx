import { Badge, Button, Card, EmptyState, Icon } from "../../components/ui";
import { useI18n } from "../../i18n/useI18n";
import { formatDate, formatNumber } from "../../i18n/format";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { AgentTaskResponse } from "../../lib/types/agentTask";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { ModelStatus } from "../../lib/types/model";
import type { ProjectDetail } from "../../lib/types/project";
import type { TaskLogEntry } from "../../lib/types/task";
import type { PlanNodeSelection } from "../../lib/workspaceSelection";
import type {
  LegacyWorkspace,
  LifecycleItem,
  ProjectWorkspace,
} from "../navigation/workspaceModel";
import styles from "./OverviewWorkspace.module.css";

export function OverviewWorkspace({
  agentTask,
  dataset,
  inventory,
  lifecycleItems,
  model,
  onNavigate,
  onSelectedPlanNodeChange,
  project,
  tasks,
}: {
  agentTask: AgentTaskResponse | null;
  dataset: DatasetSummary | null;
  inventory: ProjectInventory | null;
  lifecycleItems: LifecycleItem[];
  model: ModelStatus | null;
  onNavigate: (workspace: ProjectWorkspace | LegacyWorkspace) => void;
  onSelectedPlanNodeChange: (node: PlanNodeSelection | null) => void;
  project: ProjectDetail;
  tasks: TaskLogEntry[];
}) {
  const { locale, t } = useI18n();

  if (!inventory) {
    return (
      <EmptyState description={t("common.loading")} title={t("overview.projectUnavailable")} />
    );
  }

  const recommendation = getRecommendation(inventory, tasks, t);
  const latestTask = latestRun(tasks);
  const projectDirectory = safeDirectorySummary(project.metadata?.project_dir);
  const planNodes = agentTask?.technical_details?.node_ids ?? [];

  return (
    <section className={styles.workspace} aria-labelledby="overview-title">
      <header className={styles.projectHeader}>
        <div className={styles.projectIdentity}>
          <div className={styles.titleLine}>
            <span className={styles.projectGlyph}>
              <Icon height={20} name="folder" width={20} />
            </span>
            <div>
              <p className={styles.eyebrow}>{t("overview.title")}</p>
              <h1 id="overview-title">{inventory.projectName}</h1>
            </div>
          </div>
          <div className={styles.contextLine}>
            <Badge tone={dataTone(inventory)}>{inventory.dataStateLabel}</Badge>
            <span>{project.study_id}</span>
            <span>{inventory.modality}</span>
            <span>{projectDirectory || t("common.unavailable")}</span>
          </div>
        </div>
        <div className={styles.headerActions}>
          <Button onClick={() => onNavigate("settings")} variant="secondary">
            {t("overview.configure")}
          </Button>
          <Button onClick={() => onNavigate(latestTask ? "runs" : recommendation.workspace)}>
            {latestTask ? t("overview.reviewRun") : t("overview.openPlanWorkspace")}
          </Button>
        </div>
      </header>

      <WorkflowProgress items={lifecycleItems} onNavigate={onNavigate} />

      <div className={styles.dashboardGrid}>
        <div className={styles.primaryColumn}>
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

          <div className={styles.infoCards}>
            <InfoCard
              label={t("overview.datasetCard")}
              status={inventory.dataStateLabel}
              values={[
                [
                  t("projects.subjects"),
                  inventory.hasConvertedData
                    ? formatNumber(locale, inventory.convertedSubjects)
                    : t("common.unavailable"),
                ],
                [
                  t("overview.sequences"),
                  project.sequences.length
                    ? formatNumber(locale, project.sequences.length)
                    : t("common.unavailable"),
                ],
                [
                  t("overview.files"),
                  inventory.hasConvertedData
                    ? formatNumber(locale, inventory.niftiFileCount)
                    : inventory.hasRawDicom
                      ? formatNumber(locale, inventory.dicomFileCount)
                      : t("common.unavailable"),
                ],
                [
                  t("overview.storage"),
                  localizeOverviewValue(dataset?.total_size, t) || t("common.unavailable"),
                ],
              ]}
            />
            <InfoCard
              label={t("overview.modelCard")}
              status={localizeOverviewValue(model?.status, t) || t("common.unavailable")}
              values={[
                [
                  t("overview.modelName"),
                  localizeOverviewValue(model?.model_name, t) || t("common.unavailable"),
                ],
                [
                  t("overview.modelVersion"),
                  localizeOverviewValue(model?.version, t) || t("common.unavailable"),
                ],
                [
                  t("overview.modelContext"),
                  model ? t("overview.projectScoped") : t("common.unavailable"),
                ],
              ]}
            />
            <InfoCard
              label={t("overview.latestRunCard")}
              status={latestTask ? statusLabel(latestTask.status, t) : t("common.unavailable")}
              values={[
                [t("overview.runName"), latestTask?.run_name || t("common.unavailable")],
                [
                  t("overview.progress"),
                  latestTask ? `${Math.round(latestTask.progress)}%` : t("common.unavailable"),
                ],
                [
                  t("overview.started"),
                  latestTask ? formatDate(locale, latestTask.started_at) : t("common.unavailable"),
                ],
              ]}
            />
          </div>

          <PipelineDagPanel
            agentTask={agentTask}
            nodes={planNodes}
            onNavigate={onNavigate}
            onSelectedPlanNodeChange={onSelectedPlanNodeChange}
          />
        </div>

        <Card className={styles.activity}>
          <div className={styles.sectionHeading}>
            <div>
              <span>{t("overview.activity")}</span>
              <h2>{t("overview.recentRuns")}</h2>
            </div>
            <Button onClick={() => onNavigate("runs")} size="sm" variant="ghost">
              {t("nav.runs")}
            </Button>
          </div>
          {tasks.length ? (
            <ol className={styles.activityList}>
              {tasks.slice(0, 6).map((task) => (
                <li key={task.id}>
                  <span className={styles.activityDot} data-status={task.status} />
                  <div>
                    <strong>{task.run_name || task.pipeline || task.id}</strong>
                    <span>{task.pipeline}</span>
                    <time dateTime={task.started_at}>{formatDate(locale, task.started_at)}</time>
                  </div>
                  <Badge tone={taskTone(task.status)}>{statusLabel(task.status, t)}</Badge>
                </li>
              ))}
            </ol>
          ) : (
            <div className={styles.activityEmpty}>
              <Icon height={20} name="runs" width={20} />
              <p>{t("overview.noActivity")}</p>
            </div>
          )}
        </Card>
      </div>
    </section>
  );
}

function WorkflowProgress({
  items,
  onNavigate,
}: {
  items: LifecycleItem[];
  onNavigate: (workspace: LegacyWorkspace) => void;
}) {
  const { t } = useI18n();
  const labels: Record<LifecycleItem["id"], string> = {
    overview: t("nav.overview"),
    data: t("nav.data"),
    plan: t("nav.plan"),
    preprocessing: t("nav.preprocessing"),
    qc: t("nav.qc"),
    results: t("nav.results"),
  };
  return (
    <section className={styles.workflowProgress} aria-label={t("overview.workflowProgress")}>
      <div className={styles.sectionHeading}>
        <div>
          <span>{t("overview.workflow")}</span>
          <h2>{t("overview.workflowProgress")}</h2>
        </div>
      </div>
      <ol>
        {items.map((item, index) => (
          <li key={item.id} data-state={item.state}>
            {index ? <span className={styles.workflowConnector} aria-hidden="true" /> : null}
            <button
              aria-disabled={item.state === "blocked"}
              onClick={() => item.state !== "blocked" && onNavigate(item.id)}
              title={item.blockedReason ?? undefined}
              type="button"
            >
              <span className={styles.workflowNode} aria-hidden="true">
                {item.state === "completed" ? (
                  <Icon height={13} name="circle-check" width={13} />
                ) : (
                  index + 1
                )}
              </span>
              <span>
                <strong>{labels[item.id]}</strong>
                <small>{t(`overview.workflowState.${item.state}`)}</small>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

function InfoCard({
  label,
  status,
  values,
}: {
  label: string;
  status: string;
  values: string[][];
}) {
  return (
    <Card className={styles.infoCard}>
      <header>
        <h2>{label}</h2>
        <span>{status}</span>
      </header>
      <dl>
        {values.map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function PipelineDagPanel({
  agentTask,
  nodes,
  onNavigate,
  onSelectedPlanNodeChange,
}: {
  agentTask: AgentTaskResponse | null;
  nodes: string[];
  onNavigate: (workspace: LegacyWorkspace) => void;
  onSelectedPlanNodeChange: (node: PlanNodeSelection | null) => void;
}) {
  const { t } = useI18n();
  return (
    <Card className={styles.dagPanel}>
      <div className={styles.sectionHeading}>
        <div>
          <span>{t("overview.reviewedPlan")}</span>
          <h2>{t("overview.pipelineDag")}</h2>
        </div>
        <Badge tone={agentTask ? "info" : "neutral"}>
          {agentTask?.technical_details?.plan_hash
            ? t("overview.planBound")
            : t("common.unavailable")}
        </Badge>
      </div>
      {nodes.length ? (
        <div className={styles.dagScroller}>
          <ol className={styles.dag}>
            {nodes.map((node, index) => (
              <li key={`${node}-${index}`}>
                {index ? <span aria-hidden="true" /> : null}
                <button
                  onClick={() =>
                    onSelectedPlanNodeChange({
                      backend: agentTask?.technical_details?.backend?.selected ?? "unavailable",
                      detail: t("overview.nodePlannedDetail"),
                      id: node,
                      name: node,
                      risk: t("overview.reviewRequired"),
                    })
                  }
                  type="button"
                >
                  <Icon height={16} name="plan" width={16} />
                  <strong>{node}</strong>
                  <small>{t("overview.nodePlanned")}</small>
                </button>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <div className={styles.dagEmpty}>
          <p>{t("overview.noPlanDag")}</p>
          <Button onClick={() => onNavigate("plan")} size="sm" variant="secondary">
            {t("overview.openPlanWorkspace")}
          </Button>
        </div>
      )}
    </Card>
  );
}

function latestRun(tasks: TaskLogEntry[]): TaskLogEntry | null {
  return (
    [...tasks].sort(
      (left, right) => Date.parse(right.started_at) - Date.parse(left.started_at),
    )[0] ?? null
  );
}

function safeDirectorySummary(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) return "";
  const parts = value.replace(/\\/g, "/").split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "";
}

function getRecommendation(
  inventory: ProjectInventory,
  tasks: TaskLogEntry[],
  t: ReturnType<typeof useI18n>["t"],
) {
  const latestTask = latestRun(tasks);
  const activeOrNeedsAttention =
    latestTask != null &&
    (latestTask.status === "running" ||
      latestTask.status === "pending" ||
      latestTask.status === "partial" ||
      latestTask.status === "failed");
  if (activeOrNeedsAttention) {
    return {
      action: t("overview.recommendation.runsAction"),
      description: t("overview.recommendation.runsDescription"),
      title: t("overview.recommendation.runsTitle"),
      workspace: "runs" as const,
    };
  }
  if (latestTask?.status === "completed") {
    return {
      action: t("overview.recommendation.resultsAction"),
      description: t("overview.recommendation.resultsDescription"),
      title: t("overview.recommendation.resultsTitle"),
      workspace: "results" as const,
    };
  }
  if (inventory.dataState === "raw_dicom" || inventory.dataState === "mixed") {
    return {
      action: t("overview.recommendation.dataAction"),
      description: t("overview.recommendation.dataDescription"),
      title: t("overview.recommendation.dataTitle"),
      workspace: "data" as const,
    };
  }
  if (inventory.dataState === "converted_bids") {
    return {
      action: t("overview.recommendation.planAction"),
      description: t("overview.recommendation.planDescription"),
      title: t("overview.recommendation.planTitle"),
      workspace: "plan" as const,
    };
  }
  return {
    action: t("overview.recommendation.emptyAction"),
    description: t("overview.recommendation.emptyDescription"),
    title: t("overview.recommendation.emptyTitle"),
    workspace: "data" as const,
  };
}

function localizeOverviewValue(
  value: string | null | undefined,
  t: ReturnType<typeof useI18n>["t"],
): string {
  const normalized = value?.trim().toLowerCase();
  if (!normalized) return "";
  if (normalized === "unavailable") {
    return t("common.unavailable");
  }
  if (normalized === "no model selected") {
    return t("overview.noModelSelected");
  }
  if (normalized === "referenced rawdata") {
    return t("overview.referencedRawdata");
  }
  return value!.trim();
}

function dataTone(inventory: ProjectInventory): "neutral" | "success" | "warning" {
  if (inventory.dataState === "converted_bids") return "success";
  if (inventory.dataState === "raw_dicom" || inventory.dataState === "mixed") return "warning";
  return "neutral";
}

function taskTone(
  status: TaskLogEntry["status"],
): "neutral" | "info" | "success" | "warning" | "danger" {
  if (status === "completed") return "success";
  if (status === "partial") return "warning";
  if (status === "failed") return "danger";
  if (status === "running") return "info";
  return "neutral";
}

function statusLabel(status: TaskLogEntry["status"], t: ReturnType<typeof useI18n>["t"]): string {
  return t(`runs.status.${status}`);
}
