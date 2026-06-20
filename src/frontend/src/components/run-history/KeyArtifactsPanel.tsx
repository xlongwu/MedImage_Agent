import { useMemo } from "react";
import type { RunArtifactRecord, RunSummaryPreview } from "../../types";
import { getKeyArtifactReason, getKeyArtifacts } from "../projectRunsPanelModel";
import {
  artifactAttentionStyle,
  artifactTone,
  ArtifactBadgeRow,
  headerStyle,
  keyArtifactButtonStyle,
  keyArtifactGridStyle,
  keyArtifactPathStyle,
  selectedArtifactCardStyle,
  statusPillStyle,
  subtitleStyle,
  summaryPanelStyle,
} from "./pathActions";

export function KeyArtifactsPanel({
  artifacts,
  runSummary,
  loading,
  previewLoading,
  selectedArtifactId,
  onPreview,
}: {
  artifacts: RunArtifactRecord[];
  runSummary: RunSummaryPreview | null;
  loading: boolean;
  previewLoading: boolean;
  selectedArtifactId: string | null;
  onPreview: (artifact: RunArtifactRecord) => void;
}) {
  const keyArtifacts = useMemo(
    () => getKeyArtifacts(artifacts, runSummary),
    [artifacts, runSummary],
  );

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>Key Artifacts</h4>
          <span style={subtitleStyle}>
            Summary, pipeline, reports, QC, failed logs, and tables.
          </span>
        </div>
        <span
          style={{ ...statusPillStyle, ...artifactTone(keyArtifacts.length ? "ok" : "neutral") }}
        >
          {keyArtifacts.length}
        </span>
      </div>

      {keyArtifacts.length ? (
        <div style={keyArtifactGridStyle}>
          {keyArtifacts.map((artifact) => {
            const selected = artifact.artifact_id === selectedArtifactId;
            const reason = getKeyArtifactReason(artifact, runSummary);
            return (
              <button
                key={artifact.artifact_id}
                type="button"
                onClick={() => onPreview(artifact)}
                disabled={previewLoading}
                style={{
                  ...keyArtifactButtonStyle,
                  ...(selected
                    ? selectedArtifactCardStyle
                    : artifactAttentionStyle(artifact, runSummary)),
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 8,
                    alignItems: "flex-start",
                  }}
                >
                  <strong style={{ fontSize: 12, overflowWrap: "anywhere" }}>
                    {artifact.name}
                  </strong>
                  <span
                    style={{
                      color: "#667085",
                      fontSize: 11,
                      fontWeight: 900,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {reason}
                  </span>
                </div>
                <ArtifactBadgeRow artifact={artifact} runSummary={runSummary} />
                <div style={keyArtifactPathStyle}>{artifact.relative_path || artifact.path}</div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="empty">
          {loading ? "Loading key artifacts..." : "No key artifacts were discovered for this run."}
        </div>
      )}
    </div>
  );
}
