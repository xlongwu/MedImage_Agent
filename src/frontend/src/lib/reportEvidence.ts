import type { EvidenceLevel } from "./evidence";

export type ReportEvidence = {
  detail: string;
  level: EvidenceLevel;
};

type RecordLike = Record<string, unknown>;

function isRecord(value: unknown): value is RecordLike {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasText(value: unknown): boolean {
  return typeof value === "string" && value.trim().length > 0;
}

function hasObjectContent(value: unknown): boolean {
  return isRecord(value) && Object.keys(value).length > 0;
}

function numberValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim().length) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function nestedRecords(...values: Array<RecordLike | null | undefined>): RecordLike[] {
  const records: RecordLike[] = [];
  for (const value of values) {
    if (!value) continue;
    records.push(value);
    for (const nestedValue of Object.values(value)) {
      if (isRecord(nestedValue)) records.push(nestedValue);
    }
  }
  return records;
}

export function deriveReportViewerEvidence(report: RecordLike | null | undefined): ReportEvidence {
  if (!report) {
    return {
      detail: "No report response has been loaded from the backend.",
      level: "backend_required",
    };
  }

  if (
    hasText(report.report_markdown) ||
    hasText(report.report_html) ||
    hasText(report.subject_qc_table) ||
    hasText(report.exclusion_recommendations)
  ) {
    return {
      detail: "Report content is present.",
      level: "created",
    };
  }

  if (hasObjectContent(report.dataset_summary)) {
    return {
      detail: "Only dataset summary metadata is present.",
      level: "metadata_only",
    };
  }

  return {
    detail: "Report response loaded without report artifacts.",
    level: "backend_required",
  };
}

export function deriveReportExportEvidence(
  ...records: Array<RecordLike | null | undefined>
): ReportEvidence {
  const allRecords = nestedRecords(...records);
  if (!allRecords.length) {
    return {
      detail: "No export response has been loaded from the backend.",
      level: "backend_required",
    };
  }

  const hasCreatedExport = allRecords.some((record) => {
    const manifest = isRecord(record.manifest) ? record.manifest : null;
    const exportSummary = isRecord(record.export_summary) ? record.export_summary : record;
    const exportedFileCount = numberValue(exportSummary.exported_files_total);
    const manifestFiles = Array.isArray(manifest?.files) ? manifest.files.length : 0;
    return (
      hasText(record.export_id) ||
      hasText(record.zip_path) ||
      hasText(record.package_dir) ||
      manifestFiles > 0 ||
      (exportedFileCount !== null && exportedFileCount > 0)
    );
  });

  if (hasCreatedExport) {
    return {
      detail: "Export package evidence is present.",
      level: "created",
    };
  }

  return {
    detail: "The backend request returned metadata, but no export package evidence is present.",
    level: "metadata_only",
  };
}

export function deriveReportValidationEvidence(
  record: RecordLike | null | undefined,
): ReportEvidence {
  if (!record) {
    return {
      detail: "No validation response has been loaded from the backend.",
      level: "backend_required",
    };
  }

  const validationResult = isRecord(record.validation_result) ? record.validation_result : record;
  const stats = isRecord(validationResult.stats) ? validationResult.stats : {};
  const status = String(validationResult.validation_status ?? validationResult.status ?? "")
    .trim()
    .toLowerCase();
  const mismatchCount = numberValue(stats.checksum_mismatch_total);
  const missingCount = numberValue(stats.missing_files_total);
  const safetyCount = numberValue(stats.safety_violations_total);
  const zipTestOk = stats.zip_test_ok;
  const counts = [mismatchCount, missingCount, safetyCount];
  const hasFailureEvidence =
    counts.some((count) => count !== null && count > 0) ||
    zipTestOk === false ||
    ["failed", "fail", "error", "invalid", "validation_failed"].includes(status);

  if (hasFailureEvidence) {
    return {
      detail: "Validation evidence reports missing, mismatched, unsafe, or failed checks.",
      level: "validation_failed",
    };
  }

  const passed = ["passed", "pass", "success", "ok", "valid", "validated"].includes(status);
  const zeroCounts =
    counts.every((count) => count === 0) &&
    zipTestOk !== false;

  if (passed && zeroCounts) {
    return {
      detail: "Validation passed with zero mismatch, missing-file, and safety counts.",
      level: "validated",
    };
  }

  if (status || Object.keys(stats).length > 0) {
    return {
      detail: "Validation metadata is present, but it is not sufficient to mark validated.",
      level: "metadata_only",
    };
  }

  return {
    detail: "Validation response loaded without validation result evidence.",
    level: "backend_required",
  };
}
