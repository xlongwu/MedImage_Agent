import { useState, type KeyboardEvent } from "react";

import { Badge, Icon } from "../../components/ui";
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
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(105);
  const [failedPreviewUrl, setFailedPreviewUrl] = useState<string | null>(null);
  const sliceCount = Math.max(preview?.slice_count ?? 0, 0);
  const maxSliceIndex = Math.max(sliceCount - 1, 0);
  const currentSlice = Math.min(Math.max(preview?.slice_index ?? 0, 0), maxSliceIndex);
  const planeOptions: Array<{ value: ImagePlane; label: string }> = [
    { value: "axial", label: t("viewer.plane.axial") },
    { value: "sagittal", label: t("viewer.plane.sagittal") },
    { value: "coronal", label: t("viewer.plane.coronal") },
  ];
  const planeLabel =
    planeOptions.find((item) => item.value === plane)?.label ?? t("viewer.plane.axial");
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
  const visibleValidationIssues = (validation.issues ?? []).slice(0, 5);
  const hasRealPreview = hasRealImagePreview(preview);
  const canNavigateSlices = sliceCount > 1 && !loading;
  const imageLoadFailed = Boolean(preview?.preview_url && failedPreviewUrl === preview.preview_url);
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

  const requestSliceChange = (nextSlice: number) => {
    if (!canNavigateSlices) return;
    const boundedSlice = Math.min(Math.max(nextSlice, 0), maxSliceIndex);
    if (boundedSlice !== currentSlice) onSliceChange(boundedSlice);
  };

  const handleViewerKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.currentTarget.blur();
      return;
    }
    if (!canNavigateSlices) return;
    const nextByKey: Record<string, number> = {
      ArrowRight: currentSlice + 1,
      ArrowDown: currentSlice + 1,
      PageDown: currentSlice + 1,
      ArrowLeft: currentSlice - 1,
      ArrowUp: currentSlice - 1,
      PageUp: currentSlice - 1,
      Home: 0,
      End: maxSliceIndex,
    };
    if (event.key in nextByKey) {
      event.preventDefault();
      requestSliceChange(nextByKey[event.key]);
    }
  };

  if (!hasRealPreview) {
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
            <Icon height={28} name="results" width={28} />
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
    <section className={styles.viewerCard} aria-label={t("viewer.workspace")}>
      <aside className={styles.controls} aria-label={t("viewer.controls")}>
        <PaneHeader title={t("viewer.imageControls")} subtitle={t("viewer.displayOnly")} />
        <label className={styles.field}>
          <span>{t("viewer.subject")}</span>
          <select
            aria-label={t("viewer.subject")}
            disabled={!imageSources.subjects.length}
            onChange={(event) => onSubjectChange(event.target.value)}
            value={subjectId || ""}
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
          <span>{t("viewer.sequence")}</span>
          <select
            aria-label={t("viewer.sequence")}
            onChange={(event) => onSequenceChange(event.target.value)}
            value={sequence}
          >
            {(sequenceOptions.length ? sequenceOptions : project.sequences).map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <fieldset className={styles.controlGroup}>
          <legend>{t("viewer.anatomicalPlane")}</legend>
          <div
            className={styles.planeSegmented}
            role="tablist"
            aria-label={t("viewer.anatomicalPlane")}
          >
            {planeOptions.map((item) => (
              <button
                aria-selected={plane === item.value}
                className={plane === item.value ? styles.activePlane : undefined}
                key={item.value}
                onClick={() => onPlaneChange(item.value)}
                role="tab"
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset className={styles.controlGroup}>
          <legend>{t("viewer.display")}</legend>
          <label className={styles.sliderField}>
            <span>
              {t("viewer.brightness")} <b>{brightness}%</b>
            </span>
            <input
              aria-label={t("viewer.brightness")}
              max={160}
              min={40}
              onChange={(event) => setBrightness(Number(event.target.value))}
              type="range"
              value={brightness}
            />
          </label>
          <label className={styles.sliderField}>
            <span>
              {t("viewer.contrast")} <b>{contrast}%</b>
            </span>
            <input
              aria-label={t("viewer.contrast")}
              max={180}
              min={40}
              onChange={(event) => setContrast(Number(event.target.value))}
              type="range"
              value={contrast}
            />
          </label>
        </fieldset>
        <fieldset className={styles.controlGroup}>
          <legend>{t("viewer.overlays")}</legend>
          <label className={styles.disabledToggle} title={t("viewer.overlayUnavailable")}>
            <input aria-label={t("viewer.activationMap")} disabled type="checkbox" />
            <span>{t("viewer.activationMap")}</span>
            <small>{t("common.unavailable")}</small>
          </label>
          <label className={styles.disabledToggle} title={t("viewer.overlayUnavailable")}>
            <input aria-label={t("viewer.roiAtlas")} disabled type="checkbox" />
            <span>{t("viewer.roiAtlas")}</span>
            <small>{t("common.unavailable")}</small>
          </label>
          <p>{t("viewer.overlayUnavailable")}</p>
        </fieldset>
        <details className={styles.sourceDetails}>
          <summary>{t("viewer.source")}</summary>
          <code>{sourceSummary}</code>
        </details>
      </aside>

      <div className={styles.canvasWorkspace}>
        <header className={styles.canvasHeader}>
          <div>
            <strong>{subjectId ?? t("viewer.unknownSubject")}</strong>
            <span>{sequence}</span>
          </div>
          <Badge tone="neutral">{planeLabel}</Badge>
        </header>
        <div
          aria-busy={loading}
          aria-describedby="medical-image-viewer-status medical-image-viewer-keyboard-help"
          aria-label={t("viewer.aria", { status: viewerStatusText })}
          className={styles.canvas}
          onKeyDown={handleViewerKeyDown}
          role="group"
          tabIndex={0}
        >
          {!imageLoadFailed && preview?.preview_url ? (
            <img
              alt={t("viewer.imageAlt", {
                project: project.name,
                subject: subjectId ?? t("viewer.selectedSubject"),
                sequence,
                plane: planeLabel,
              })}
              className={styles.previewImage}
              decoding="async"
              loading="lazy"
              onError={() => setFailedPreviewUrl(preview.preview_url)}
              onLoad={() => setFailedPreviewUrl(null)}
              src={preview.preview_url}
              style={{
                filter: `grayscale(1) brightness(${brightness / 100}) contrast(${contrast / 100})`,
              }}
            />
          ) : null}
          {imageLoadFailed ? (
            <div className={styles.imageError} role="alert">
              <Icon height={22} name="circle-alert" width={22} />
              <strong>{t("viewer.previewLoadFailed")}</strong>
              <span>{t("viewer.previewLoadFailedDescription")}</span>
            </div>
          ) : null}
          {loading ? (
            <div className={styles.loadingOverlay} role="status" aria-live="polite">
              <span className={styles.loadingOrbit} aria-hidden="true" />
              <span>{t("viewer.loadingStatus")}</span>
            </div>
          ) : null}
          <div className={styles.orientationLabels} aria-hidden="true">
            <span data-position="top">S</span>
            <span data-position="bottom">I</span>
            <span data-position="left">L</span>
            <span data-position="right">R</span>
          </div>
          <p id="medical-image-viewer-status" className={styles.srOnly} aria-live="polite">
            {viewerStatusText}
          </p>
          <p id="medical-image-viewer-keyboard-help" className={styles.srOnly}>
            {canNavigateSlices ? t("viewer.keyboardNavigation") : t("viewer.keyboardInspection")}
          </p>
        </div>
        <div className={styles.sliceControl}>
          <span>{t("viewer.slice")}</span>
          <input
            aria-label={t("viewer.sliceIndex")}
            disabled={!canNavigateSlices}
            max={maxSliceIndex}
            min={0}
            onChange={(event) => onSliceChange(Number(event.target.value))}
            type="range"
            value={currentSlice}
          />
          <strong>{sliceCount ? `${currentSlice + 1} / ${sliceCount}` : "-"}</strong>
        </div>
        <div className={styles.statusBar} aria-label={t("viewer.status")}>
          <span>
            {t("viewer.slice")} <b>{sliceCount ? `${currentSlice + 1} / ${sliceCount}` : "-"}</b>
          </span>
          <span>
            {t("viewer.dimensionsShort")}{" "}
            <b>{dimensions.length ? dimensions.join(" × ") : t("viewer.unknown")}</b>
          </span>
          <span>
            {t("viewer.spacing")}{" "}
            <b>{spacing.length ? spacing.slice(0, 3).join(" × ") : t("viewer.pending")}</b>
          </span>
          <span>
            {t("viewer.source")} <b>{sourceSummary}</b>
          </span>
        </div>
      </div>

      <aside className={styles.inspector} aria-label={t("viewer.inspector.aria")}>
        <PaneHeader title={t("viewer.qcInspector")} subtitle={t("viewer.qcEvidenceDescription")} />
        <div className={styles.validationSummary}>
          <span className={styles.validationPill} data-status={validationStatus}>
            {t("viewer.inspector.validation", { status: validationStatus })}
          </span>
          <dl>
            <div>
              <dt>{t("viewer.qcSubjects")}</dt>
              <dd>{validation.subject_count ?? t("common.unavailable")}</dd>
            </div>
            <div>
              <dt>{t("viewer.qcSequences")}</dt>
              <dd>{validation.sequence_count ?? t("common.unavailable")}</dd>
            </div>
            <div>
              <dt>{t("viewer.qcSources")}</dt>
              <dd>{validation.source_count ?? t("common.unavailable")}</dd>
            </div>
          </dl>
        </div>
        <section className={styles.qcSection}>
          <h4>{t("viewer.inspector.issues")}</h4>
          {visibleValidationIssues.length ? (
            <ul>
              {visibleValidationIssues.map((issue) => (
                <li
                  data-severity={issue.severity}
                  key={`${issue.code}-${issue.subject_id ?? "project"}-${issue.sequence ?? "all"}`}
                >
                  <strong>{issue.severity}</strong>
                  <span>{issue.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>{t("viewer.inspector.noIssues")}</p>
          )}
        </section>
        <section className={styles.qcSection}>
          <h4>{t("viewer.advancedQc")}</h4>
          <div className={styles.unavailableMetrics}>
            {["FD", "SNR", "tSNR", t("viewer.outlierVolumes")].map((label) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{t("common.unavailable")}</strong>
              </div>
            ))}
          </div>
          <p>{t("viewer.qcNotGenerated")}</p>
        </section>
      </aside>
    </section>
  );
}

function PaneHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className={styles.paneHeader}>
      <h3>{title}</h3>
      <p>{subtitle}</p>
    </header>
  );
}
