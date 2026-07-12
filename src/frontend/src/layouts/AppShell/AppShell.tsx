import type { ReactNode } from "react";

import { useI18n } from "../../i18n/useI18n";
import styles from "./AppShell.module.css";

export type AppShellProps = {
  children: ReactNode;
  inspector?: ReactNode;
  inspectorOpen?: boolean;
  lifecycle?: ReactNode;
  mainClassName?: string;
  runActivity?: ReactNode;
  systemMessages?: ReactNode;
  topBar: ReactNode;
};

export function AppShell({
  children,
  inspector,
  inspectorOpen = false,
  lifecycle,
  mainClassName,
  runActivity,
  systemMessages,
  topBar,
}: AppShellProps) {
  const { t } = useI18n();
  return (
    <div className={styles.shell} data-inspector={inspectorOpen ? "open" : "closed"}>
      <div className={styles.topBarSlot}>{topBar}</div>
      {lifecycle ? <div className={styles.lifecycleSlot}>{lifecycle}</div> : null}
      {systemMessages ? (
        <div className={styles.systemMessages} aria-label={t("system.messages")}>
          {systemMessages}
        </div>
      ) : null}
      <div className={styles.body}>
        <main className={`${styles.mainSlot} ${mainClassName ?? ""}`}>{children}</main>
        {inspector ? <div className={styles.inspectorSlot}>{inspector}</div> : null}
      </div>
      {runActivity ? <div className={styles.runActivitySlot}>{runActivity}</div> : null}
    </div>
  );
}
