import { MetricCard } from "./MetricCard";
import type { DatasetSummary } from "../../lib/types/dataset";

export interface DatasetSummaryCardProps {
  summary: DatasetSummary;
  loading: boolean;
  error: string;
}

export function DatasetSummaryCard({ summary, loading, error }: DatasetSummaryCardProps) {
  const isRawDicom = summary.dicom_files !== undefined && summary.dicom_files > 0 && summary.subjects === 0;
  return (
    <MetricCard
      title={`Dataset Summary ${loading ? "..." : error ? "(fallback)" : ""}`}
      values={
        isRawDicom
          ? [
              [String(summary.dicom_subjects || 0), "Candidate Subjects"],
              [String(summary.dicom_series || 0), "DICOM Series"],
              [summary.total_size || "0 KB", "Total Size (DICOM)"],
            ]
          : [
              [String(summary.subjects), "Subjects"],
              [summary.scans.toLocaleString(), "Scans"],
              [summary.total_size, "Total Size"],
            ]
      }
      tone="blue"
      note={isRawDicom ? "Raw DICOM (Expected before conversion)" : summary.health_status}
    />
  );
}
