import type { ReactNode } from "react";

import styles from "./ProjectShell.module.css";

export type ProjectShellProps = {
  children: ReactNode;
  overview: ReactNode;
  viewer?: ReactNode;
  workspaceId?: string;
  workspaceLabel: string;
};

export function ProjectShell({
  children,
  overview,
  viewer,
  workspaceId = "workflow-workspace",
  workspaceLabel,
}: ProjectShellProps) {
  return (
    <div className={styles.shell}>
      {overview}
      {viewer ? <div className={styles.viewerSlot}>{viewer}</div> : null}
      <section
        id={workspaceId}
        className={styles.workspace}
        role="region"
        aria-label={workspaceLabel}
        aria-live="polite"
      >
        {children}
      </section>
    </div>
  );
}
