import type {
  ImagePlane,
  ImagePreview,
  ImageSourceFile,
  ImageSources,
  ImageValidationReport,
} from "../../lib/types/image";
import type { ProjectDetail } from "../../lib/types/project";
import { BrainScan } from "./BrainScan";
import { MiniScan } from "./MiniScan";

export interface MedicalImageViewerProps {
  project: ProjectDetail;
  sequence: string;
  plane: ImagePlane;
  sequenceOptions: string[];
  imageSources: ImageSources;
  validation: ImageValidationReport;
  subjectId: string | null;
  preview: ImagePreview;
  sourceFile: ImageSourceFile | null;
  loading: boolean;
  onSequenceChange: (sequence: string) => void;
  onPlaneChange: (plane: ImagePlane) => void;
  onSubjectChange: (subjectId: string) => void;
  onSliceChange: (sliceIndex: number) => void;
}

export function MedicalImageViewer({
  project,
  sequence,
  plane,
  sequenceOptions,
  imageSources,
  validation,
  subjectId,
  preview,
  sourceFile,
  loading,
  onSequenceChange,
  onPlaneChange,
  onSubjectChange,
  onSliceChange,
}: MedicalImageViewerProps) {
  const currentSlice = preview.slice_index ?? 0;
  const sliceCount = preview.slice_count ?? 0;
  const activePlane = plane;
  const planeOptions: Array<{ axis: string; value: ImagePlane; label: string }> = [
    { axis: "S", value: "sagittal", label: "Sagittal" },
    { axis: "A", value: "axial", label: "Axial" },
    { axis: "C", value: "coronal", label: "Coronal" },
  ];
  const planeLabel = planeOptions.find((item) => item.value === activePlane)?.label ?? "Axial";
  const dimensions = sourceFile?.dimensions?.length
    ? sourceFile.dimensions
    : (preview.dimensions ?? []);
  const spacing = sourceFile?.voxel_spacing ?? [];
  const sourceSummary = sourceFile?.relative_path ?? preview.source_path ?? preview.message;
  const visibleValidationIssues = validation.issues.slice(0, 3);
  return (
    <section className="viewer-card">
      <div className="viewer-tools">
        <select
          className="scan-select subject-select"
          value={subjectId || ""}
          onChange={(event) => onSubjectChange(event.target.value)}
          disabled={!imageSources.subjects.length}
          aria-label="Subject"
        >
          {imageSources.subjects.length ? (
            imageSources.subjects.map((item) => (
              <option key={item.subject_id} value={item.subject_id}>
                {item.subject_id}
              </option>
            ))
          ) : (
            <option value="">No sources</option>
          )}
        </select>
        <select
          className="scan-select"
          value={sequence}
          onChange={(event) => onSequenceChange(event.target.value)}
          aria-label="Sequence"
        >
          {(sequenceOptions.length ? sequenceOptions : project.sequences).map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <button aria-label="Window level">WL</button>
        <button aria-label="Fullscreen">[]</button>
        <button aria-label="More">...</button>
      </div>
      <div className="scan-thumbs">
        {planeOptions.map((item) => (
          <button
            key={item.value}
            type="button"
            className={`scan-thumb ${activePlane === item.value ? "active" : ""}`}
            onClick={() => onPlaneChange(item.value)}
            aria-label={`${item.label} plane`}
            title={`${item.label} plane`}
          >
            <MiniScan axis={item.axis} />
          </button>
        ))}
      </div>
      <div className="scan-canvas">
        {preview.preview_url ? (
          <img
            className="brain-preview-img"
            src={preview.preview_url}
            alt={`${project.name} ${subjectId ?? "selected subject"} ${sequence} ${planeLabel} medical image preview`}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <BrainScan />
        )}
        <div className="slice-rule">
          <span>S</span>
          <i />
          <span>I</span>
        </div>
        <div className="scan-count">
          {loading ? "loading" : sliceCount ? `${currentSlice + 1} / ${sliceCount}` : "126 / 256"}
        </div>
      </div>
      <div className="preview-status">
        <strong>
          {preview.source === "nifti" ? `${planeLabel} NIfTI preview` : "Fallback preview"}
        </strong>
        <span>
          {preview.source === "nifti"
            ? `slice ${(preview.slice_index ?? 0) + 1} / ${preview.slice_count ?? "?"}`
            : preview.message}
        </span>
        <div className="preview-meta">
          <span>
            Dims <b>{dimensions.length ? dimensions.join(" x ") : "unknown"}</b>
          </span>
          <span>
            Spacing <b>{spacing.length ? spacing.slice(0, 3).join(" x ") : "pending"}</b>
          </span>
          <span>
            Source <b>{sourceSummary}</b>
          </span>
        </div>
        <div className={`validation-checklist ${validation.status}`}>
          <span>
            Validation <b>{validation.status}</b>
          </span>
          {visibleValidationIssues.length ? (
            visibleValidationIssues.map((issue) => (
              <span
                key={`${issue.code}-${issue.subject_id ?? "project"}-${issue.sequence ?? "all"}`}
              >
                {issue.severity}: <b>{issue.message}</b>
              </span>
            ))
          ) : (
            <span>
              <b>No checklist issues</b>
            </span>
          )}
        </div>
        {sliceCount > 1 ? (
          <input
            className="slice-slider"
            type="range"
            min={0}
            max={sliceCount - 1}
            value={currentSlice}
            onChange={(event) => onSliceChange(Number(event.target.value))}
            aria-label="Slice index"
          />
        ) : null}
      </div>
      <div className="viewer-dock">
        {["Pan", "Cross", "Zoom", "WL", "Grid", "Measure", "Expand"].map((item, index) => (
          <button key={item} className={index === 0 ? "selected" : ""}>
            {item.slice(0, 2)}
          </button>
        ))}
      </div>
    </section>
  );
}
