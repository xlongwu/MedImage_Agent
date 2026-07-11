import { useCallback, type KeyboardEvent } from "react";
import {
  deriveWorkflowLifecycleState,
  isWorkflowTabBlocked,
  workflowTabItems,
  type ProjectDataState,
  type WorkflowLifecycleState,
  type WorkflowTab,
} from "../../lib/projectWorkflow";
import styles from "./ProjectLifecycleSidebar.module.css";

export type ProjectLifecycleSidebarProps = {
  activeTab: WorkflowTab;
  dataState?: ProjectDataState;
  hasPreprocessingRun?: boolean;
  projectsPageOpen?: boolean;
  onChange: (tab: WorkflowTab) => void;
  onOpenWorkspace?: () => void;
};

const lifecycleStateLabels: Record<WorkflowLifecycleState, string> = {
  current: "Current",
  completed: "Completed",
  available: "Available",
  blocked: "Blocked",
};

const lifecycleStateClasses: Record<WorkflowLifecycleState, string> = {
  current: styles.current,
  completed: styles.completed,
  available: styles.available,
  blocked: styles.blocked,
};

export function ProjectLifecycleSidebar({
  activeTab,
  dataState,
  hasPreprocessingRun = false,
  projectsPageOpen = false,
  onChange,
  onOpenWorkspace,
}: ProjectLifecycleSidebarProps) {
  const handleChange = useCallback(
    (tab: WorkflowTab) => {
      onOpenWorkspace?.();
      onChange(tab);
    },
    [onChange, onOpenWorkspace],
  );
  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>, tab: WorkflowTab) => {
      const currentIndex = workflowTabItems.findIndex((item) => item.id === tab);
      let nextIndex: number | null = null;
      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        nextIndex = nextReachableIndex(currentIndex, 1, dataState, hasPreprocessingRun);
      } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        nextIndex = nextReachableIndex(currentIndex, -1, dataState, hasPreprocessingRun);
      } else if (event.key === "Home") {
        nextIndex = firstReachableIndex(dataState, hasPreprocessingRun);
      } else if (event.key === "End") {
        nextIndex = lastReachableIndex(dataState, hasPreprocessingRun);
      }

      if (nextIndex === null) {
        return;
      }

      event.preventDefault();
      const nextTab = workflowTabItems[nextIndex];
      handleChange(nextTab.id);
      window.requestAnimationFrame(() => {
        document.getElementById(`project-lifecycle-${nextTab.id}`)?.focus();
      });
    },
    [dataState, handleChange, hasPreprocessingRun],
  );

  return (
    <nav className={styles.nav} aria-label="Project lifecycle">
      <div className={styles.header}>
        <span>Lifecycle</span>
      </div>
      <ol className={styles.list}>
        {workflowTabItems.map((tab, index) => {
          const lifecycle = deriveWorkflowLifecycleState(tab.id, dataState, hasPreprocessingRun);
          const isActive = !projectsPageOpen && activeTab === tab.id;
          const isBlocked = lifecycle === "blocked";
          const stateLabel = lifecycleLabel(tab.id, lifecycle, dataState, hasPreprocessingRun);
          const description = lifecycleDescription(
            tab.id,
            tab.description,
            dataState,
            hasPreprocessingRun,
          );
          const disabledReason = lifecycleDisabledReason(tab.id, dataState, hasPreprocessingRun);
          const buttonClassName = [
            styles.button,
            lifecycleStateClasses[lifecycle],
            isActive ? styles.isActive : "",
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <li key={tab.id} className={styles.item}>
              <button
                id={`project-lifecycle-${tab.id}`}
                type="button"
                className={buttonClassName}
                aria-current={isActive ? "page" : undefined}
                aria-controls="workflow-workspace"
                aria-disabled={isBlocked}
                aria-label={`${tab.label}, ${stateLabel}`}
                disabled={isBlocked}
                title={disabledReason || description}
                onClick={() => {
                  if (isBlocked) {
                    return;
                  }
                  handleChange(tab.id);
                }}
                onKeyDown={(event) => handleKeyDown(event, tab.id)}
              >
                <span className={styles.glyph} aria-hidden="true">
                  <LifecycleGlyph state={lifecycle} index={index + 1} />
                </span>
                <span className={styles.text}>
                  <span className={styles.label}>{tab.label}</span>
                  <span className={styles.description}>{description}</span>
                </span>
                <span className={styles.stateText}>{stateLabel}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function lifecycleLabel(
  tabId: WorkflowTab,
  lifecycle: WorkflowLifecycleState,
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): string {
  if (tabId === "preprocessing" && lifecycle === "blocked" && dataState === "raw_dicom") {
    return "Convert";
  }
  if (tabId === "reports" && lifecycle === "blocked" && dataState === "raw_dicom") {
    return "Run first";
  }
  if (tabId === "results" && lifecycle === "blocked" && !hasPreprocessingRun) {
    return "Run first";
  }
  return lifecycleStateLabels[lifecycle];
}

function lifecycleDescription(
  tabId: WorkflowTab,
  fallback: string,
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): string {
  if (tabId === "preprocessing" && dataState === "raw_dicom") {
    return "Needs BIDS/NIfTI";
  }
  if ((tabId === "reports" || tabId === "results") && !hasPreprocessingRun) {
    return "Needs run evidence";
  }
  return fallback;
}

function lifecycleDisabledReason(
  tabId: WorkflowTab,
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): string {
  if (tabId === "preprocessing" && dataState === "raw_dicom") {
    return "Convert raw DICOM to registered BIDS/NIfTI before preprocessing.";
  }
  if (tabId === "reports" && !hasPreprocessingRun) {
    return "Create or run preprocessing before QC reports are available.";
  }
  if (tabId === "results" && !hasPreprocessingRun) {
    return "Create or run preprocessing before result artifacts are available.";
  }
  return "";
}

function firstReachableIndex(
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): number | null {
  const index = workflowTabItems.findIndex(
    (tab) => !isWorkflowTabBlocked(tab.id, dataState, hasPreprocessingRun),
  );
  return index >= 0 ? index : null;
}

function lastReachableIndex(
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): number | null {
  for (let index = workflowTabItems.length - 1; index >= 0; index -= 1) {
    if (!isWorkflowTabBlocked(workflowTabItems[index].id, dataState, hasPreprocessingRun)) {
      return index;
    }
  }
  return null;
}

function nextReachableIndex(
  currentIndex: number,
  direction: 1 | -1,
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): number | null {
  const count = workflowTabItems.length;
  for (let offset = 1; offset <= count; offset += 1) {
    const nextIndex = (currentIndex + direction * offset + count) % count;
    if (!isWorkflowTabBlocked(workflowTabItems[nextIndex].id, dataState, hasPreprocessingRun)) {
      return nextIndex;
    }
  }
  return null;
}

function LifecycleGlyph({ state, index }: { state: WorkflowLifecycleState; index: number }) {
  if (state === "completed") {
    return (
      <svg viewBox="0 0 16 16" width="13" height="13">
        <path
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M3 8.5l3.5 3.5L13 4.5"
        />
      </svg>
    );
  }
  if (state === "blocked") {
    return (
      <svg viewBox="0 0 16 16" width="13" height="13">
        <path
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.6"
          d="M5.5 7V5.5a2.5 2.5 0 015 0V7m-6 0h7v5.5h-7z"
        />
      </svg>
    );
  }
  return <>{index}</>;
}
