import { useMemo } from "react";
import type { RunArtifactRecord, RunLinkRecord, RunSummaryPreview } from "../../types";
import {
  buildArtifactProvenanceRows,
  extractFailedNodeHighlights,
  extractQcHighlights,
  summarizeRunHealth,
} from "../projectRunsPanelModel";
import {
  artifactChipStyle,
  artifactMiniTextStyle,
  artifactTableStyle,
  artifactTone,
  headerStyle,
  jsonMessageStyle,
  metricChipGridStyle,
  metricChipStyle,
  selectedArtifactCardStyle,
  smallButtonStyle,
  statusPillStyle,
  statusTone,
  subtitleStyle,
  SummaryMetric,
  summaryExcerptStyle,
  summaryMetricsStyle,
  summaryPanelStyle,
  summaryRowStyle,
  summarySectionLabelStyle,
  tableCellStyle,
  tableHeaderCellStyle,
  tableScrollStyle,
  WarningList,
} from "./pathActions";

export function RunQcErrorSummaryCard({
  run,
  runSummary,
  artifacts,
  loading,
  previewLoading,
  selectedArtifactId,
  onPreview,
}: {
  run: RunLinkRecord;
  runSummary: RunSummaryPreview | null;
  artifacts: RunArtifactRecord[];
  loading: boolean;
  previewLoading: boolean;
  selectedArtifactId: string | null;
  onPreview: (artifact: RunArtifactRecord) => void;
}) {
  const health = useMemo(
    () => summarizeRunHealth(run, runSummary, artifacts),
    [artifacts, run, runSummary],
  );
  const qcHighlights = useMemo(() => extractQcHighlights(artifacts), [artifacts]);
  const failedNodes = useMemo(
    () => extractFailedNodeHighlights(runSummary, artifacts),
    [artifacts, runSummary],
  );
  const provenanceRows = useMemo(
    () => buildArtifactProvenanceRows(artifacts).slice(0, 8),
    [artifacts],
  );

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>QC / Error Summary</h4>
          <span style={subtitleStyle}>
            Run health, QC highlights, failed logs, and artifact provenance.
          </span>
        </div>
        <span style={{ ...statusPillStyle, ...statusTone(health.status) }}>{health.status}</span>
      </div>

      <div style={summaryMetricsStyle}>
        <SummaryMetric label="nodes total" value={health.nodesTotal} />
        <SummaryMetric label="succeeded" value={health.nodesSucceeded} />
        <SummaryMetric label="failed" value={health.nodesFailed} />
        <SummaryMetric label="skipped" value={health.nodesSkipped} />
        <SummaryMetric label="warnings" value={health.warningsCount} />
        <SummaryMetric label="errors" value={health.errorsCount} />
        <SummaryMetric label="missing" value={health.missingArtifactCount} />
        <SummaryMetric label="failed logs" value={health.failedLogCount} />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <span
          style={{
            ...artifactChipStyle,
            ...artifactTone(
              health.artifactPresenceState === "missing"
                ? "missing"
                : health.artifactPresenceState === "present"
                  ? "ok"
                  : "neutral",
            ),
          }}
        >
          {health.artifactPresenceLabel}
        </span>
        <span
          style={{
            ...artifactChipStyle,
            ...artifactTone(health.hasFailedNodeLogs ? "error" : "ok"),
          }}
        >
          {health.hasFailedNodeLogs ? "failed-node logs" : "no failed-node logs"}
        </span>
        {loading ? (
          <span style={{ ...artifactChipStyle, ...artifactTone("neutral") }}>
            loading artifacts
          </span>
        ) : null}
      </div>

      {failedNodes.length ? (
        <div style={{ display: "grid", gap: 7 }}>
          <strong style={summarySectionLabelStyle}>Failed nodes</strong>
          {failedNodes.map((node) => {
            const selected = node.artifactId === selectedArtifactId;
            return (
              <div
                key={`${node.nodeId}-${node.artifactId || "summary"}`}
                style={{
                  ...summaryRowStyle,
                  ...(selected ? selectedArtifactCardStyle : {}),
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 12 }}>{node.nodeName || node.nodeId}</strong>
                    <span style={{ ...artifactChipStyle, ...artifactTone("error") }}>
                      {node.status}
                    </span>
                    {node.artifactName ? (
                      <span style={artifactMiniTextStyle}>{node.artifactName}</span>
                    ) : null}
                  </div>
                  {node.errorExcerpt ? (
                    <pre style={summaryExcerptStyle}>{node.errorExcerpt}</pre>
                  ) : (
                    <div style={artifactMiniTextStyle}>No bounded error excerpt recorded.</div>
                  )}
                </div>
                {node.artifact ? (
                  <button
                    type="button"
                    onClick={() => onPreview(node.artifact!)}
                    disabled={previewLoading}
                    style={smallButtonStyle}
                  >
                    Preview log
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      {qcHighlights.length ? (
        <div style={{ display: "grid", gap: 7 }}>
          <strong style={summarySectionLabelStyle}>QC highlights</strong>
          {qcHighlights.map((highlight) => {
            const selected = highlight.artifactId === selectedArtifactId;
            const tone = highlight.failed ? "error" : highlight.passed ? "ok" : "neutral";
            return (
              <div
                key={highlight.artifactId}
                style={{
                  ...summaryRowStyle,
                  ...(selected ? selectedArtifactCardStyle : {}),
                }}
              >
                <div style={{ display: "grid", gap: 6, minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 12, overflowWrap: "anywhere" }}>
                      {highlight.artifactName}
                    </strong>
                    <span style={{ ...artifactChipStyle, ...artifactTone(tone) }}>
                      {highlight.status ?? highlight.category}
                    </span>
                    {highlight.subjectId ? (
                      <span style={artifactMiniTextStyle}>subject {highlight.subjectId}</span>
                    ) : null}
                    {highlight.nodeId ? (
                      <span style={artifactMiniTextStyle}>node {highlight.nodeId}</span>
                    ) : null}
                  </div>
                  {highlight.metrics.length ? (
                    <div style={metricChipGridStyle}>
                      {highlight.metrics.map((metric) => (
                        <span
                          key={`${highlight.artifactId}-${metric.label}`}
                          style={metricChipStyle}
                        >
                          {metric.label}: <b>{metric.value}</b>
                        </span>
                      ))}
                    </div>
                  ) : highlight.topLevelKeys.length ? (
                    <div style={artifactMiniTextStyle}>
                      keys: {highlight.topLevelKeys.join(", ")}
                    </div>
                  ) : null}
                  <WarningList warnings={highlight.warnings.slice(0, 3)} />
                  {highlight.errorMessage ? (
                    <div style={{ ...jsonMessageStyle, color: "#b53b3b" }}>
                      {highlight.errorMessage}
                    </div>
                  ) : null}
                  <div style={artifactMiniTextStyle}>{highlight.reference}</div>
                </div>
                <button
                  type="button"
                  onClick={() => onPreview(highlight.artifact)}
                  disabled={previewLoading}
                  style={smallButtonStyle}
                >
                  Preview
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty" style={{ padding: 8 }}>
          {loading
            ? "Loading QC artifacts..."
            : "No QC JSON or QC report artifacts were discovered."}
        </div>
      )}

      {provenanceRows.length ? (
        <details>
          <summary style={{ cursor: "pointer", fontWeight: 900 }}>Artifact provenance</summary>
          <div style={{ ...tableScrollStyle, marginTop: 8, maxHeight: 220 }}>
            <table style={artifactTableStyle}>
              <thead>
                <tr>
                  <th style={tableHeaderCellStyle}>source</th>
                  <th style={tableHeaderCellStyle}>node</th>
                  <th style={tableHeaderCellStyle}>kind</th>
                  <th style={tableHeaderCellStyle}>artifact</th>
                  <th style={tableHeaderCellStyle}>state</th>
                </tr>
              </thead>
              <tbody>
                {provenanceRows.map((row) => (
                  <tr key={row.artifactId}>
                    <td style={tableCellStyle}>{row.source}</td>
                    <td style={tableCellStyle}>{row.nodeId || "-"}</td>
                    <td style={tableCellStyle}>{row.kind}</td>
                    <td style={tableCellStyle}>{row.artifactName}</td>
                    <td style={tableCellStyle}>{row.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
    </div>
  );
}
