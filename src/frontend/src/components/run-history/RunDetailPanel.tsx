import type {
  RunArtifactPreviewResponse,
  RunArtifactRecord,
  RunLinkRecord,
  RunSummaryPreview,
} from "../../types";
import { JsonBlock } from "../JsonBlock";
import { extractRunPaths } from "../projectRunsPanelModel";
import { KeyArtifactsPanel } from "./KeyArtifactsPanel";
import { RunArtifactsPanel } from "./RunArtifactsPanel";
import { RunQcErrorSummaryCard } from "./RunQcErrorSummaryCard";
import { RunSummaryPreviewCard } from "./RunSummaryPreviewCard";
import {
  detailGridStyle,
  formatDate,
  headerStyle,
  PathActions,
  statusPillStyle,
  statusTone,
  subtitleStyle,
  summaryPanelStyle,
  WarningList,
} from "./pathActions";

export function RunDetailPanel({
  detail,
  detailLoading,
  projectDir,
  summaryPreview,
  summaryWarnings,
  summaryError,
  artifacts,
  artifactWarnings,
  artifactError,
  artifactsLoading,
  artifactPreviewLoading,
  selectedArtifactId,
  artifactPreview,
  onPreview,
  onRefreshArtifacts,
  onNotice,
}: {
  detail: RunLinkRecord | null;
  detailLoading: boolean;
  projectDir?: string | null;
  summaryPreview: RunSummaryPreview | null;
  summaryWarnings: string[];
  summaryError: string;
  artifacts: RunArtifactRecord[];
  artifactWarnings: string[];
  artifactError: string;
  artifactsLoading: boolean;
  artifactPreviewLoading: boolean;
  selectedArtifactId: string | null;
  artifactPreview: RunArtifactPreviewResponse | null;
  onPreview: (artifact: RunArtifactRecord) => void;
  onRefreshArtifacts: (runId: string) => void;
  onNotice: (message: string) => void;
}) {
  return (
    <div style={{ minWidth: 0, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(247, 249, 253, 0.9)", padding: 12 }}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 15 }}>Run Detail</h3>
          <span style={subtitleStyle}>
            {detailLoading ? "Loading detail..." : detail ? detail.run_id : "Select a run"}
          </span>
        </div>
        {detail ? <span style={{ ...statusPillStyle, ...statusTone(detail.status) }}>{detail.status}</span> : null}
      </div>

      {detail ? (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={detailGridStyle}>
            <div><span>run_id</span><strong>{detail.run_id}</strong></div>
            <div><span>run_link_id</span><strong>{detail.run_link_id}</strong></div>
            <div><span>reviewed_plan_id</span><strong>{detail.reviewed_plan_id}</strong></div>
            <div><span>audit_id</span><strong>{detail.audit_id || "-"}</strong></div>
            <div><span>created_at</span><strong>{formatDate(detail.created_at)}</strong></div>
            <div><span>updated_at</span><strong>{formatDate(detail.updated_at)}</strong></div>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            {extractRunPaths(detail, projectDir).map((entry) => (
              <PathActions
                key={entry.label}
                label={entry.label}
                path={entry.path}
                onNotice={onNotice}
              />
            ))}
          </div>

          <WarningList warnings={detail.warnings} />

          <RunQcErrorSummaryCard
            run={detail}
            runSummary={summaryPreview}
            artifacts={artifacts}
            loading={artifactsLoading}
            previewLoading={artifactPreviewLoading}
            selectedArtifactId={selectedArtifactId}
            onPreview={onPreview}
          />

          <KeyArtifactsPanel
            artifacts={artifacts}
            runSummary={summaryPreview}
            loading={artifactsLoading}
            previewLoading={artifactPreviewLoading}
            selectedArtifactId={selectedArtifactId}
            onPreview={onPreview}
          />

          <div style={summaryPanelStyle}>
            <div style={{ ...headerStyle, marginBottom: 10 }}>
              <div>
                <h4 style={{ margin: 0, fontSize: 14 }}>Summary Preview</h4>
                <span style={subtitleStyle}>Pipeline summary JSON key fields.</span>
              </div>
            </div>
            <RunSummaryPreviewCard
              preview={summaryPreview}
              summaryPath={detail.summary_path}
              warnings={summaryWarnings}
              error={summaryError}
              loading={detailLoading}
            />
          </div>

          <RunArtifactsPanel
            artifacts={artifacts}
            runSummary={summaryPreview}
            selectedArtifactId={selectedArtifactId}
            preview={artifactPreview}
            loading={artifactsLoading}
            previewLoading={artifactPreviewLoading}
            error={artifactError}
            warnings={artifactWarnings}
            onRefresh={() => onRefreshArtifacts(detail.run_id)}
            onPreview={onPreview}
            onNotice={onNotice}
          />

          <details>
            <summary style={{ cursor: "pointer", fontWeight: 900 }}>Run link payload</summary>
            <div style={{ marginTop: 8 }}>
              <JsonBlock value={detail.payload} emptyText="No run payload recorded" />
            </div>
          </details>
        </div>
      ) : (
        <div className="empty">Select a run to inspect paths, warnings, and payload.</div>
      )}
    </div>
  );
}
