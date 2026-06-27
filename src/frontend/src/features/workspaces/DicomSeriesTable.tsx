import { useEffect, useMemo, useRef, useState } from "react";
import { Badge, Button, Card, Table, TableEmpty } from "../../components/ui";
import type {
  ConversionDryRunResponse,
  ConversionMappingPreview,
  ConversionSourceSummary,
} from "../../types";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { DataSeriesSelection } from "../../lib/workspaceSelection";
import styles from "./DicomSeriesTable.module.css";

type FilterId = "all" | "dicom_series" | "mapped" | "warnings" | "manual";
type DryRunRestoreState = "idle" | "loading" | "restored" | "refresh_required" | "error";

type DicomRow = {
  acquisition: string;
  description: string;
  fileCount: string;
  id: string;
  modality: string;
  sourceKind: "project_summary" | "source_summary" | "mapping_preview";
  statusLabel: string;
  statusTone: "neutral" | "info" | "success" | "warning" | "danger";
  subject: string;
  subjectDetail: string;
  series: string;
  seriesDetail: string;
  warnings: string[];
};

const filters: Array<{ id: FilterId; label: string }> = [
  { id: "all", label: "All" },
  { id: "dicom_series", label: "DICOM series" },
  { id: "mapped", label: "Mapped" },
  { id: "warnings", label: "Warnings" },
  { id: "manual", label: "Manual review" },
];

const VIRTUALIZATION_THRESHOLD = 40;
const VIRTUAL_ROW_HEIGHT = 72;
const VIRTUAL_WINDOW_HEIGHT = 420;
const VIRTUAL_OVERSCAN = 4;

export interface DicomSeriesTableProps {
  dryRun: ConversionDryRunResponse | null;
  error: string;
  inventory: ProjectInventory;
  loading: boolean;
  onGenerateDryRun: () => void;
  onReviewSelectionChange?: (selection: DataSeriesSelection | null) => void;
  projectId: string | null;
  restoreMessage?: string;
  restoreState?: DryRunRestoreState;
}

