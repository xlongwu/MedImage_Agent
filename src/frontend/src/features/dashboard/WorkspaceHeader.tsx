import { memo } from "react";

import { StatusPill as DashboardStatusPill } from "../../components/dashboardUi";
import styles from "./WorkspaceHeader.module.css";

export const WorkspaceHeader = memo(function WorkspaceHeader({
  title,
  subtitle,
  status,
  compact = false,
}: {
  title: string;
  subtitle: string;
  status?: string;
  compact?: boolean;
}) {
  return (
    <div className={`${styles.header} ${compact ? styles.compact : ""}`}>
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {status ? <DashboardStatusPill status={status}>{status}</DashboardStatusPill> : null}
    </div>
  );
});
