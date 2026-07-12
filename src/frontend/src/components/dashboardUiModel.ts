export type DashboardStatus =
  | "ready"
  | "warning"
  | "blocked"
  | "not_applicable"
  | "not_started"
  | "unknown";

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

export function cleanupNextActions(
  actions: string[],
  options: ActionCleanupOptions = {},
): string[] {
  const seen = new Set<string>();
  const filtered = actions.filter((action) => {
    const normalized = normalizeActionText(action);
    if (!normalized || seen.has(normalized)) return false;
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

  if (!options.rawDicom) return filtered;

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

export function statusFromBackend(status?: string | null): DashboardStatus {
  if (status === "ready" || status === "pass") return "ready";
  if (status === "warning") return "warning";
  if (status === "blocked" || status === "fail" || status === "failed") return "blocked";
  if (status === "not_applicable") return "not_applicable";
  if (status === "not_started" || status === "not_run") return "not_started";
  return "unknown";
}

export function statusLabel(status: DashboardStatus): string {
  if (status === "not_applicable") return "Not applicable";
  if (status === "not_started") return "Not started";
  return status.charAt(0).toUpperCase() + status.slice(1);
}
