/**
 * Run Health Status Helper
 *
 * Pure helper that derives a compact run health level from a run link
 * record and an optional summary preview.  Used by the run detail panel
 * to display an at-a-glance health indicator.
 */

import type { RunLinkRecord, RunSummaryPreview } from "../types";

export type RunHealthLevel = "ok" | "warning" | "failed" | "unknown";

export type RunHealthSummary = {
  level: RunHealthLevel;
  label: string;
  explanation: string;
};

/**
 * Derive a compact health summary from a run link and optional summary preview.
 *
 * Rules (first match wins):
 *   - `failed`   — run status contains "FAILED", or summary reports failed nodes.
 *   - `warning`  — run or summary has warnings, or missing summary.
 *   - `ok`       — status suggests success / submitted / completed and no warnings.
 *   - `unknown`  — anything else (no summary, no clear status, etc.).
 */
export function deriveRunHealth(
  run: RunLinkRecord | null,
  summaryPreview?: RunSummaryPreview | null,
): RunHealthSummary {
  if (!run) {
    return {
      level: "unknown",
      label: "Unknown",
      explanation: "No run link record is loaded.",
    };
  }

  const status = (run.status ?? "").toUpperCase();
  const isFailedStatus = status.includes("FAILED") || status.includes("BLOCKED");
  const hasFailedNodes =
    summaryPreview?.nodes_failed != null && summaryPreview.nodes_failed > 0;

  if (isFailedStatus || hasFailedNodes) {
    const reasons: string[] = [];
    if (isFailedStatus) reasons.push("run status is failed/blocked");
    if (hasFailedNodes) reasons.push(`${summaryPreview!.nodes_failed} node(s) failed`);
    return {
      level: "failed",
      label: "Failed",
      explanation: `Run has issues: ${reasons.join("; ")}.`,
    };
  }

  const runWarnings = (run.warnings ?? []).filter(
    (w): w is string => typeof w === "string" && w.length > 0,
  );
  const summaryWarnings = summaryPreview?.warnings ?? [];
  const hasWarnings = runWarnings.length > 0 || summaryWarnings.length > 0;
  const hasSummary = summaryPreview != null;

  if (!hasSummary && !isFailedStatus) {
    return {
      level: "warning",
      label: "No summary",
      explanation:
        "No summary preview is available — the run may still be in progress, or the summary file is missing.",
    };
  }

  if (hasWarnings && !isFailedStatus && !hasFailedNodes) {
    return {
      level: "warning",
      label: "Warning",
      explanation: "Run completed with warnings. Review the warnings list for details.",
    };
  }

  const isSuccess =
    status.includes("SUBMITTED") ||
    status.includes("SUCCESS") ||
    status.includes("COMPLETED") ||
    status.includes("RUNNING") ||
    status === "OK";

  if (isSuccess) {
    return {
      level: "ok",
      label: "Healthy",
      explanation:
        status.includes("RUNNING")
          ? "Run is submitted/running; summary may update later."
          : "Run completed successfully with no warnings.",
    };
  }

  return {
    level: "unknown",
    label: status || "Unknown",
    explanation: "Run status could not be classified — check the raw detail below.",
  };
}