export function DicomSeriesTable({
  dryRun,
  error,
  inventory,
  loading,
  onGenerateDryRun,
  onReviewSelectionChange,
  projectId,
  restoreMessage = "",
  restoreState = "idle",
}: DicomSeriesTableProps) {
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterId>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [tableScrollTop, setTableScrollTop] = useState(0);
  const tableViewportRef = useRef<HTMLDivElement>(null);

  const rows = useMemo(() => buildDicomRows(inventory, dryRun), [dryRun, inventory]);
  const filteredRows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => {
      const haystack = [
        row.subject,
        row.subjectDetail,
        row.series,
        row.seriesDetail,
        row.modality,
        row.description,
        row.acquisition,
        row.statusLabel,
        row.warnings.join(" "),
      ]
        .join(" ")
        .toLowerCase();
      const matchesQuery = !needle || haystack.includes(needle);
      const matchesFilter =
        activeFilter === "all" ||
        (activeFilter === "dicom_series" &&
          /dicom|series/i.test(
            `${row.modality} ${row.series} ${row.subjectDetail} ${row.sourceKind}`,
          )) ||
        (activeFilter === "mapped" && row.sourceKind === "mapping_preview") ||
        (activeFilter === "warnings" && row.warnings.length > 0) ||
        (activeFilter === "manual" &&
          /manual|low|warning/i.test(`${row.statusLabel} ${row.warnings.join(" ")}`));
      return matchesQuery && matchesFilter;
    });
  }, [activeFilter, query, rows]);

  useEffect(() => {
    setSelectedIds((current) => {
      const rowIds = new Set(rows.map((row) => row.id));
      const next = new Set([...current].filter((id) => rowIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [rows]);

  useEffect(() => {
    if (!selectedIds.size) return;
    const rowIds = new Set(rows.map((row) => row.id));
    if (![...selectedIds].some((id) => rowIds.has(id))) {
      onReviewSelectionChange?.(null);
    }
  }, [onReviewSelectionChange, rows, selectedIds]);

  const selectedRows = rows.filter((row) => selectedIds.has(row.id));
  const sourceCount = dryRun?.source_summaries.length ?? (inventory.hasRawDicom ? 1 : 0);
  const mappingCount = dryRun?.mapping_preview.length ?? 0;
  const mappingCountLabel = dryRun
    ? String(mappingCount)
    : restoreState === "loading"
      ? "Loading"
      : "Refresh required";
  const manualReviewRows = rows.filter((row) =>
    /manual|required|low/i.test(`${row.statusLabel} ${row.warnings.join(" ")}`),
  );
  const rowWarningMessages = rows.flatMap((row) => row.warnings);
  const warningMessages = [...(dryRun?.warnings ?? []), ...rowWarningMessages];
  const blockingMessages = dryRun?.blocking_issues ?? [];
  const usesVirtualization = filteredRows.length > VIRTUALIZATION_THRESHOLD;
  const virtualRange = useMemo(() => {
    if (!usesVirtualization) {
      return {
        endIndex: filteredRows.length,
        startIndex: 0,
      };
    }

    const visibleRows = Math.ceil(VIRTUAL_WINDOW_HEIGHT / VIRTUAL_ROW_HEIGHT);
    const maxStartIndex = Math.max(0, filteredRows.length - visibleRows - VIRTUAL_OVERSCAN);
    const startIndex = Math.min(
      Math.max(0, Math.floor(tableScrollTop / VIRTUAL_ROW_HEIGHT) - VIRTUAL_OVERSCAN),
      maxStartIndex,
    );
    const endIndex = Math.min(
      filteredRows.length,
      startIndex + visibleRows + VIRTUAL_OVERSCAN * 2,
    );

    return { endIndex, startIndex };
  }, [filteredRows.length, tableScrollTop, usesVirtualization]);
  const renderedRows = usesVirtualization
    ? filteredRows.slice(virtualRange.startIndex, virtualRange.endIndex)
    : filteredRows;
  const topSpacerHeight = usesVirtualization
    ? virtualRange.startIndex * VIRTUAL_ROW_HEIGHT
    : 0;
  const bottomSpacerHeight = usesVirtualization
    ? (filteredRows.length - virtualRange.endIndex) * VIRTUAL_ROW_HEIGHT
    : 0;

  useEffect(() => {
    setTableScrollTop(0);
    if (tableViewportRef.current) {
      tableViewportRef.current.scrollTop = 0;
    }
  }, [activeFilter, dryRun, query]);

  const toggleRow = (row: DicomRow) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(row.id)) {
        next.delete(row.id);
      } else {
        next.add(row.id);
      }
      return next;
    });

    if (selectedIds.has(row.id)) {
      const fallbackRow = rows.find((item) => item.id !== row.id && selectedIds.has(item.id));
      onReviewSelectionChange?.(fallbackRow ? dicomRowSelection(fallbackRow) : null);
    } else {
      onReviewSelectionChange?.(dicomRowSelection(row));
    }
  };

  return (
    <Card className={styles.panel} tone="muted">
      <div className={styles.header}>
        <div>
          <h3>DICOM series browser</h3>
          <p>
            Review raw DICOM sources and dry-run mappings before any conversion write is requested.
            Per-series file totals are shown only when the backend returns verified detail.
          </p>
        </div>
        <Button disabled={!projectId || loading || !inventory.hasRawDicom} onClick={onGenerateDryRun}>
          {loading
            ? restoreState === "loading"
              ? "Loading preview..."
              : "Generating..."
            : dryRun
              ? "Refresh dry-run"
              : restoreState === "refresh_required" || restoreState === "error"
                ? "Refresh dry-run preview"
                : "Generate dry-run preview"}
        </Button>
      </div>

      <div className={styles.summaryStrip} aria-label="DICOM inventory summary">
        <div className={styles.summaryItem}>
          <span>Subject candidates</span>
          <strong>{inventory.rawDicomCandidates}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Series</span>
          <strong>{inventory.dicomSeriesCount}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Files</span>
          <strong>{inventory.dicomFileCount.toLocaleString()}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Dry-run mappings</span>
          <strong>{mappingCountLabel}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Manual review</span>
          <strong>{manualReviewRows.length}</strong>
        </div>
      </div>

      {!dryRun ? (
        <div className={styles.statusMessage}>
          {restoreState === "loading"
            ? "Checking for persisted dry-run mappings for the active project."
            : restoreMessage ||
              "Dry-run preview not loaded; refresh required. No mappings are being counted for this session until verified sources and suggested BIDS mappings are loaded."}
        </div>
      ) : null}
      {error ? (
        <div className={`${styles.statusMessage} ${styles.error}`} role="alert">
          Dry-run failed before any conversion write was requested. Review the backend response and
          retry when the project source state is available: {error}
        </div>
      ) : null}
      {dryRun ? (
        <ReviewSummary
          blockingMessages={blockingMessages}
          manualReviewCount={manualReviewRows.length}
          status={dryRun.status}
          warningMessages={warningMessages}
        />
      ) : null}

      <div className={styles.toolbar}>
        <div className={styles.search}>
          <label htmlFor="dicom-series-search">Search DICOM sources</label>
          <input
            id="dicom-series-search"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Subject, series UID, modality, path"
            type="search"
            value={query}
          />
        </div>
        <div className={styles.filters} aria-label="DICOM source filters">
          {filters.map((filter) => (
            <button
              key={filter.id}
              aria-pressed={activeFilter === filter.id}
              className={styles.filterButton}
              onClick={() => setActiveFilter(filter.id)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.tableWrap}>
        {usesVirtualization ? (
          <div className={styles.virtualizationStatus} role="status">
            Rendering rows {virtualRange.startIndex + 1}-{virtualRange.endIndex} of{" "}
            {filteredRows.length}. Scroll the table to inspect the full DICOM source list.
          </div>
        ) : null}
        <Table
          aria-rowcount={filteredRows.length}
          caption={`${sourceCount} source group(s), ${filteredRows.length} visible row(s)`}
          viewportClassName={usesVirtualization ? styles.virtualizedViewport : undefined}
          viewportProps={
            usesVirtualization
              ? {
                  "aria-label": "Virtualized DICOM series table",
                  onScroll: (event) => setTableScrollTop(event.currentTarget.scrollTop),
                }
              : undefined
          }
          viewportRef={tableViewportRef}
        >
          <thead>
            <tr>
              <th className={styles.checkboxCell} scope="col">
                Select
              </th>
              <th scope="col">Subject</th>
              <th scope="col">Series / source</th>
              <th scope="col">Files</th>
              <th scope="col">Modality</th>
              <th scope="col">Acquisition</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.length === 0 ? (
              <TableEmpty colSpan={7}>
                {emptyFilterMessage(activeFilter, dryRun, restoreState)}
              </TableEmpty>
            ) : (
              <>
                {usesVirtualization && topSpacerHeight > 0 ? (
                  <VirtualSpacer height={topSpacerHeight} />
                ) : null}
                {renderedRows.map((row, index) => (
                  <DicomSeriesRow
                    key={row.id}
                    ariaRowIndex={usesVirtualization ? virtualRange.startIndex + index + 2 : undefined}
                    checked={selectedIds.has(row.id)}
                    onToggle={toggleRow}
                    row={row}
                  />
                ))}
                {usesVirtualization && bottomSpacerHeight > 0 ? (
                  <VirtualSpacer height={bottomSpacerHeight} />
                ) : null}
              </>
            )}
          </tbody>
        </Table>
      </div>

      {selectedRows.length > 0 ? (
        <div className={styles.selectionPanel} aria-label="Selected DICOM sources">
          <strong>{selectedRows.length} selected for review</strong>
          <p>
            Selection is local to this browser session. It is review selection only: it is not
            persisted, does not approve mappings, and does not execute conversion.
          </p>
          <ul className={styles.selectionList}>
            {selectedRows.map((row) => (
              <li key={row.id}>{selectionLabel(row)}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </Card>
  );
}

function emptyFilterMessage(
  activeFilter: FilterId,
  dryRun: ConversionDryRunResponse | null,
  restoreState: DryRunRestoreState,
): string {
  if (!dryRun && (restoreState === "refresh_required" || restoreState === "error")) {
    return "Dry-run mappings are not loaded; refresh the preview before filtering restored mappings.";
  }
  if (activeFilter === "dicom_series") {
    return "No DICOM series rows match the current search. This filter matches DICOM source rows and dicom_series mapping previews.";
  }
  return "No DICOM sources match the current filters.";
}

function selectionLabel(row: DicomRow): string {
  const details = [row.modality, row.series].filter(Boolean).join(" - ");
  return [row.subject, details, row.seriesDetail].filter(Boolean).join(" - ");
}

function ReviewSummary({
  blockingMessages,
  manualReviewCount,
  status,
  warningMessages,
}: {
  blockingMessages: string[];
  manualReviewCount: number;
  status: ConversionDryRunResponse["status"];
  warningMessages: string[];
}) {
  const hasIssues = status !== "ready" || warningMessages.length > 0 || blockingMessages.length > 0;
  const statusTone = blockingMessages.length > 0 ? "danger" : status === "warning" ? "warning" : "success";

  return (
    <div className={styles.reviewSummary} aria-label="Dry-run review summary">
      <div className={styles.reviewSummaryHeader}>
        <strong>Dry-run review state</strong>
        <Badge tone={statusTone} size="sm">
          {status}
        </Badge>
      </div>
      <p>
        {hasIssues
          ? "Review warnings and blockers before using any mapping as approval material."
          : "Dry-run mappings are ready for human review. No conversion has been executed."}
      </p>
      <dl className={styles.reviewFacts}>
        <div>
          <dt>Warnings</dt>
          <dd>{warningMessages.length}</dd>
        </div>
        <div>
          <dt>Blocking issues</dt>
          <dd>{blockingMessages.length}</dd>
        </div>
        <div>
          <dt>Manual review</dt>
          <dd>{manualReviewCount}</dd>
        </div>
      </dl>
      {blockingMessages.length > 0 || warningMessages.length > 0 ? (
        <ul className={styles.reviewIssueList}>
          {[...blockingMessages, ...warningMessages].slice(0, 4).map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function DicomSeriesRow({
  ariaRowIndex,
  checked,
  onToggle,
  row,
}: {
  ariaRowIndex?: number;
  checked: boolean;
  onToggle: (row: DicomRow) => void;
  row: DicomRow;
}) {
  return (
    <tr aria-rowindex={ariaRowIndex}>
      <td className={styles.checkboxCell}>
        <input
          aria-label={`Select ${row.series}`}
          checked={checked}
          onChange={() => onToggle(row)}
          type="checkbox"
        />
      </td>
      <td>
        <span className={styles.subjectCell}>
          <strong>{row.subject}</strong>
          <span>{row.subjectDetail}</span>
        </span>
      </td>
      <td>
        <span className={styles.seriesCell}>
          <strong>{row.series}</strong>
          <span>{row.description}</span>
        </span>
      </td>
      <td>{row.fileCount}</td>
      <td>{row.modality}</td>
      <td>
        <span className={styles.muted}>{row.acquisition}</span>
      </td>
      <td>
        <span className={styles.statusCell}>
          <Badge tone={row.statusTone} size="sm">
            {row.statusLabel}
          </Badge>
        </span>
        {row.warnings.length > 0 ? (
          <span className={styles.warningList}>
            {row.warnings.slice(0, 2).map((warning) => (
              <span key={warning}>{warning}</span>
            ))}
          </span>
        ) : null}
      </td>
    </tr>
  );
}

function dicomRowSelection(row: DicomRow): DataSeriesSelection {
  return {
    evidenceLevel: row.sourceKind === "mapping_preview" ? "preview_only" : "metadata_only",
    series: row.series,
    seriesDetail: row.seriesDetail,
    sourceKind: row.sourceKind,
    status: row.statusLabel,
    subject: row.subject,
    subjectDetail: row.subjectDetail,
    warnings: row.warnings,
  };
}

function VirtualSpacer({ height }: { height: number }) {
  return (
    <tr aria-hidden="true" className={styles.virtualSpacer}>
      <td colSpan={7} style={{ height }} />
    </tr>
  );
}

function buildDicomRows(
  inventory: ProjectInventory,
  dryRun: ConversionDryRunResponse | null,
): DicomRow[] {
  if (dryRun?.mapping_preview.length) {
    return dryRun.mapping_preview.map((mapping, index) => mappingToRow(mapping, index));
  }

  if (dryRun?.source_summaries.length) {
    return dryRun.source_summaries.map((source) => sourceToRow(source));
  }

  if (!inventory.hasRawDicom) {
    return [];
  }

  return [
    {
      acquisition: "Not inspected",
      description: "Project inventory summary; generate dry-run for verified mapping rows.",
      fileCount: inventory.dicomFileCount.toLocaleString(),
      id: "project-summary",
      modality: inventory.modality,
      sourceKind: "project_summary",
      statusLabel: "Summary",
      statusTone: inventory.dicomSeriesCount > 0 ? "info" : "warning",
      subject: `${inventory.rawDicomCandidates} candidates`,
      subjectDetail: "Project-level diagnostics",
      series: `${inventory.dicomSeriesCount} series`,
      seriesDetail: "Source detection pending",
      warnings:
        inventory.dicomSeriesCount > 0
          ? []
          : ["No per-series metadata is currently available for this project."],
    },
  ];
}

function mappingToRow(mapping: ConversionMappingPreview, index: number): DicomRow {
  const seriesId =
    mapping.source_series_uid ||
    basename(mapping.source_path ?? "") ||
    mapping.suggested_relative_path ||
    `mapping-${index + 1}`;
  const suffix = [mapping.modality, mapping.suffix, mapping.task ? `task-${mapping.task}` : ""]
    .filter(Boolean)
    .join(" / ");
  const needsManual = mapping.confidence === "manual_required" || mapping.confidence === "low";
  const manualWarnings =
    needsManual && mapping.warnings.length === 0
      ? [
          mapping.confidence === "manual_required"
            ? "Manual review required before this mapping can be used."
            : "Low confidence mapping requires manual review.",
        ]
      : mapping.warnings;

  return {
    acquisition: mapping.session_id || "Session not assigned",
    description: mapping.suggested_relative_path || mapping.source_path || "Mapping path pending",
    fileCount: "per-series pending",
    id: `mapping-${index}-${seriesId}`,
    modality: suffix || mapping.source_type,
    sourceKind: "mapping_preview",
    statusLabel: mapping.confidence.replace(/_/g, " "),
    statusTone: needsManual ? "warning" : mapping.confidence === "high" ? "success" : "info",
    subject: mapping.subject_id || "Unassigned",
    subjectDetail: mapping.source_type,
    series: seriesId,
    seriesDetail: mapping.source_series_uid ? "Series UID" : "Source path",
    warnings: manualWarnings,
  };
}

function sourceToRow(source: ConversionSourceSummary): DicomRow {
  const subjectList = source.subject_candidates.slice(0, 3).join(", ");
  return {
    acquisition: "Dry-run source",
    description: source.root,
    fileCount: source.file_count.toLocaleString(),
    id: source.source_id,
    modality: source.source_type,
    sourceKind: "source_summary",
    statusLabel: source.exists ? "Detected" : "Missing",
    statusTone: source.exists ? (source.warnings.length ? "warning" : "success") : "danger",
    subject: subjectList || "No subject candidates",
    subjectDetail:
      source.subject_candidates.length > 3
        ? `+${source.subject_candidates.length - 3} more`
        : `${source.subject_candidates.length} candidate(s)`,
    series: `${source.series_count} series`,
    seriesDetail: source.source_id,
    warnings: source.warnings,
  };
}

function basename(path: string): string {
  return path.replace(/\\/g, "/").split("/").filter(Boolean).pop() ?? "";
}
