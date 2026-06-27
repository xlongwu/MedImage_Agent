import type { ReactNode } from "react";

import styles from "./AppShell.module.css";

export type AppShellProps = {
  children: ReactNode;
  inspector?: ReactNode;
  inspectorOpen?: boolean;
  mainClassName?: string;
  runActivity?: ReactNode;
  sidebar: ReactNode;
  systemMessages?: ReactNode;
  topBar: ReactNode;
};

export function AppShell({
  children,
  inspector,
  inspectorOpen = false,
  mainClassName,
  runActivity,
  sidebar,
  systemMessages,
  topBar,
}: AppShellProps) {
  return (
    <div className={styles.shell} data-inspector={inspectorOpen ? "open" : "closed"}>
      <div className={styles.topBarSlot}>{topBar}</div>
      {systemMessages ? (
        <div className={styles.systemMessages} aria-label="System messages">
          {systemMessages}
        </div>
      ) : null}
      <div className={styles.body}>
        <div className={styles.sidebarSlot}>{sidebar}</div>
        <main className={`${styles.mainSlot} ${mainClassName ?? ""}`}>{children}</main>
        {inspector ? <div className={styles.inspectorSlot}>{inspector}</div> : null}
      </div>
      {runActivity ? <div className={styles.runActivitySlot}>{runActivity}</div> : null}
    </div>
  );
}
