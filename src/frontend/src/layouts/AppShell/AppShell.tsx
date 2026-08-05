import type { ReactNode } from "react";

import { useI18n } from "../../i18n/useI18n";
import type { WorkspaceChromePreset } from "../../lib/workspaceChromeModel";
import styles from "./AppShell.module.css";

export type AppShellProps = {
  children: ReactNode;
  contextSidebar?: ReactNode;
  inspector?: ReactNode;
  inspectorOpen?: boolean;
  lifecycle?: ReactNode;
  mainClassName?: string;
  preset?: WorkspaceChromePreset;
  rail?: ReactNode;
  runActivity?: ReactNode;
  systemMessages?: ReactNode;
  topBar: ReactNode;
};

export function AppShell({
  children,
  contextSidebar,
  inspector,
  inspectorOpen = false,
  lifecycle,
  mainClassName,
  preset = "standard-workspace",
  rail,
  runActivity,
  systemMessages,
  topBar,
}: AppShellProps) {
  const { t } = useI18n();
  return (
    <div className={styles.shell} data-preset={preset}>
      <div className={styles.topBarSlot}>{topBar}</div>
      <div className={styles.workspace}>
        {rail ? <div className={styles.railSlot}>{rail}</div> : null}
        <div className={styles.contentStack}>
          {lifecycle ? <div className={styles.lifecycleSlot}>{lifecycle}</div> : null}
          {systemMessages ? (
            <div className={styles.systemMessages} aria-label={t("system.messages")}>
              {systemMessages}
            </div>
          ) : null}
          <div
            className={styles.body}
            data-context={contextSidebar ? "open" : "closed"}
            data-inspector={inspectorOpen && inspector ? "open" : "closed"}
          >
            {contextSidebar ? (
              <div className={styles.contextSidebarSlot}>{contextSidebar}</div>
            ) : null}
            <main className={`${styles.mainSlot} ${mainClassName ?? ""}`}>{children}</main>
            {inspector ? <div className={styles.inspectorSlot}>{inspector}</div> : null}
          </div>
          {runActivity ? <div className={styles.runActivitySlot}>{runActivity}</div> : null}
        </div>
      </div>
    </div>
  );
}
