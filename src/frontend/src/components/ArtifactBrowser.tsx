import { useMemo, useState } from "react";

import { getArtifacts, previewArtifact, refreshArtifacts } from "../lib/api/legacy";
import type { EvidenceLevel } from "../lib/evidence";
import type { ArtifactSelection } from "../lib/workspaceSelection";
import { EvidenceBadge } from "./domain/EvidenceBadge";
import { Badge, Button, Card, EmptyState, Table, TableEmpty } from "./ui";
import { TextViewer } from "./TextViewer";
import styles from "./ArtifactBrowser.module.css";

type Props = {
  baseUrl: string;
  onSelectedArtifactChange?: (artifact: ArtifactSelection | null) => void;
};

type ArtifactRecord = {
  path: string;
  name: string;
  extension: string;
  size_bytes: number;
  modified_time: string;
  category: string;
  preview_supported: boolean;
  preview_type: string;
  run_id_guess?: string | null;
};

type ArtifactIndexMeta = {
  artifacts_total?: number | string;
  generated_at?: string;
};

type PreviewPayload = Record<string, unknown> & {
  artifact?: ArtifactRecord;
  error?: unknown;
  preview?: {
    parsed?: unknown;
    preview_type?: unknown;
    text?: unknown;
    truncated?: unknown;
  };
};

function asArtifacts(payload: Record<string, unknown> | null): ArtifactRecord[] {
  const index = payload?.index as Record<string, unknown> | undefined;
  const artifacts = index?.artifacts;

  if (!Array.isArray(artifacts)) return [];
  return artifacts as ArtifactRecord[];
}

