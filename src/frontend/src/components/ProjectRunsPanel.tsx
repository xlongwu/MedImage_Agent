import { useEffect, useMemo, useRef, useState } from "react";
import {
  getProjectRun,
  getProjectRunArtifact,
  listProjectRunArtifacts,
  listProjectRuns,
} from "../lib/api/legacy";
import type {
  RunArtifactPreviewResponse,
  RunArtifactRecord,
  RunLinkRecord,
  RunSummaryPreview,
} from "../types";
import { mergeSummaryWarnings, normalizeRunSummaryPreview } from "./projectRunsPanelModel";
import { RunDetailPanel, RunListPanel } from "./run-history";
import { headerStyle, panelStyle, subtitleStyle, titleStyle } from "./run-history/pathActions";

type Props = {
  baseUrl: string;
  projectId: string | null;
  projectDir?: string | null;
};

export default function ProjectRunsPanel({ baseUrl, projectId, projectDir }: Props) {
  const [runs, setRuns] = useState<RunLinkRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunLinkRecord | null>(null);
  const [summaryPreview, setSummaryPreview] = useState<RunSummaryPreview | null>(null);
  const [summaryWarnings, setSummaryWarnings] = useState<string[]>([]);
  const [summaryError, setSummaryError] = useState("");
  const [artifacts, setArtifacts] = useState<RunArtifactRecord[]>([]);
  const [artifactWarnings, setArtifactWarnings] = useState<string[]>([]);
  const [artifactError, setArtifactError] = useState("");
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [artifactPreviewLoading, setArtifactPreviewLoading] = useState(false);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [artifactPreview, setArtifactPreview] = useState<RunArtifactPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const activeProjectIdRef = useRef<string | null>(projectId);
  const activeRunIdRef = useRef<string | null>(null);
  const activeArtifactIdRef = useRef<string | null>(null);
  const runsRequestRef = useRef(0);
  const detailRequestRef = useRef(0);
  const artifactsRequestRef = useRef(0);
  const previewRequestRef = useRef(0);

  const selectedFromList = useMemo(
    () => runs.find((run) => run.run_id === selectedRunId) ?? null,
    [runs, selectedRunId],
  );
  const detail = selectedRun ?? selectedFromList;

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    activeRunIdRef.current = null;
    activeArtifactIdRef.current = null;
    detailRequestRef.current += 1;
    setRuns([]);
    setSelectedRunId(null);
    setSelectedRun(null);
    setSummaryPreview(null);
    setSummaryWarnings([]);
    setSummaryError("");
    resetArtifacts();
    setLoading(false);
    setDetailLoading(false);
    setError("");
    setNotice("");
    if (projectId) {
      void refreshRuns(projectId);
    }
  }, [projectId]);

  async function refreshRuns(nextProjectId = projectId) {
    if (!nextProjectId) {
      setRuns([]);
      return;
    }
    const requestId = runsRequestRef.current + 1;
    runsRequestRef.current = requestId;
    setLoading(true);
    setError("");
    try {
      const payload = await listProjectRuns(baseUrl, nextProjectId);
      if (requestId !== runsRequestRef.current || activeProjectIdRef.current !== nextProjectId) {
        return;
      }
      const nextRuns = payload.runs ?? [];
      setRuns(nextRuns);
      if (selectedRunId && !nextRuns.some((run) => run.run_id === selectedRunId)) {
        activeRunIdRef.current = null;
        setSelectedRunId(null);
        setSelectedRun(null);
        setSummaryPreview(null);
        setSummaryWarnings([]);
        setSummaryError("");
        resetArtifacts();
      }
      setNotice(nextRuns.length ? `Loaded ${nextRuns.length} project run(s).` : "");
    } catch (err) {
      if (requestId !== runsRequestRef.current || activeProjectIdRef.current !== nextProjectId) {
        return;
      }
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (requestId === runsRequestRef.current && activeProjectIdRef.current === nextProjectId) {
        setLoading(false);
      }
    }
  }

  async function loadRunDetail(runId: string) {
    if (!projectId) return;
    const nextProjectId = projectId;
    const requestId = detailRequestRef.current + 1;
    detailRequestRef.current = requestId;
    activeRunIdRef.current = runId;
    activeArtifactIdRef.current = null;
    setSelectedRunId(runId);
    setSelectedRun(null);
    setSummaryPreview(null);
    setSummaryWarnings([]);
    setSummaryError("");
    resetArtifacts();
    setDetailLoading(true);
    setError("");
    try {
      const payload = await getProjectRun(baseUrl, nextProjectId, runId);
      if (
        requestId !== detailRequestRef.current ||
        activeProjectIdRef.current !== nextProjectId ||
        activeRunIdRef.current !== runId
      ) {
        return;
      }
      setSelectedRun(payload.run_link);
      setSummaryPreview(normalizeRunSummaryPreview(payload.summary_preview, payload.run_link));
      setSummaryWarnings(mergeSummaryWarnings(payload, payload.summary_preview));
      setSummaryError(payload.summary_preview_error || "");
      setNotice(`Loaded run detail for ${runId}.`);
      void loadArtifacts(runId);
    } catch (err) {
      if (
        requestId !== detailRequestRef.current ||
        activeProjectIdRef.current !== nextProjectId ||
        activeRunIdRef.current !== runId
      ) {
        return;
      }
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (
        requestId === detailRequestRef.current &&
        activeProjectIdRef.current === nextProjectId &&
        activeRunIdRef.current === runId
      ) {
        setDetailLoading(false);
      }
    }
  }

  function resetArtifacts() {
    artifactsRequestRef.current += 1;
    previewRequestRef.current += 1;
    activeArtifactIdRef.current = null;
    setArtifacts([]);
    setArtifactWarnings([]);
    setArtifactError("");
    setArtifactsLoading(false);
    setArtifactPreviewLoading(false);
    setSelectedArtifactId(null);
    setArtifactPreview(null);
  }

  async function loadArtifacts(runId = selectedRunId) {
    if (!projectId || !runId) return;
    const nextProjectId = projectId;
    const requestId = artifactsRequestRef.current + 1;
    artifactsRequestRef.current = requestId;
    setArtifactsLoading(true);
    setArtifactError("");
    setArtifactPreview(null);
    setSelectedArtifactId(null);
    activeArtifactIdRef.current = null;
    try {
      const payload = await listProjectRunArtifacts(baseUrl, nextProjectId, runId);
      if (
        requestId !== artifactsRequestRef.current ||
        activeProjectIdRef.current !== nextProjectId ||
        activeRunIdRef.current !== runId
      ) {
        return;
      }
      setArtifacts(payload.artifacts ?? []);
      setArtifactWarnings(payload.warnings ?? []);
    } catch (err) {
      if (
        requestId !== artifactsRequestRef.current ||
        activeProjectIdRef.current !== nextProjectId ||
        activeRunIdRef.current !== runId
      ) {
        return;
      }
      setArtifactError(err instanceof Error ? err.message : String(err));
    } finally {
      if (
        requestId === artifactsRequestRef.current &&
        activeProjectIdRef.current === nextProjectId &&
        activeRunIdRef.current === runId
      ) {
        setArtifactsLoading(false);
      }
    }
  }

  async function loadArtifactPreview(artifact: RunArtifactRecord) {
    const runId = activeRunIdRef.current ?? selectedRunId;
    if (!projectId || !runId) return;
    const nextProjectId = projectId;
    const requestId = previewRequestRef.current + 1;
    previewRequestRef.current = requestId;
    activeArtifactIdRef.current = artifact.artifact_id;
    setSelectedArtifactId(artifact.artifact_id);
    setArtifactPreview(null);
    setArtifactPreviewLoading(true);
    setArtifactError("");
    try {
      const payload = await getProjectRunArtifact(
        baseUrl,
        nextProjectId,
        runId,
        artifact.artifact_id,
      );
      if (
        requestId !== previewRequestRef.current ||
        activeProjectIdRef.current !== nextProjectId ||
        activeRunIdRef.current !== runId ||
        activeArtifactIdRef.current !== artifact.artifact_id
      ) {
        return;
      }
      setArtifactPreview(payload);
    } catch (err) {
      if (
        requestId !== previewRequestRef.current ||
        activeProjectIdRef.current !== nextProjectId ||
        activeRunIdRef.current !== runId ||
        activeArtifactIdRef.current !== artifact.artifact_id
      ) {
        return;
      }
      setArtifactError(err instanceof Error ? err.message : String(err));
    } finally {
      if (
        requestId === previewRequestRef.current &&
        activeProjectIdRef.current === nextProjectId &&
        activeRunIdRef.current === runId &&
        activeArtifactIdRef.current === artifact.artifact_id
      ) {
        setArtifactPreviewLoading(false);
      }
    }
  }

  if (!projectId) {
    return (
      <section style={panelStyle}>
        <div style={headerStyle}>
          <div>
            <h2 style={titleStyle}>Project Runs</h2>
            <span style={subtitleStyle}>Select a project to view reviewed execution history.</span>
          </div>
        </div>
        <div className="empty">No project selected.</div>
      </section>
    );
  }

  return (
    <section style={panelStyle}>
      <div style={headerStyle}>
        <div>
          <h2 style={titleStyle}>Project Runs</h2>
          <span style={subtitleStyle}>Reviewed execute history and artifact entry points.</span>
        </div>
        <button
          type="button"
          onClick={() => void refreshRuns()}
          disabled={loading}
          style={{ minHeight: 34, padding: "6px 12px", fontWeight: 850 }}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}
      {notice ? (
        <div className="empty" style={{ marginBottom: 12, padding: 10 }}>
          {notice}
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 14,
          alignItems: "start",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <RunListPanel
            runs={runs}
            loading={loading}
            error={error || undefined}
            selectedRunId={selectedRunId}
            onSelect={(runId) => void loadRunDetail(runId)}
          />
        </div>

        <RunDetailPanel
          detail={detail}
          detailLoading={detailLoading}
          baseUrl={baseUrl}
          projectId={projectId}
          projectDir={projectDir}
          summaryPreview={summaryPreview}
          summaryWarnings={summaryWarnings}
          summaryError={summaryError}
          artifacts={artifacts}
          artifactWarnings={artifactWarnings}
          artifactError={artifactError}
          artifactsLoading={artifactsLoading}
          artifactPreviewLoading={artifactPreviewLoading}
          selectedArtifactId={selectedArtifactId}
          artifactPreview={artifactPreview}
          onPreview={(artifact) => void loadArtifactPreview(artifact)}
          onRefreshArtifacts={(runId) => void loadArtifacts(runId)}
          onNotice={setNotice}
        />
      </div>
    </section>
  );
}
