import { memo, useMemo, useState, type ReactNode } from "react";
import {
  cleanupNextActions,
  normalizeActionText,
  statusFromBackend,
  statusLabel,
  type DashboardStatus,
} from "./dashboardUiModel";

export type { DashboardStatus } from "./dashboardUiModel";

const statusClass: Record<DashboardStatus, string> = {
  ready: "is-ready",
  warning: "is-warning",
  blocked: "is-blocked",
  not_applicable: "is-muted",
  not_started: "is-muted",
  unknown: "is-muted",
};

export const StatusPill = memo(function StatusPill({
  status,
  children,
}: {
  status: DashboardStatus | string;
  children?: ReactNode;
}) {
  const resolved = statusFromBackend(status);
  return (
    <span className={`apple-status-pill ${statusClass[resolved]}`}>
      {children ?? statusLabel(resolved)}
    </span>
  );
});

export const MetricTile = memo(function MetricTile({
  label,
  value,
  tone = "neutral",
  mono = false,
}: {
  label: string;
  value: ReactNode;
  tone?: "neutral" | "blue" | "green" | "amber" | "red";
  mono?: boolean;
}) {
  return (
    <div className={`apple-metric-tile tone-${tone}`}>
      <span>{label}</span>
      <strong className={mono ? "mono-value" : undefined}>{value}</strong>
    </div>
  );
});

export const SafetyBanner = memo(function SafetyBanner({
  tone = "info",
  children,
}: {
  tone?: "info" | "warning" | "danger";
  children: ReactNode;
}) {
  return <div className={`apple-safety-banner tone-${tone}`}>{children}</div>;
});

export const CollapsibleDetails = memo(function CollapsibleDetails({
  title,
  summary,
  children,
  defaultOpen = false,
}: {
  title: string;
  summary?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details className="apple-collapsible" open={defaultOpen}>
      <summary>
        <span>{title}</span>
        {summary ? <small>{summary}</small> : null}
      </summary>
      <div className="apple-collapsible-body">{children}</div>
    </details>
  );
});

export const ActionList = memo(function ActionList({
  actions,
  rawDicom = false,
  maxVisible = 3,
}: {
  actions: string[];
  rawDicom?: boolean;
  maxVisible?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const cleaned = useMemo(
    () => cleanupNextActions(actions, { rawDicom, maxVisible }),
    [actions, rawDicom, maxVisible],
  );
  const visible = expanded ? cleaned : cleaned.slice(0, maxVisible);

  if (!cleaned.length) {
    return null;
  }

  return (
    <div className="apple-action-list">
      {visible.map((action, index) => (
        <div key={`${normalizeActionText(action)}-${index}`} className="apple-action-item">
          <span>{index + 1}</span>
          <p>{action}</p>
        </div>
      ))}
      {cleaned.length > maxVisible ? (
        <button
          type="button"
          className="apple-link-button"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "View fewer" : `View ${cleaned.length - maxVisible} more`}
        </button>
      ) : null}
    </div>
  );
});