function formatBytes(value: number) {
  if (!Number.isFinite(value)) return "Unknown";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function ArtifactBrowser({ baseUrl, onSelectedArtifactChange }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [preview, setPreview] = useState<PreviewPayload | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [extensionFilter, setExtensionFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoad() {
    setStatus("LOADING");
    setError("");
    setPreview(null);
    onSelectedArtifactChange?.(null);

    try {
      const result = await getArtifacts(baseUrl);
      setPayload(result);
      setStatus("LOADED");
    } catch (e) {
      setError(String(e));
      setStatus("ERROR");
    }
  }

  async function handleRefresh() {
    setStatus("LOADING");
    setError("");
    setPreview(null);
    onSelectedArtifactChange?.(null);

    try {
      const result = await refreshArtifacts(baseUrl);
      setPayload(result);
      setStatus("LOADED");
    } catch (e) {
      setError(String(e));
      setStatus("ERROR");
    }
  }

  async function handlePreview(path: string) {
    setPreview(null);
    onSelectedArtifactChange?.(null);
    try {
      const result = await previewArtifact(baseUrl, path);
      const payload = result as PreviewPayload;
      setPreview(payload);
      const artifact = payload.artifact ?? allArtifacts.find((item) => item.path === path);
      onSelectedArtifactChange?.(artifact ? artifactSelection(artifact) : null);
    } catch (e) {
      setPreview({ error: String(e) });
      onSelectedArtifactChange?.(null);
    }
  }

  const allArtifacts = useMemo(() => asArtifacts(payload), [payload]);

  const categories = useMemo(() => {
    const set = new Set(allArtifacts.map((a) => a.category).filter(Boolean));
    return Array.from(set).sort();
  }, [allArtifacts]);

  const extensions = useMemo(() => {
    const set = new Set(allArtifacts.map((a) => a.extension).filter(Boolean));
    return Array.from(set).sort();
  }, [allArtifacts]);

  const filteredArtifacts = useMemo(() => {
    return allArtifacts.filter((a) => {
      const query = search.trim().toLowerCase();
      const matchesCategory = categoryFilter === "all" || a.category === categoryFilter;
      const matchesExtension = extensionFilter === "all" || a.extension === extensionFilter;
      const matchesSearch =
        !query ||
        [a.name, a.path, a.category, a.extension, a.run_id_guess ?? ""].some((value) =>
          value.toLowerCase().includes(query),
        );
      return matchesCategory && matchesExtension && matchesSearch;
    });
  }, [allArtifacts, categoryFilter, extensionFilter, search]);

  const indexMeta = payload?.index as ArtifactIndexMeta | undefined;
  const previewableTotal = allArtifacts.filter((artifact) => artifact.preview_supported).length;
  const generatedAt = indexMeta?.generated_at
    ? new Date(String(indexMeta.generated_at)).toLocaleString()
    : "Not loaded";
  const visibleArtifacts = filteredArtifacts.slice(0, 100);

  return (
    <section className={styles.browser} aria-label="Artifact browser">
      <Card className={styles.hero} tone="muted">
        <div className={styles.heroCopy}>
          <div>
            <h2>Artifact Browser</h2>
            <p>
              Browse backend-indexed artifacts by run, subject, type, and stage. Preview and
              provenance stay tied to persisted artifact records.
            </p>
          </div>
          {status === "ERROR" ? (
            <Badge tone="danger">Index request failed</Badge>
          ) : (
            <EvidenceBadge level={status === "LOADED" ? "metadata_only" : "backend_required"}>
              {status === "LOADING"
                ? "Loading metadata"
                : status === "LOADED"
                  ? "Index metadata loaded"
                  : "On demand"}
            </EvidenceBadge>
          )}
        </div>
        <div className={styles.actionRow}>
          <Button onClick={handleLoad} disabled={status === "LOADING"} variant="primary">
            {status === "LOADING" ? "Loading..." : "Load Artifacts"}
          </Button>
          <Button onClick={handleRefresh} disabled={status === "LOADING"} variant="secondary">
            {status === "LOADING" ? "Refreshing..." : "Refresh Index"}
          </Button>
        </div>
        {error ? (
          <div className={styles.errorLine} role="alert">
            <strong>Error</strong>
            <span>{error}</span>
          </div>
        ) : null}
      </Card>

      <div className={styles.summaryGrid} aria-label="Artifact index summary">
        <SummaryTile label="Artifacts" value={String(indexMeta?.artifacts_total ?? allArtifacts.length)} />
        <SummaryTile label="Previewable" value={String(previewableTotal)} />
        <SummaryTile label="Types" value={String(categories.length)} />
        <SummaryTile label="Generated" value={generatedAt} />
      </div>

      <Card className={styles.browserCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>Indexed artifacts</h3>
            <p>
              The table stays empty until the backend artifact index is loaded. Filters never imply
              validation or computation success.
            </p>
          </div>
          <Badge tone="neutral">
            Showing {filteredArtifacts.length} of {allArtifacts.length}
          </Badge>
        </div>

        <div className={styles.filterBar} aria-label="Artifact filters">
          <label>
            <span>Type</span>
            <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option value="all">All types</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Extension</span>
            <select
              value={extensionFilter}
              onChange={(event) => setExtensionFilter(event.target.value)}
            >
              <option value="all">All extensions</option>
              {extensions.map((extension) => (
                <option key={extension} value={extension}>
                  {extension}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.searchField}>
            <span>Search</span>
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Name, path, run, type"
            />
          </label>
        </div>

        <Table caption="Artifact index">
          <thead>
            <tr>
              <th>Artifact</th>
              <th>Run</th>
              <th>Subject</th>
              <th>Type</th>
              <th>Stage</th>
              <th>Size</th>
              <th>Evidence</th>
              <th>Preview</th>
            </tr>
          </thead>
          <tbody>
            {visibleArtifacts.length ? (
              visibleArtifacts.map((artifact) => (
                <tr key={artifact.path}>
                  <td>
                    <strong className={styles.artifactName}>{artifact.name}</strong>
                    <small className={styles.artifactPath}>{artifact.path}</small>
                  </td>
                  <td>{artifact.run_id_guess || "Unassigned"}</td>
                  <td>{inferSubject(artifact.path)}</td>
                  <td>
                    <Badge tone="info" size="sm">
                      {artifact.category || "uncategorized"}
                    </Badge>
                  </td>
                  <td>{inferStage(artifact)}</td>
                  <td>{formatBytes(artifact.size_bytes)}</td>
                  <td>
                    <EvidenceBadge level={artifactEvidenceLevel(artifact)} size="sm" />
                  </td>
                  <td>
                    {artifact.preview_supported ? (
                      <Button size="sm" variant="secondary" onClick={() => handlePreview(artifact.path)}>
                        Preview
                      </Button>
                    ) : (
                      <Badge tone="neutral" size="sm">
                        Unsupported
                      </Badge>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <TableEmpty colSpan={8}>
                {allArtifacts.length
                  ? "No artifacts match the current filters."
                  : "Load the backend artifact index before browsing artifacts."}
              </TableEmpty>
            )}
          </tbody>
        </Table>
        {filteredArtifacts.length > visibleArtifacts.length ? (
          <p className={styles.helperText}>
            {filteredArtifacts.length - visibleArtifacts.length} additional artifacts are hidden.
            Narrow the filters to inspect a smaller set.
          </p>
        ) : null}
      </Card>

      <div className={styles.lowerGrid}>
        <Card className={styles.provenanceCard} tone="muted">
          <div className={styles.cardHeader}>
            <div>
              <h3>Provenance</h3>
              <p>Run, subject, type, and stage are displayed only from indexed artifact metadata.</p>
            </div>
          </div>
          <dl className={styles.provenanceList} aria-label="Artifact provenance fields">
            <InfoRow label="Run" value="run_id_guess or backend path metadata" />
            <InfoRow label="Subject" value="subject token parsed from persisted path" />
            <InfoRow label="Type" value="artifact category and extension" />
            <InfoRow label="Validation" value="handled by report validator, not this browser" />
          </dl>
        </Card>

        <Card className={styles.previewCard}>
          <div className={styles.cardHeader}>
            <div>
              <h3>Preview</h3>
              <p>Only backend-supported preview types open here.</p>
            </div>
            {preview ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setPreview(null);
                  onSelectedArtifactChange?.(null);
                }}
              >
                Close
              </Button>
            ) : null}
          </div>
          {preview ? (
            <PreviewPanel payload={preview} />
          ) : (
            <EmptyState
              title="No artifact selected"
              description="Choose Preview for a supported artifact to load text, JSON, metadata, or table-compatible preview output."
            />
          )}
        </Card>
      </div>
    </section>
  );
}

function artifactSelection(artifact: ArtifactRecord): ArtifactSelection {
  return {
    evidenceLevel: artifactEvidenceLevel(artifact),
    name: artifact.name,
    path: artifact.path,
    previewType: artifact.preview_type || "unsupported",
    runId: artifact.run_id_guess ?? null,
    stage: inferStage(artifact),
    subject: inferSubject(artifact.path),
  };
}

function artifactEvidenceLevel(artifact: ArtifactRecord): EvidenceLevel {
  return artifact.preview_supported ? "preview_only" : "created";
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className={styles.summaryTile}>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </Card>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function PreviewPanel({ payload }: { payload: PreviewPayload }) {
  if (payload.error) {
    return (
      <div className={styles.errorLine} role="alert">
        <strong>Preview error</strong>
        <span>{String(payload.error)}</span>
      </div>
    );
  }

  const artifact = payload.artifact;
  const preview = payload.preview;
  const previewType = String(preview?.preview_type ?? artifact?.preview_type ?? "text");

  return (
    <div className={styles.previewPanel}>
      {artifact ? (
        <div className={styles.previewMeta} aria-label="Preview artifact metadata">
          <InfoRow label="Artifact" value={artifact.name} />
          <InfoRow label="Path" value={artifact.path} />
          <InfoRow label="Preview type" value={previewType} />
        </div>
      ) : null}
      <TextViewer
        text={String(preview?.text ?? "")}
        parsed={preview?.parsed}
        truncated={Boolean(preview?.truncated)}
        previewType={previewType}
      />
    </div>
  );
}

function inferSubject(path: string): string {
  const match = path.match(/(?:^|[/\\])(sub-[A-Za-z0-9_-]+)/);
  return match?.[1] ?? "Unassigned";
}

function inferStage(artifact: ArtifactRecord): string {
  const normalizedPath = artifact.path.toLowerCase();
  const knownStages = [
    "conversion",
    "preprocessing",
    "motion",
    "normalization",
    "qc",
    "report",
    "results",
  ];
  return knownStages.find((stage) => normalizedPath.includes(stage)) ?? artifact.category ?? "unknown";
}
