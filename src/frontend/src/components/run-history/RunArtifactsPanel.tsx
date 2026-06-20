import { useMemo, useState } from "react";
import type { RunArtifactPreviewResponse, RunArtifactRecord, RunSummaryPreview } from "../../types";
import {
  ARTIFACT_CATEGORIES,
  artifactPath,
  filterArtifacts,
  formatArtifactSize,
  getArtifactWarnings,
  groupArtifacts,
  isPreviewableArtifact,
  sortArtifacts,
} from "../projectRunsPanelModel";
import type { RunArtifactCategoryFilter, RunArtifactStateFilter } from "../projectRunsPanelModel";
import { ArtifactPreviewPane } from "./ArtifactPreviewPane";
import {
  artifactAttentionStyle,
  ArtifactBadgeRow,
  artifactCardStyle,
  artifactGroupHeaderStyle,
  artifactMetaGridStyle,
  filterGridStyle,
  filterLabelStyle,
  formatDate,
  headerStyle,
  monoPathStyle,
  PathActions,
  selectStyle,
  selectedArtifactCardStyle,
  smallButtonStyle,
  subtitleStyle,
  summaryPanelStyle,
  WarningList,
} from "./pathActions";

export function RunArtifactsPanel({
  artifacts,
  runSummary,
  selectedArtifactId,
  preview,
  loading,
  previewLoading,
  error,
  warnings,
  onRefresh,
  onPreview,
  onNotice,
}: {
  artifacts: RunArtifactRecord[];
  runSummary: RunSummaryPreview | null;
  selectedArtifactId: string | null;
  preview: RunArtifactPreviewResponse | null;
  loading: boolean;
  previewLoading: boolean;
  error: string;
  warnings: string[];
  onRefresh: () => void;
  onPreview: (artifact: RunArtifactRecord) => void;
  onNotice: (message: string) => void;
}) {
  const [categoryFilter, setCategoryFilter] = useState<RunArtifactCategoryFilter>("all");
  const [stateFilter, setStateFilter] = useState<RunArtifactStateFilter>("all");
  const [kindFilter, setKindFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const sortedArtifacts = useMemo(
    () => sortArtifacts(artifacts, runSummary),
    [artifacts, runSummary],
  );
  const kindOptions = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.kind).filter(Boolean))).sort(),
    [artifacts],
  );
  const sourceOptions = useMemo(
    () =>
      Array.from(
        new Set(artifacts.map((artifact) => artifact.source || "").filter(Boolean)),
      ).sort(),
    [artifacts],
  );
  const filteredArtifacts = useMemo(
    () =>
      filterArtifacts(sortedArtifacts, {
        category: categoryFilter,
        kind: kindFilter,
        state: stateFilter,
        source: sourceFilter,
      }),
    [categoryFilter, kindFilter, sortedArtifacts, sourceFilter, stateFilter],
  );
  const groupedArtifacts = useMemo(
    () => groupArtifacts(filteredArtifacts, runSummary),
    [filteredArtifacts, runSummary],
  );

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>Artifacts</h4>
          <span style={subtitleStyle}>Run-scoped reports, QC files, and logs.</span>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading} style={smallButtonStyle}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}
      <WarningList warnings={warnings} />

      {loading && !artifacts.length ? (
        <div className="empty" style={{ marginBottom: 8 }}>
          Loading artifacts...
        </div>
      ) : !artifacts.length ? (
        <div className="empty" style={{ marginBottom: 8 }}>
          No artifacts were discovered for this run. The run may not have produced any output files.
        </div>
      ) : (
        (() => {
          const existsCount = artifacts.filter((a) => a.exists).length;
          const missingCount = artifacts.length - existsCount;
          const previewableCount = artifacts.filter((a) => isPreviewableArtifact(a)).length;
          return (
            <>
              {warnings.length > 0 && (
                <div
                  style={{
                    marginBottom: 8,
                    padding: 8,
                    background: "rgba(255, 251, 242, 0.94)",
                    border: "1px solid rgba(242, 153, 74, 0.28)",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#9a5a15",
                  }}
                >
                  Artifact discovery returned {warnings.length} warning(s). Some artifacts may be
                  missing or inaccessible.
                </div>
              )}
              {missingCount > 0 && (
                <div
                  style={{
                    marginBottom: 8,
                    padding: 8,
                    background: "rgba(255, 245, 245, 0.92)",
                    border: "1px solid rgba(235, 87, 87, 0.24)",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#b53b3b",
                  }}
                >
                  {missingCount} artifact(s) are missing from disk.{" "}
                  {existsCount > 0 ? `${existsCount} file(s) are present.` : ""}
                </div>
              )}
              {existsCount > 0 && !previewableCount && (
                <div className="empty" style={{ marginBottom: 8 }}>
                  {existsCount} artifact(s) exist but none are previewable (binary/metadata-only).
                </div>
              )}
              <div style={filterGridStyle}>
                <label style={filterLabelStyle}>
                  Category
                  <select
                    value={categoryFilter}
                    onChange={(event) =>
                      setCategoryFilter(event.target.value as RunArtifactCategoryFilter)
                    }
                    style={selectStyle}
                  >
                    <option value="all">All categories</option>
                    {ARTIFACT_CATEGORIES.map((category) => (
                      <option key={category.key} value={category.key}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={filterLabelStyle}>
                  State
                  <select
                    value={stateFilter}
                    onChange={(event) =>
                      setStateFilter(event.target.value as RunArtifactStateFilter)
                    }
                    style={selectStyle}
                  >
                    <option value="all">All states</option>
                    <option value="exists">Exists</option>
                    <option value="missing">Missing</option>
                    <option value="warnings">Warnings</option>
                    <option value="previewable">Previewable</option>
                  </select>
                </label>
                <label style={filterLabelStyle}>
                  Kind
                  <select
                    value={kindFilter}
                    onChange={(event) => setKindFilter(event.target.value)}
                    style={selectStyle}
                  >
                    <option value="all">All kinds</option>
                    {kindOptions.map((kind) => (
                      <option key={kind} value={kind}>
                        {kind}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={filterLabelStyle}>
                  Source
                  <select
                    value={sourceFilter}
                    onChange={(event) => setSourceFilter(event.target.value)}
                    style={selectStyle}
                  >
                    <option value="all">All sources</option>
                    {sourceOptions.map((source) => (
                      <option key={source} value={source}>
                        {source}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div style={{ color: "#667085", fontSize: 11, fontWeight: 850, marginBottom: 8 }}>
                Showing {filteredArtifacts.length} of {artifacts.length} artifact(s).
              </div>

              {groupedArtifacts.length ? (
                <div style={{ display: "grid", gap: 12 }}>
                  {groupedArtifacts.map((group) => (
                    <div key={group.category} style={{ display: "grid", gap: 8 }}>
                      <div style={artifactGroupHeaderStyle}>
                        <span>{group.label}</span>
                        <b>{group.artifacts.length}</b>
                      </div>
                      {group.artifacts.map((artifact) => {
                        const artifactWarnings = getArtifactWarnings(artifact);
                        const previewable = isPreviewableArtifact(artifact);
                        const selected = artifact.artifact_id === selectedArtifactId;
                        return (
                          <div
                            key={artifact.artifact_id}
                            style={{
                              ...artifactCardStyle,
                              ...(selected
                                ? selectedArtifactCardStyle
                                : artifactAttentionStyle(artifact, runSummary)),
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                gap: 10,
                                alignItems: "center",
                                flexWrap: "wrap",
                              }}
                            >
                              <strong style={{ fontSize: 13, overflowWrap: "anywhere" }}>
                                {artifact.name}
                              </strong>
                              <ArtifactBadgeRow artifact={artifact} runSummary={runSummary} />
                            </div>
                            <div style={artifactMetaGridStyle}>
                              <span>size</span>
                              <b>{formatArtifactSize(artifact.size_bytes)}</b>
                              <span>exists</span>
                              <b>{artifact.exists ? "yes" : "no"}</b>
                              <span>modified</span>
                              <b>{formatDate(artifact.modified_at)}</b>
                              <span>source</span>
                              <b>{artifact.source || "-"}</b>
                            </div>
                            <div style={monoPathStyle}>
                              {artifact.relative_path || artifact.path}
                            </div>
                            <WarningList warnings={artifactWarnings} />
                            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                              <button
                                type="button"
                                onClick={() => onPreview(artifact)}
                                disabled={previewLoading}
                                style={smallButtonStyle}
                              >
                                {previewable ? "Preview" : "Details"}
                              </button>
                              <PathActions
                                label="Artifact"
                                path={artifactPath(artifact)}
                                onNotice={onNotice}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty">No artifacts match the current filters.</div>
              )}
            </>
          );
        })()
      )}

      {artifacts.length > 0 && (
        <details style={{ marginTop: 12 }}>
          <summary style={{ cursor: "pointer", fontWeight: 900 }}>Raw artifacts JSON</summary>
          <div style={{ marginTop: 8 }}>
            <pre
              style={{
                maxHeight: 260,
                overflow: "auto",
                padding: 10,
                border: "1px solid rgba(137, 150, 171, 0.24)",
                borderRadius: 6,
                background: "#0f172a",
                color: "#e5e7eb",
                fontFamily: '"Cascadia Mono", "Consolas", monospace',
                fontSize: 11,
                whiteSpace: "pre-wrap",
                overflowWrap: "anywhere",
              }}
            >
              {JSON.stringify({ artifacts, warnings }, null, 2)}
            </pre>
          </div>
        </details>
      )}

      <div
        style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(137, 150, 171, 0.24)" }}
      >
        {previewLoading ? (
          <div className="empty">Loading artifact preview...</div>
        ) : (
          <ArtifactPreviewPane preview={preview} onNotice={onNotice} />
        )}
      </div>
    </div>
  );
}
