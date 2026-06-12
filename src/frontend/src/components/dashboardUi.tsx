import { useMemo, useState, type CSSProperties, type ReactNode } from "react";

export type DashboardStatus = "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown";

type ActionCleanupOptions = {
  rawDicom?: boolean;
  maxVisible?: number;
};

const rawDicomPriority = [
  "conversion dry-run",
  "conversion preflight",
  "persist review package",
  "register converted",
  "create preprocessing run",
];

export function normalizeActionText(action: string): string {
  return action
    .trim()
    .toLowerCase()
    .replace(/[^\w\s-]+/g, "")
    .replace(/\s+/g, " ");
}

export function cleanupNextActions(actions: string[], options: ActionCleanupOptions = {}): string[] {
  const seen = new Set<string>();
  const filtered = actions.filter((action) => {
    const normalized = normalizeActionText(action);
    if (!normalized || seen.has(normalized)) {
      return false;
    }
    if (
      options.rawDicom &&
      normalized.includes("import bids dataset") &&
      !normalized.includes("conversion")
    ) {
      return false;
    }
    seen.add(normalized);
    return true;
  });

  if (!options.rawDicom) {
    return filtered;
  }

  return filtered.sort((a, b) => {
    const na = normalizeActionText(a);
    const nb = normalizeActionText(b);
    const ia = rawDicomPriority.findIndex((term) => na.includes(term));
    const ib = rawDicomPriority.findIndex((term) => nb.includes(term));
    const pa = ia === -1 ? rawDicomPriority.length : ia;
    const pb = ib === -1 ? rawDicomPriority.length : ib;
    return pa - pb;
  });
}

const statusClass: Record<DashboardStatus, string> = {
  ready: "is-ready",
  warning: "is-warning",
  blocked: "is-blocked",
  not_applicable: "is-muted",
  not_started: "is-muted",
  unknown: "is-muted",
};

export function statusFromBackend(status?: string | null): DashboardStatus {
  if (status === "ready" || status === "pass") return "ready";
  if (status === "warning") return "warning";
  if (status === "blocked" || status === "fail" || status === "failed") return "blocked";
  if (status === "not_applicable") return "not_applicable";
  if (status === "not_started" || status === "not_run") return "not_started";
  return "unknown";
}

export function StatusPill({
  status,
  children,
}: {
  status: DashboardStatus | string;
  children?: ReactNode;
}) {
  const resolved = statusFromBackend(status);
  return <span className={`apple-status-pill ${statusClass[resolved]}`}>{children ?? statusLabel(resolved)}</span>;
}

export function statusLabel(status: DashboardStatus): string {
  if (status === "not_applicable") return "Not applicable";
  if (status === "not_started") return "Not started";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function MetricTile({
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
}

export function SafetyBanner({
  tone = "info",
  children,
}: {
  tone?: "info" | "warning" | "danger";
  children: ReactNode;
}) {
  return <div className={`apple-safety-banner tone-${tone}`}>{children}</div>;
}

export function CollapsibleDetails({
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
}

export function ActionList({
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
        <button type="button" className="apple-link-button" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "View fewer" : `View ${cleaned.length - maxVisible} more`}
        </button>
      ) : null}
    </div>
  );
}

export const appleCardStyle: CSSProperties = {
  padding: 18,
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 8,
  background: "rgba(255, 255, 255, 0.92)",
};
