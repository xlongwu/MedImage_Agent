import { useState } from "react";

import { formatDate } from "../i18n/format";
import { useI18n } from "../i18n/useI18n";
import { getArtifacts, previewArtifact, refreshArtifacts } from "../lib/api/artifact";
import { getLatestNativeFullPreprocessingRun } from "../lib/api/preprocessing";
import type { EvidenceLevel } from "../lib/evidence";
import type { ArtifactSelection } from "../lib/workspaceSelection";
import type { NativeFullPreprocResponse, NativeFullStageApiResult } from "../types";
import { EvidenceBadge } from "./domain/EvidenceBadge";
import { Badge, Button, Card, EmptyState, Table, TableEmpty } from "./ui";
import { TextViewer } from "./TextViewer";
import styles from "./ArtifactBrowser.module.css";

type Props = {
  baseUrl: string;
  projectId?: string | null;
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
  artifact_id?: string | null;
  run_id_guess?: string | null;
  source?: string | null;
  stage_id?: string | null;
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

async function loadArtifactPayload(
  baseUrl: string,
  projectId: string | null | undefined,
  mode: "load" | "refresh",
): Promise<Record<string, unknown>> {
  if (projectId) {
    const projectPayload = await loadProjectNativeArtifactPayload(baseUrl, projectId);
    if (projectPayload && asArtifacts(projectPayload).length > 0) {
      return projectPayload;
    }
  }

  return mode === "refresh" ? refreshArtifacts(baseUrl) : getArtifacts(baseUrl);
}

async function loadProjectNativeArtifactPayload(baseUrl: string, projectId: string) {
  try {
    const run = await getLatestNativeFullPreprocessingRun(baseUrl, projectId);
    const artifacts = nativeRunArtifacts(run);
    if (!artifacts.length) return null;

    return {
      index: {
        artifacts_total: artifacts.length,
        generated_at: latestTimestamp(artifacts) ?? new Date().toISOString(),
        project_id: run.project_id,
        run_id: run.run_id,
        source: "native_preprocessing_latest",
        artifacts,
      },
    };
  } catch {
    return null;
  }
}

function nativeRunArtifacts(run: NativeFullPreprocResponse): ArtifactRecord[] {
  if (run.dry_run || !Array.isArray(run.stage_results)) return [];

  const artifacts = run.stage_results.flatMap((stage) =>
    stage.output_artifacts
      .map((artifact, index) => nativeArtifactToRecord(run, stage, artifact, index))
      .filter((artifact): artifact is ArtifactRecord => Boolean(artifact)),
  );

  const byPath = new Map<string, ArtifactRecord>();
  for (const artifact of artifacts) {
    if (!byPath.has(artifact.path)) {
      byPath.set(artifact.path, artifact);
    }
  }
  return Array.from(byPath.values());
}

function nativeArtifactToRecord(
  run: NativeFullPreprocResponse,
  stage: NativeFullStageApiResult,
  artifact: Record<string, unknown>,
  index: number,
): ArtifactRecord | null {
  const metadata = asRecord(artifact.metadata);
  const path = firstString(artifact.path, metadata.path, metadata.relative_path);
  if (!path) return null;

  const extension = inferExtension(path);
  const previewType =
    firstString(artifact.preview_type, metadata.preview_type) ?? previewTypeForExtension(extension);
  const artifactId = firstString(artifact.artifact_id, metadata.artifact_id);
  const category =
    firstString(artifact.artifact_type, metadata.artifact_type, metadata.kind, stage.stage_id) ??
    "artifact";

  return {
    artifact_id: artifactId,
    category,
    extension,
    modified_time:
      firstString(artifact.modified_time, metadata.modified_time, metadata.created_at) ?? "",
    name:
      firstString(
        artifact.name,
        metadata.name,
        metadata.filename,
        fileNameFromPath(path),
        artifactId,
      ) ?? `${stage.stage_id}-${index + 1}`,
    path,
    preview_supported:
      coerceBoolean(artifact.preview_supported) ?? isPreviewableExtension(extension),
    preview_type: previewType,
    run_id_guess: run.run_id,
    size_bytes: firstNumber(artifact.size_bytes, metadata.size_bytes) ?? 0,
    source: "native_preprocessing",
    stage_id: stage.stage_id,
  };
}

function latestTimestamp(artifacts: ArtifactRecord[]): string | null {
  const latest = artifacts
    .map((artifact) => Date.parse(artifact.modified_time))
    .filter(Number.isFinite)
    .sort((a, b) => b - a)[0];
  return Number.isFinite(latest) ? new Date(latest).toISOString() : null;
}

function formatBytes(value: number, unknownLabel = "Unknown") {
  if (!Number.isFinite(value)) return unknownLabel;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function ArtifactBrowser({ baseUrl, projectId, onSelectedArtifactChange }: Props) {
  const { locale, t } = useI18n();
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
      const result = await loadArtifactPayload(baseUrl, projectId, "load");
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
      const result = await loadArtifactPayload(baseUrl, projectId, "refresh");
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

  const allArtifacts = asArtifacts(payload);

  const categorySet = new Set(allArtifacts.map((artifact) => artifact.category).filter(Boolean));
  const categories = Array.from(categorySet).sort();

  const extensionSet = new Set(allArtifacts.map((artifact) => artifact.extension).filter(Boolean));
  const extensions = Array.from(extensionSet).sort();

  const query = search.trim().toLowerCase();
  const filteredArtifacts = allArtifacts.filter((artifact) => {
    const matchesCategory = categoryFilter === "all" || artifact.category === categoryFilter;
    const matchesExtension = extensionFilter === "all" || artifact.extension === extensionFilter;
    const matchesSearch =
      !query ||
      [
        artifact.name,
        artifact.path,
        artifact.category,
        artifact.extension,
        artifact.artifact_id ?? "",
        artifact.run_id_guess ?? "",
        artifact.stage_id ?? "",
      ].some((value) => value.toLowerCase().includes(query));
    return matchesCategory && matchesExtension && matchesSearch;
  });

  const indexMeta = payload?.index as ArtifactIndexMeta | undefined;
  const previewableTotal = allArtifacts.filter((artifact) => artifact.preview_supported).length;
  const generatedAt = indexMeta?.generated_at
    ? formatDate(locale, String(indexMeta.generated_at))
    : t("results.browser.notLoaded");
  const visibleArtifacts = filteredArtifacts.slice(0, 100);

  return (
    <section className={styles.browser} aria-label={t("results.browser.title")}>
      <Card className={styles.hero} tone="muted">
        <div className={styles.heroCopy}>
          <div>
            <h2>{t("results.browser.title")}</h2>
            <p>{t("results.browser.description")}</p>
          </div>
          {status === "ERROR" ? (
            <Badge tone="danger">{t("results.browser.requestFailed")}</Badge>
          ) : (
            <EvidenceBadge level={status === "LOADED" ? "metadata_only" : "backend_required"}>
              {status === "LOADING"
                ? t("results.browser.loadingMetadata")
                : status === "LOADED"
                  ? t("results.browser.metadataLoaded")
                  : t("results.browser.onDemand")}
            </EvidenceBadge>
          )}
        </div>
        <div className={styles.actionRow}>
          <Button onClick={handleLoad} disabled={status === "LOADING"} variant="primary">
            {status === "LOADING" ? t("results.browser.loading") : t("results.browser.load")}
          </Button>
          <Button onClick={handleRefresh} disabled={status === "LOADING"} variant="secondary">
            {status === "LOADING" ? t("results.browser.refreshing") : t("results.browser.refresh")}
          </Button>
        </div>
        {error ? (
          <div className={styles.errorLine} role="alert">
            <strong>{t("results.browser.error")}</strong>
            <span>{error}</span>
          </div>
        ) : null}
      </Card>

      <div className={styles.summaryGrid} aria-label={t("results.browser.summary")}>
        <SummaryTile
          label={t("results.browser.artifacts")}
          value={String(indexMeta?.artifacts_total ?? allArtifacts.length)}
        />
        <SummaryTile label={t("results.browser.previewable")} value={String(previewableTotal)} />
        <SummaryTile label={t("results.browser.types")} value={String(categories.length)} />
        <SummaryTile label={t("results.browser.generated")} value={generatedAt} />
      </div>

      <Card className={styles.browserCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>{t("results.browser.indexed")}</h3>
            <p>{t("results.browser.indexedDescription")}</p>
          </div>
          <Badge tone="neutral">
            {t("results.browser.showing", {
              visible: filteredArtifacts.length,
              total: allArtifacts.length,
            })}
          </Badge>
        </div>

        <div className={styles.filterBar} aria-label={t("results.browser.filters")}>
          <label>
            <span>{t("results.browser.type")}</span>
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="all">{t("results.browser.allTypes")}</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>{t("results.browser.extension")}</span>
            <select
              value={extensionFilter}
              onChange={(event) => setExtensionFilter(event.target.value)}
            >
              <option value="all">{t("results.browser.allExtensions")}</option>
              {extensions.map((extension) => (
                <option key={extension} value={extension}>
                  {extension}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.searchField}>
            <span>{t("results.browser.search")}</span>
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("results.browser.searchPlaceholder")}
            />
          </label>
        </div>

        <Table caption={t("results.browser.index")}>
          <thead>
            <tr>
              <th>{t("results.browser.artifact")}</th>
              <th>{t("results.browser.run")}</th>
              <th>{t("results.browser.subject")}</th>
              <th>{t("results.browser.type")}</th>
              <th>{t("results.browser.stage")}</th>
              <th>{t("results.browser.size")}</th>
              <th>{t("results.browser.evidence")}</th>
              <th>{t("results.browser.preview")}</th>
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
                  <td>{artifact.run_id_guess || t("results.browser.unassigned")}</td>
                  <td>{inferSubject(artifact.path, t("results.browser.unassigned"))}</td>
                  <td>
                    <Badge tone="info" size="sm">
                      {artifact.category || t("results.browser.uncategorized")}
                    </Badge>
                  </td>
                  <td>{inferStage(artifact, t("results.browser.unknown"))}</td>
                  <td>{formatBytes(artifact.size_bytes, t("results.browser.unknownSize"))}</td>
                  <td>
                    <EvidenceBadge level={artifactEvidenceLevel(artifact)} size="sm" />
                  </td>
                  <td>
                    {artifact.preview_supported ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handlePreview(artifact.path)}
                      >
                        {t("results.browser.preview")}
                      </Button>
                    ) : (
                      <Badge tone="neutral" size="sm">
                        {t("results.browser.unsupported")}
                      </Badge>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <TableEmpty colSpan={8}>
                {allArtifacts.length
                  ? t("results.browser.noMatches")
                  : t("results.browser.loadFirst")}
              </TableEmpty>
            )}
          </tbody>
        </Table>
        {filteredArtifacts.length > visibleArtifacts.length ? (
          <p className={styles.helperText}>
            {t("results.browser.hidden", {
              count: filteredArtifacts.length - visibleArtifacts.length,
            })}
          </p>
        ) : null}
      </Card>

      <div className={styles.lowerGrid}>
        <Card className={styles.provenanceCard} tone="muted">
          <div className={styles.cardHeader}>
            <div>
              <h3>{t("results.browser.provenance")}</h3>
              <p>{t("results.browser.provenanceDescription")}</p>
            </div>
          </div>
          <dl className={styles.provenanceList} aria-label={t("results.browser.provenanceFields")}>
            <InfoRow label={t("results.browser.run")} value={t("results.browser.runSource")} />
            <InfoRow
              label={t("results.browser.subject")}
              value={t("results.browser.subjectSource")}
            />
            <InfoRow label={t("results.browser.type")} value={t("results.browser.typeSource")} />
            <InfoRow
              label={t("results.browser.validation")}
              value={t("results.browser.validationSource")}
            />
          </dl>
        </Card>

        <Card className={styles.previewCard}>
          <div className={styles.cardHeader}>
            <div>
              <h3>{t("results.browser.preview")}</h3>
              <p>{t("results.browser.previewDescription")}</p>
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
                {t("results.browser.close")}
              </Button>
            ) : null}
          </div>
          {preview ? (
            <PreviewPanel payload={preview} />
          ) : (
            <EmptyState
              title={t("results.browser.noSelection")}
              description={t("results.browser.noSelectionDescription")}
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
  const { t } = useI18n();

  if (payload.error) {
    return (
      <div className={styles.errorLine} role="alert">
        <strong>{t("results.browser.previewError")}</strong>
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
        <div className={styles.previewMeta} aria-label={t("results.browser.previewMetadata")}>
          <InfoRow label={t("results.browser.artifact")} value={artifact.name} />
          <InfoRow label={t("results.browser.path")} value={artifact.path} />
          <InfoRow label={t("results.browser.previewType")} value={previewType} />
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

function inferSubject(path: string, fallback = "Unassigned"): string {
  const match = path.match(/(?:^|[/\\])(sub-[A-Za-z0-9_-]+)/);
  return match?.[1] ?? fallback;
}

function inferStage(artifact: ArtifactRecord, fallback = "unknown"): string {
  if (artifact.stage_id) return artifact.stage_id;

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
  return (
    knownStages.find((stage) => normalizedPath.includes(stage)) ?? artifact.category ?? fallback
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const parsed = typeof value === "number" ? value : Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function coerceBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function fileNameFromPath(path: string): string {
  const parts = path.split(/[/\\]/).filter(Boolean);
  return parts.length ? parts[parts.length - 1] : path;
}

function inferExtension(path: string): string {
  const name = fileNameFromPath(path);
  const lowerName = name.toLowerCase();
  if (lowerName.endsWith(".nii.gz")) return ".nii.gz";
  const dotIndex = name.lastIndexOf(".");
  return dotIndex >= 0 ? name.slice(dotIndex) : "";
}

function previewTypeForExtension(extension: string): string {
  const normalized = extension.toLowerCase();
  if (normalized === ".json") return "json";
  if (normalized === ".tsv" || normalized === ".csv") return "table";
  if (normalized === ".md" || normalized === ".markdown") return "markdown";
  if (normalized === ".yaml" || normalized === ".yml") return "yaml";
  if (normalized === ".txt" || normalized === ".log") return "text";
  return "metadata_only";
}

function isPreviewableExtension(extension: string): boolean {
  return [".json", ".md", ".markdown", ".txt", ".tsv", ".csv", ".yaml", ".yml", ".log"].includes(
    extension.toLowerCase(),
  );
}
