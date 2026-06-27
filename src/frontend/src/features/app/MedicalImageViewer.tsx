import type { KeyboardEvent } from "react";

import type {
  ImagePlane,
  ImagePreview,
  ImageSourceFile,
  ImageSources,
  ImageValidationReport,
} from "../../lib/types/image";
import type { ProjectDetail } from "../../lib/types/project";
import type { ProjectDataState } from "../../lib/projectWorkflow";
import { hasRealImagePreview } from "./viewerVisibility";
import styles from "./MedicalImageViewer.module.css";

export interface MedicalImageViewerProps {
  project: ProjectDetail;
  sequence: string;
  plane: ImagePlane;
  sequenceOptions: string[];
  imageSources: ImageSources;
  validation: ImageValidationReport;
  subjectId: string | null;
  preview: ImagePreview | null;
  sourceFile: ImageSourceFile | null;
  loading: boolean;
  dataState?: ProjectDataState;
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
  dataState,
  onSequenceChange,
  onPlaneChange,
  onSubjectChange,
  onSliceChange,
}: MedicalImageViewerProps) {
  const rawSliceCount = preview?.slice_count ?? 0;
  const sliceCount = rawSliceCount > 0 ? rawSliceCount : 0;
  const maxSliceIndex = Math.max(sliceCount - 1, 0);
  const currentSlice = Math.min(Math.max(preview?.slice_index ?? 0, 0), maxSliceIndex);
  const activePlane = plane;
  const planeOptions: Array<{ axis: string; value: ImagePlane; label: string }> = [
    { axis: "S", value: "sagittal", label: "Sagittal" },
    { axis: "A", value: "axial", label: "Axial" },
    { axis: "C", value: "coronal", label: "Coronal" },
  ];
  const planeLabel = planeOptions.find((item) => item.value === activePlane)?.label ?? "Axial";
  const dimensions = sourceFile?.dimensions?.length
    ? sourceFile.dimensions
    : (preview?.dimensions ?? []);
  const spacing = sourceFile?.voxel_spacing ?? [];
  const sourceSummary =
    sourceFile?.relative_path ?? preview?.source_path ?? preview?.message ?? "No preview source";
  const visibleValidationIssues = validation.issues.slice(0, 3);

  // Viewer display conditions per design spec:
  // - Raw DICOM / Empty / unknown: do NOT show pseudo NIfTI viewer; show Empty State
  // - Only show full viewer when there is a real preview URL
  const hasRealPreview = hasRealImagePreview(preview);
  const shouldShowViewer = hasRealPreview;
  const canNavigateSlices = sliceCount > 1 && !loading;
  const sliceStatus = sliceCount ? `slice ${currentSlice + 1} of ${sliceCount}` : "slice unknown";
  const viewerStatusText = loading
    ? "Loading image preview"
    : `${project.name}, subject ${subjectId ?? "unknown"}, sequence ${sequence}, ${planeLabel} plane, ${sliceStatus}.`;
  const keyboardHelp = canNavigateSlices
    ? "Use Left and Right arrow keys or Page Up and Page Down to move between slices. Home and End jump to the first or last slice. Escape leaves the image viewer."
    : "Image preview is focusable for inspection. Slice navigation is unavailable for this preview.";

  const requestSliceChange = (nextSlice: number) => {
    if (!canNavigateSlices) {
      return;
    }

    const boundedSlice = Math.min(Math.max(nextSlice, 0), maxSliceIndex);
    if (boundedSlice !== currentSlice) {
      onSliceChange(boundedSlice);
    }
  };

  const handleViewerKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.currentTarget.blur();
      return;
    }

    if (!canNavigateSlices) {
      return;
    }

    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
      case "PageDown":
        event.preventDefault();
        requestSliceChange(currentSlice + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
      case "PageUp":
        event.preventDefault();
        requestSliceChange(currentSlice - 1);
        break;
      case "Home":
        event.preventDefault();
        requestSliceChange(0);
        break;
      case "End":
        event.preventDefault();
        requestSliceChange(maxSliceIndex);
        break;
      default:
        break;
    }
  };

  if (!shouldShowViewer) {
    const isEmpty = dataState === "empty" || !dataState;
    const isRawDicom = dataState === "raw_dicom";
    const isConvertedContext = dataState === "converted_bids" || dataState === "mixed";
    const emptyTitle = isRawDicom
      ? "No image preview is available"
      : isEmpty
        ? "No imaging dataset loaded"
        : "No image preview is available";
    const emptyMessage = isRawDicom
      ? "This project currently contains raw DICOM candidates, but no validated preview source has been registered. Complete DICOM conversion to enable NIfTI preview."
      : isEmpty
        ? "Import a DICOM, BIDS, or NIfTI dataset to begin viewing imaging data."
        : isConvertedContext
          ? "Converted inventory exists, but the backend has not returned a verified preview URL for this subject and sequence."
          : "Imaging preview will become available once data conversion is complete.";
    const emptyCta = isRawDicom
      ? "Open Data & Conversion"
      : isEmpty
        ? "Import dataset"
        : "Review preview source details";

    return (
      <section
        className={`${styles.viewerCard} ${styles.emptyState}`}
        aria-label="Image viewer empty state"
      >
        <div className={styles.emptyContent}>
          <div className={styles.emptyGlyph} aria-hidden="true">
            <svg viewBox="0 0 80 80" width="64" height="64">
              <rect
                x="12"
                y="12"
                width="56"
                height="56"
                rx="6"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                opacity="0.4"
              />
              <line
                x1="40"
                y1="20"
                x2="40"
                y2="60"
                stroke="currentColor"
                strokeWidth="1"
                opacity="0.3"
              />
              <line
                x1="20"
                y1="40"
                x2="60"
                y2="40"
                stroke="currentColor"
                strokeWidth="1"
                opacity="0.3"
              />
              <circle cx="40" cy="40" r="4" fill="currentColor" opacity="0.5" />
            </svg>
          </div>
          <h3>{emptyTitle}</h3>
          <p>{emptyMessage}</p>
          <div className={styles.emptyMeta}>
            <span>
              Project state: <b>{dataState ?? "unknown"}</b>
            </span>
            {isRawDicom ? (
              <span className={styles.emptyWarning}>
                Raw DICOM preview is intentionally disabled to avoid misreading placeholder imagery
                as real patient data.
              </span>
            ) : null}
          </div>
          <div className={styles.emptyActions}>
            <span className={styles.emptyNextAction}>Next: {emptyCta}</span>
            <span className={styles.emptyHint}>
              {isRawDicom
                ? "Use the Data & Conversion workspace below"
                : "Use the project workspace below"}
            </span>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.viewerCard}>
      <div className={styles.toolbar}>
        <div className={`${styles.toolbarGroup} ${styles.toolbarSelectors}`}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Subject</span>
            <select
              className={`${styles.scanSelect} ${styles.subjectSelect}`}
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
          </label>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Sequence</span>
            <select
              className={styles.scanSelect}
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
          </label>
        </div>
        <div className={styles.planeSegmented} role="tablist" aria-label="Anatomical plane">
          {planeOptions.map((item) => (
            <button
              key={item.value}
              type="button"
              role="tab"
              aria-selected={activePlane === item.value}
              className={`${styles.planeSegment} ${
                activePlane === item.value ? styles.activePlane : ""
              }`}
              onClick={() => onPlaneChange(item.value)}
              title={`${item.label} plane`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className={`${styles.toolbarGroup} ${styles.toolbarActions}`}>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="Fullscreen"
            title="Fullscreen"
          >
            <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
              <path
                fill="currentColor"
                d="M2 2h4v1.5H3.5V6H2V2zm12 0v4h-1.5V3.5H10V2h4zM2 14v-4h1.5v2.5H6V14H2zm12 0h-4v-1.5h2.5V10H14v4z"
              />
            </svg>
          </button>
        </div>
      </div>
      <div
        className={styles.canvas}
        role="group"
        tabIndex={0}
        aria-busy={loading}
        aria-label={`Medical image viewer: ${viewerStatusText}`}
        aria-describedby="medical-image-viewer-status medical-image-viewer-keyboard-help"
        onKeyDown={handleViewerKeyDown}
      >
        {preview?.preview_url ? (
          <img
            className={styles.previewImage}
            src={preview.preview_url}
            alt={`${project.name} ${subjectId ?? "selected subject"} ${sequence} ${planeLabel} medical image preview`}
            loading="lazy"
            decoding="async"
          />
        ) : null}
        {loading ? (
          <div className={styles.loadingOverlay} role="status" aria-live="polite">
            <span className={styles.loadingOrbit} aria-hidden="true" />
            <span>Loading image preview</span>
          </div>
        ) : null}
        <div className={styles.sliceRule}>
          <span>S</span>
          <i />
          <span>I</span>
        </div>
        <p id="medical-image-viewer-status" className={styles.srOnly} aria-live="polite">
          {viewerStatusText}
        </p>
        <p id="medical-image-viewer-keyboard-help" className={styles.srOnly}>
          {keyboardHelp}
        </p>
      </div>
      <div className={styles.statusBar} aria-label="Viewer status">
        <span className={styles.statusItem}>
          Slice <b>{loading ? "..." : sliceCount ? `${currentSlice + 1} / ${sliceCount}` : "-"}</b>
        </span>
        <span className={styles.statusItem}>
          Plane <b>{planeLabel}</b>
        </span>
        <span className={styles.statusItem}>
          Source <b>{sourceSummary}</b>
        </span>
        <span className={styles.statusItem}>
          Dims <b>{dimensions.length ? dimensions.join(" x ") : "unknown"}</b>
        </span>
        <span className={styles.statusItem}>
          Spacing <b>{spacing.length ? spacing.slice(0, 3).join(" x ") : "pending"}</b>
        </span>
      </div>
      <div className={styles.dock} role="toolbar" aria-label="Viewer canvas tools">
        {[
          {
            label: "Window / Level",
            icon: (
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
                <path fill="currentColor" d="M8 2.5a5.5 5.5 0 0 0 0 11z" opacity="0.55" />
              </svg>
            ),
          },
          {
            label: "Pan",
            icon: (
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M8 1.5l1.6 1.6-1.1 1.1 3.3 3.3 1.1-1.1L14.5 8 13 9.5l-1.1-1.1-3.3 3.3 1.1 1.1L8 14.5 6.4 12.9l1.1-1.1-3.3-3.3-1.1 1.1L1.5 8l1.6-1.6 1.1 1.1 3.3-3.3-1.1-1.1L8 1.5z"
                />
              </svg>
            ),
          },
          {
            label: "Zoom",
            icon: (
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
                <path
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  d="M10.5 10.5L14 14"
                />
                <path
                  stroke="currentColor"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  d="M7 5v4M5 7h4"
                />
              </svg>
            ),
          },
          {
            label: "Crosshair",
            icon: (
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <path
                  stroke="currentColor"
                  strokeWidth="1.3"
                  strokeLinecap="round"
                  d="M8 1v4M8 11v4M1 8h4M11 8h4"
                />
                <circle cx="8" cy="8" r="1.4" fill="currentColor" />
              </svg>
            ),
          },
          {
            label: "Grid",
            icon: (
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <path
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  d="M2 2h12v12H2z M6 2v12 M10 2v12 M2 6h12 M2 10h12"
                />
              </svg>
            ),
          },
          {
            label: "Measure",
            icon: (
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <path
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  d="M2 14L14 2 M3 11l2 2 M6 8l2 2 M9 5l2 2"
                />
              </svg>
            ),
          },
        ].map((item, index) => (
          <button
            key={item.label}
            type="button"
            title={item.label}
            aria-label={item.label}
            aria-pressed={index === 0}
            className={`${styles.iconButton} ${index === 0 ? styles.selectedTool : ""}`}
          >
            {item.icon}
          </button>
        ))}
      </div>
      <aside className={styles.inspector} aria-label="Image metadata and validation">
        <header className={styles.inspectorHeader}>
          <h4>Inspector</h4>
          <span className={styles.validationPill} data-status={validation.status}>
            Validation {validation.status}
          </span>
        </header>
        <dl className={styles.inspectorMeta}>
          <div>
            <dt>Preview</dt>
            <dd>
              {preview?.source === "nifti"
                ? `${planeLabel} NIfTI, slice ${(preview.slice_index ?? 0) + 1} / ${preview.slice_count ?? "?"}`
                : preview?.message || "No preview source registered"}
            </dd>
          </div>
          <div>
            <dt>Dimensions</dt>
            <dd>{dimensions.length ? dimensions.join(" x ") : "unknown"}</dd>
          </div>
          <div>
            <dt>Voxel spacing</dt>
            <dd>{spacing.length ? spacing.slice(0, 3).join(" x ") : "pending"}</dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{sourceSummary}</dd>
          </div>
        </dl>
        {visibleValidationIssues.length ? (
          <div className={styles.inspectorIssues} aria-label="Validation issues">
            <h5>Issues</h5>
            <ul>
              {visibleValidationIssues.map((issue) => (
                <li
                  key={`${issue.code}-${issue.subject_id ?? "project"}-${issue.sequence ?? "all"}`}
                  className={styles.issueRow}
                  data-severity={issue.severity}
                >
                  <span className={styles.issueSeverity}>{issue.severity}</span>
                  <span className={styles.issueMessage}>{issue.message}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className={styles.inspectorEmpty}>No checklist issues detected.</p>
        )}
        {sliceCount > 1 ? (
          <div className={styles.inspectorSlice}>
            <label htmlFor="viewer-slice-slider">Slice</label>
            <input
              id="viewer-slice-slider"
              className={styles.sliceSlider}
              type="range"
              min={0}
              max={sliceCount - 1}
              value={currentSlice}
              onChange={(event) => onSliceChange(Number(event.target.value))}
              aria-label="Slice index"
            />
            <span className={styles.sliceReadout}>
              {currentSlice + 1} / {sliceCount}
            </span>
          </div>
        ) : null}
      </aside>
    </section>
  );
}
