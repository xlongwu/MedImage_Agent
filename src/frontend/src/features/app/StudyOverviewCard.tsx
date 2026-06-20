import type { StudyOverview } from "../../lib/types/project";

export interface StudyOverviewCardProps {
  overview: StudyOverview;
  loading: boolean;
  error: string;
}

export function StudyOverviewCard({ overview, loading, error }: StudyOverviewCardProps) {
  const hasDicom = overview.dicom_files !== undefined && overview.dicom_files > 0;
  return (
    <section className="overview-card">
      <div className="card-title">Study Overview {loading ? "..." : error ? "(fallback)" : ""}</div>
      <dl>
        <dt>Study Name</dt><dd>{overview.study_name}</dd>
        <dt>Study ID</dt><dd>{overview.study_id}</dd>
        <dt>Modality</dt><dd>{overview.modality}</dd>
        <dt>Sequences</dt><dd>{overview.sequences.join(", ")}</dd>
        <dt>Subjects</dt><dd>{overview.subjects || (hasDicom ? `${overview.dicom_subjects} (candidate)` : "0")}</dd>
        {hasDicom && (
          <>
            <dt>DICOM Series</dt><dd>{overview.dicom_series} series</dd>
            <dt>DICOM Files</dt><dd>{overview.dicom_files?.toLocaleString()} files</dd>
          </>
        )}
        <dt>Date</dt><dd>{overview.date}</dd>
      </dl>
      <button className="soft-button">View Details</button>
    </section>
  );
}
