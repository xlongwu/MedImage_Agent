import type { KeyboardEvent } from "react";

import { useI18n } from "../../i18n/useI18n";
import type {
  ImagePlane,
  ImagePreview,
  ImageSourceFile,
  ImageSources,
  ImageValidationReport,
} from "../../lib/types/image";
import type { ProjectDetail } from "../../lib/types/project";
import type { ProjectDataState } from "../../lib/projectWorkflow";
import { hasRealImagePreview } from "./imagePreviewEvidence";
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
  const { t } = useI18n();
  const rawSliceCount = preview?.slice_count ?? 0;
  const sliceCount = rawSliceCount > 0 ? rawSliceCount : 0;
  const maxSliceIndex = Math.max(sliceCount - 1, 0);
  const currentSlice = Math.min(Math.max(preview?.slice_index ?? 0, 0), maxSliceIndex);
  const activePlane = plane;
  const planeOptions: Array<{ axis: string; value: ImagePlane; label: string }> = [
    { axis: "S", value: "sagittal", label: t("viewer.plane.sagittal") },
    { axis: "A", value: "axial", label: t("viewer.plane.axial") },
    { axis: "C", value: "coronal", label: t("viewer.plane.coronal") },
  ];
  const planeLabel =
    planeOptions.find((item) => item.value === activePlane)?.label ?? t("viewer.plane.axial");
  const dimensions = sourceFile?.dimensions?.length
    ? sourceFile.dimensions
    : (preview?.dimensions ?? []);
  const spacing = sourceFile?.voxel_spacing ?? [];
  const sourceSummary =
    sourceFile?.relative_path ??
    preview?.source_path ??
    preview?.message ??
    t("viewer.noPreviewSource");
  const validationStatus = validation.status ?? "unavailable";
  const visibleValidationIssues = (validation.issues ?? []).slice(0, 3);

  // Viewer display conditions per design spec:
  // - Raw DICOM / Empty / unknown: do NOT show pseudo NIfTI viewer; show Empty State
  // - Only show full viewer when there is a real preview URL
  const hasRealPreview = hasRealImagePreview(preview);
  const shouldShowViewer = hasRealPreview;
  const canNavigateSlices = sliceCount > 1 && !loading;
  const sliceStatus = sliceCount
    ? t("viewer.sliceOf", { current: currentSlice + 1, total: sliceCount })
    : t("viewer.sliceUnknown");
  const viewerStatusText = loading
    ? t("viewer.loadingStatus")
    : t("viewer.statusDescription", {
        project: project.name,
        subject: subjectId ?? t("viewer.unknownSubject"),
        sequence,
        plane: planeLabel,
        slice: sliceStatus,
      });
  const keyboardHelp = canNavigateSlices
    ? t("viewer.keyboardNavigation")
    : t("viewer.keyboardInspection");

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
      ? t("viewer.empty.noPreview")
      : isEmpty
        ? t("viewer.empty.noDataset")
        : t("viewer.empty.noPreview");
    const emptyMessage = isRawDicom
      ? t("viewer.empty.rawDicom")
      : isEmpty
        ? t("viewer.empty.dataset")
        : isConvertedContext
          ? t("viewer.empty.converted")
          : t("viewer.empty.conversionPending");
    const emptyCta = isRawDicom
      ? t("viewer.empty.openConversion")
      : isEmpty
        ? t("viewer.empty.importDataset")
        : t("viewer.empty.reviewDetails");

    return (
      <section
        className={`${styles.viewerCard} ${styles.emptyState}`}
        aria-label={t("viewer.empty.aria")}
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
              {t("viewer.empty.projectState")}: <b>{dataState ?? t("viewer.unknown")}</b>
            </span>
            {isRawDicom ? (
              <span className={styles.emptyWarning}>{t("viewer.empty.rawWarning")}</span>
            ) : null}
          </div>
          <div className={styles.emptyActions}>
            <span className={styles.emptyNextAction}>
              {t("viewer.empty.next", { action: emptyCta })}
            </span>
            <span className={styles.emptyHint}>
              {isRawDicom ? t("viewer.empty.conversionHint") : t("viewer.empty.projectHint")}
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
            <span className={styles.fieldLabel}>{t("viewer.subject")}</span>
            <select
              className={`${styles.scanSelect} ${styles.subjectSelect}`}
              value={subjectId || ""}
              onChange={(event) => onSubjectChange(event.target.value)}
              disabled={!imageSources.subjects.length}
              aria-label={t("viewer.subject")}
            >
              {imageSources.subjects.length ? (
                imageSources.subjects.map((item) => (
                  <option key={item.subject_id} value={item.subject_id}>
                    {item.subject_id}
                  </option>
                ))
              ) : (
                <option value="">{t("viewer.noSources")}</option>
              )}
            </select>
          </label>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t("viewer.sequence")}</span>
            <select
              className={styles.scanSelect}
              value={sequence}
              onChange={(event) => onSequenceChange(event.target.value)}
              aria-label={t("viewer.sequence")}
            >
              {(sequenceOptions.length ? sequenceOptions : project.sequences).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div
          className={styles.planeSegmented}
          role="tablist"
          aria-label={t("viewer.anatomicalPlane")}
        >
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
              title={t("viewer.planeTitle", { plane: item.label })}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className={`${styles.toolbarGroup} ${styles.toolbarActions}`}>
          <button
            type="button"
            className={styles.iconButton}
            aria-label={t("viewer.fullscreen")}
            title={t("viewer.fullscreen")}
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
        aria-label={t("viewer.aria", { status: viewerStatusText })}
        aria-describedby="medical-image-viewer-status medical-image-viewer-keyboard-help"
        onKeyDown={handleViewerKeyDown}
      >
        {preview?.preview_url ? (
          <img
            className={styles.previewImage}
            src={preview.preview_url}
            alt={t("viewer.imageAlt", {
              project: project.name,
              subject: subjectId ?? t("viewer.selectedSubject"),
              sequence,
              plane: planeLabel,
            })}
            loading="lazy"
            decoding="async"
          />
        ) : null}
        {loading ? (
          <div className={styles.loadingOverlay} role="status" aria-live="polite">
            <span className={styles.loadingOrbit} aria-hidden="true" />
            <span>{t("viewer.loadingStatus")}</span>
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
      <div className={styles.statusBar} aria-label={t("viewer.status")}>
        <span className={styles.statusItem}>
          {t("viewer.slice")}{" "}
          <b>{loading ? "..." : sliceCount ? `${currentSlice + 1} / ${sliceCount}` : "-"}</b>
        </span>
        <span className={styles.statusItem}>
          {t("viewer.plane")} <b>{planeLabel}</b>
        </span>
        <span className={styles.statusItem}>
          {t("viewer.source")} <b>{sourceSummary}</b>
        </span>
        <span className={styles.statusItem}>
          {t("viewer.dimensionsShort")}{" "}
          <b>{dimensions.length ? dimensions.join(" x ") : t("viewer.unknown")}</b>
        </span>
        <span className={styles.statusItem}>
          {t("viewer.spacing")}{" "}
          <b>{spacing.length ? spacing.slice(0, 3).join(" x ") : t("viewer.pending")}</b>
        </span>
      </div>
      <div className={styles.dock} role="toolbar" aria-label={t("viewer.canvasTools")}>
        {[
          {
            label: t("viewer.tool.windowLevel"),
            icon: (
              <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
                <path fill="currentColor" d="M8 2.5a5.5 5.5 0 0 0 0 11z" opacity="0.55" />
              </svg>
            ),
          },
          {
            label: t("viewer.tool.pan"),
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
            label: t("viewer.tool.zoom"),
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
            label: t("viewer.tool.crosshair"),
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
            label: t("viewer.tool.grid"),
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
            label: t("viewer.tool.measure"),
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
      <aside className={styles.inspector} aria-label={t("viewer.inspector.aria")}>
        <header className={styles.inspectorHeader}>
          <h4>{t("viewer.inspector.title")}</h4>
          <span className={styles.validationPill} data-status={validationStatus}>
            {t("viewer.inspector.validation", { status: validationStatus })}
          </span>
        </header>
        <dl className={styles.inspectorMeta}>
          <div>
            <dt>{t("viewer.inspector.preview")}</dt>
            <dd>
              {preview?.source === "nifti"
                ? t("viewer.inspector.nifti", {
                    plane: planeLabel,
                    current: (preview.slice_index ?? 0) + 1,
                    total: preview.slice_count ?? "?",
                  })
                : preview?.message || t("viewer.inspector.noSource")}
            </dd>
          </div>
          <div>
            <dt>{t("viewer.inspector.dimensions")}</dt>
            <dd>{dimensions.length ? dimensions.join(" x ") : t("viewer.unknown")}</dd>
          </div>
          <div>
            <dt>{t("viewer.inspector.voxelSpacing")}</dt>
            <dd>{spacing.length ? spacing.slice(0, 3).join(" x ") : t("viewer.pending")}</dd>
          </div>
          <div>
            <dt>{t("viewer.source")}</dt>
            <dd>{sourceSummary}</dd>
          </div>
        </dl>
        {visibleValidationIssues.length ? (
          <div
            className={styles.inspectorIssues}
            aria-label={t("viewer.inspector.validationIssues")}
          >
            <h5>{t("viewer.inspector.issues")}</h5>
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
          <p className={styles.inspectorEmpty}>{t("viewer.inspector.noIssues")}</p>
        )}
        {sliceCount > 1 ? (
          <div className={styles.inspectorSlice}>
            <label htmlFor="viewer-slice-slider">{t("viewer.slice")}</label>
            <input
              id="viewer-slice-slider"
              className={styles.sliceSlider}
              type="range"
              min={0}
              max={sliceCount - 1}
              value={currentSlice}
              onChange={(event) => onSliceChange(Number(event.target.value))}
              aria-label={t("viewer.sliceIndex")}
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
