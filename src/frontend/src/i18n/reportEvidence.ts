import type { I18nContextValue } from "./context";

export function localizeReportEvidenceDetail(detail: string, t: I18nContextValue["t"]): string {
  const messages: Record<string, string> = {
    "No report response has been loaded from the backend.": t("results.report.evidence.unloaded"),
    "Report content is present.": t("results.report.evidence.created"),
    "Only dataset summary metadata is present.": t("results.report.evidence.metadata"),
    "Report response loaded without report artifacts.": t("results.report.evidence.missing"),
    "No export response has been loaded from the backend.": t("report.evidence.exportUnloaded"),
    "Export package evidence is present.": t("report.evidence.exportCreated"),
    "The backend request returned metadata, but no export package evidence is present.": t(
      "report.evidence.exportMetadata",
    ),
    "No validation response has been loaded from the backend.": t(
      "report.evidence.validationUnloaded",
    ),
    "Validation evidence reports missing, mismatched, unsafe, or failed checks.": t(
      "report.evidence.validationFailed",
    ),
    "Validation completed with warnings but zero mismatch, missing-file, and safety counts.": t(
      "report.evidence.validationWarning",
    ),
    "Validation passed with zero mismatch, missing-file, and safety counts.": t(
      "report.evidence.validationPassed",
    ),
    "Validation metadata is present, but it is not sufficient to mark validated.": t(
      "report.evidence.validationMetadata",
    ),
    "Validation response loaded without validation result evidence.": t(
      "report.evidence.validationMissing",
    ),
  };

  return messages[detail] ?? detail;
}
