import type {
  CsvPreviewTable,
  JsonFieldSummary,
  JsonMessageSummary,
  JsonPreviewSummary,
  RunArtifactPreviewResponse,
  RunArtifactRecord,
  RunLinkRecord,
  RunSummaryPreview,
} from "../types";

export type RunPathEntry = {
  label: "Pipeline YAML" | "Summary JSON" | "Project directory";
  path: string | null;
};

export type RunStatusToneKey = "success" | "danger" | "active" | "neutral";
export type RunArtifactCategoryKey =
  | "summary"
  | "pipeline"
  | "reports"
  | "qc"
  | "logs"
  | "tables"
  | "json"
  | "images"
  | "other_binary";
export type RunArtifactCategoryFilter = RunArtifactCategoryKey | "all";
export type RunArtifactStateFilter = "all" | "exists" | "missing" | "warnings" | "previewable";
export type RunArtifactFilters = {
  category?: RunArtifactCategoryFilter;
  kind?: string;
  state?: RunArtifactStateFilter;
  source?: string;
};
export type ArtifactClassification = {
  category: RunArtifactCategoryKey;
  label: string;
  priority: number;
  tags: string[];
  reason: string;
};
export type ArtifactGroup = {
  category: RunArtifactCategoryKey;
  label: string;
  artifacts: RunArtifactRecord[];
};
export type RawSummaryCompact = {
  raw?: Record<string, unknown>;
  raw_truncated: boolean;
};
export type MarkdownPreviewBlock =
  | { type: "heading"; level: number; text: string }
  | { type: "list_item"; text: string }
  | { type: "code"; text: string }
  | { type: "paragraph"; text: string }
  | { type: "rule" };
export type RunHealthSummary = {
  status: string;
  statusTone: RunStatusToneKey;
  nodesTotal: number | null;
  nodesSucceeded: number | null;
  nodesFailed: number | null;
  nodesSkipped: number | null;
  warningsCount: number;
  errorsCount: number;
  missingArtifactCount: number;
  failedLogCount: number;
  hasMissingArtifacts: boolean;
  hasFailedNodeLogs: boolean;
  warningMessages: string[];
  errorMessages: string[];
};
export type QcHighlightMetric = {
  label: string;
  value: string;
};
export type QcArtifactHighlight = {
  artifact: RunArtifactRecord;
  artifactId: string;
  artifactName: string;
  kind: string;
  reference: string;
  category: "qc_json" | "qc_report";
  status: string | null;
  passed: boolean | null;
  failed: boolean | null;
  warnings: string[];
  metrics: QcHighlightMetric[];
  subjectId: string | null;
  nodeId: string | null;
  errorMessage: string | null;
  topLevelKeys: string[];
};
export type FailedNodeHighlight = {
  nodeId: string;
  nodeName: string | null;
  status: string;
  errorExcerpt: string | null;
  artifact: RunArtifactRecord | null;
  artifactId: string | null;
  artifactName: string | null;
};
export type ArtifactProvenanceRow = {
  artifactId: string;
  artifactName: string;
  kind: string;
  category: RunArtifactCategoryKey;
  source: string;
  nodeId: string | null;
  exists: boolean;
  state: "missing" | "warnings" | "previewable" | "metadata_only";
  reference: string;
};

const RAW_SUMMARY_MAX_CHARS = 20_000;
const RUN_ERROR_EXCERPT_LIMIT = 900;
const QC_HIGHLIGHT_LIMIT = 8;
const QC_METRIC_LIMIT = 8;
const PREVIEWABLE_ARTIFACT_SUFFIXES = new Set([".json", ".txt", ".md", ".csv", ".log"]);
const ARTIFACT_CATEGORY_DEFINITIONS: Array<{
  key: RunArtifactCategoryKey;
  label: string;
  priority: number;
}> = [
  { key: "summary", label: "Summary", priority: 0 },
  { key: "pipeline", label: "Pipeline", priority: 8 },
  { key: "reports", label: "Reports", priority: 16 },
  { key: "qc", label: "QC", priority: 24 },
  { key: "logs", label: "Logs", priority: 34 },
  { key: "tables", label: "Tables / CSV", priority: 44 },
  { key: "json", label: "JSON artifacts", priority: 54 },
  { key: "images", label: "Images / figures", priority: 64 },
  { key: "other_binary", label: "Other binary artifacts", priority: 74 },
];

export const ARTIFACT_CATEGORIES = ARTIFACT_CATEGORY_DEFINITIONS.map(({ key, label }) => ({
  key,
  label,
}));
const ARTIFACT_CATEGORY_META = new Map(
  ARTIFACT_CATEGORY_DEFINITIONS.map((item) => [item.key, item])
);

type WarningCarrier = {
  warnings?: unknown;
} | null | undefined;

type ExternalPathHost = {
  medimage?: {
    openExternalPath?: unknown;
  };
} | null | undefined;

function cleanPath(value: string | null | undefined): string | null {
  return value && value.trim().length ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length ? value : undefined;
}

function numberValue(value: unknown): number | null | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim().length) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  if (value === null) return null;
  return undefined;
}

function stringWarnings(source: unknown): string[] {
  if (Array.isArray(source)) {
    return source.filter(
      (warning): warning is string => typeof warning === "string" && warning.trim().length > 0
    );
  }
  if (!isRecord(source) || !Array.isArray(source.warnings)) return [];
  return source.warnings.filter(
    (warning): warning is string => typeof warning === "string" && warning.trim().length > 0
  );
}

function firstField(source: Record<string, unknown>, raw: Record<string, unknown>, names: string[]) {
  for (const name of names) {
    if (source[name] !== undefined) return source[name];
  }
  for (const name of names) {
    if (raw[name] !== undefined) return raw[name];
  }
  return undefined;
}

function recordField(value: unknown): Record<string, unknown> | undefined {
  if (isRecord(value)) return value;
  if (Array.isArray(value)) return { items: value };
  return undefined;
}

function arrayField(value: unknown): unknown[] | undefined {
  return Array.isArray(value) ? value : undefined;
}

function jsonValueType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (isRecord(value)) return "object";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  if (typeof value === "string") return "string";
  return typeof value;
}

function jsonValueShape(value: unknown): Omit<JsonFieldSummary, "key"> {
  const shape: Omit<JsonFieldSummary, "key"> = { type: jsonValueType(value) };
  if (isRecord(value)) {
    shape.size = Object.keys(value).length;
    shape.keys = Object.keys(value).slice(0, 10);
  } else if (Array.isArray(value)) {
    const sampleTypes: string[] = [];
    for (const item of value.slice(0, 10)) {
      const itemType = jsonValueType(item);
      if (!sampleTypes.includes(itemType)) sampleTypes.push(itemType);
    }
    shape.size = value.length;
    shape.sample_types = sampleTypes;
  } else if (typeof value === "string") {
    shape.size = value.length;
  }
  return shape;
}

function jsonMessageSample(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function buildJsonMessageSummary(value: unknown): JsonMessageSummary {
  const items = value === undefined || value === null ? [] : Array.isArray(value) ? value : [value];
  return {
    count: items.length,
    sample: items.slice(0, 5).map(jsonMessageSample),
  };
}

function normalizeJsonMessageSummary(value: unknown): JsonMessageSummary {
  if (!isRecord(value)) return buildJsonMessageSummary(value);
  const countValue = numberValue(value.count);
  const sample = Array.isArray(value.sample)
    ? value.sample.map((item) => String(item)).filter((item) => item.length > 0)
    : [];
  return {
    count: countValue ?? sample.length,
    sample,
  };
}

function compactText(value: string, limit = RUN_ERROR_EXCERPT_LIMIT): string {
  const normalized = value.replace(/\r\n/g, "\n").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit).trimEnd()}...`;
}

function printableScalar(value: unknown, limit = 220): string | undefined {
  if (value === null || value === undefined) return undefined;
  if (typeof value === "string") return value.trim().length ? compactText(value, limit) : undefined;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value) || isRecord(value)) {
    try {
      return compactText(JSON.stringify(value), limit);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function messageList(value: unknown): string[] {
  if (value === undefined || value === null) return [];
  if (isRecord(value) && Array.isArray(value.sample)) {
    return value.sample
      .map((item) => printableScalar(item))
      .filter((item): item is string => Boolean(item));
  }
  const items = Array.isArray(value) ? value : [value];
  return items
    .map((item) => printableScalar(item))
    .filter((item): item is string => Boolean(item));
}

function boolValue(value: unknown): boolean | undefined {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "yes", "y", "1", "pass", "passed", "success", "ok"].includes(normalized)) {
      return true;
    }
    if (["false", "no", "n", "0", "fail", "failed", "error"].includes(normalized)) {
      return false;
    }
  }
  return undefined;
}

function firstPrintableField(source: unknown, names: string[]): string | null {
  if (!isRecord(source)) return null;
  for (const name of names) {
    const value = printableScalar(source[name]);
    if (value) return value;
  }
  return null;
}

function fieldList(source: unknown, names: string[]): string[] {
  if (!isRecord(source)) return [];
  for (const name of names) {
    const values = messageList(source[name]);
    if (values.length) return values;
  }
  return [];
}

function jsonStatusValue(value: unknown): string | number | boolean | null | undefined {
  if (!isRecord(value)) return undefined;
  for (const key of ["status", "pipeline_status", "ok", "success"]) {
    const candidate = value[key];
    if (candidate === null) return null;
    if (typeof candidate === "string" || typeof candidate === "number" || typeof candidate === "boolean") {
      return candidate;
    }
  }
  return undefined;
}

function normalizeJsonFieldSummary(value: unknown): JsonFieldSummary | null {
  if (!isRecord(value)) return null;
  const key = stringValue(value.key);
  const type = stringValue(value.type);
  if (!key || !type) return null;
  return {
    key,
    type,
    size: numberValue(value.size),
    keys: Array.isArray(value.keys) ? value.keys.map((item) => String(item)) : undefined,
    sample_types: Array.isArray(value.sample_types)
      ? value.sample_types.map((item) => String(item))
      : undefined,
  };
}

function buildJsonPreviewSummary(value: unknown): JsonPreviewSummary {
  const rootShape = jsonValueShape(value);
  const summary: JsonPreviewSummary = {
    type: rootShape.type,
    size: rootShape.size,
    top_level_keys: [],
    status: null,
    warnings: { count: 0, sample: [] },
    errors: { count: 0, sample: [] },
    field_summaries: [],
  };

  if (isRecord(value)) {
    const keys = Object.keys(value);
    summary.top_level_keys = keys.slice(0, 50);
    summary.status = jsonStatusValue(value) ?? null;
    summary.warnings = buildJsonMessageSummary(value.warnings);
    summary.errors = buildJsonMessageSummary(value.errors);
    summary.field_summaries = keys.slice(0, 50).map((key) => ({
      key,
      ...jsonValueShape(value[key]),
    }));
  } else if (Array.isArray(value)) {
    summary.field_summaries = value.slice(0, 10).map((item, index) => ({
      key: `[${index}]`,
      ...jsonValueShape(item),
    }));
  }
  return summary;
}

function artifactSuffix(name: string): string {
  const normalized = name.toLowerCase();
  if (normalized.endsWith(".nii.gz")) return ".nii.gz";
  const index = normalized.lastIndexOf(".");
  return index >= 0 ? normalized.slice(index) : "";
}

function lowerArtifactText(artifact: Partial<RunArtifactRecord>): string {
  return [
    artifact.name,
    artifact.kind,
    artifact.path,
    artifact.relative_path,
    artifact.source,
    artifact.suffix,
  ]
    .filter((item): item is string => typeof item === "string" && item.length > 0)
    .join(" ")
    .replace(/\\/g, "/")
    .toLowerCase();
}

function categoryMeta(category: RunArtifactCategoryKey) {
  return ARTIFACT_CATEGORY_META.get(category) ?? ARTIFACT_CATEGORY_DEFINITIONS[ARTIFACT_CATEGORY_DEFINITIONS.length - 1];
}

function hasAnyToken(text: string, tokens: string[]): boolean {
  return tokens.some((token) => text.includes(token));
}

function failedNodeTokens(runSummary?: RunSummaryPreview | null): string[] {
  const nodes = runSummary?.failed_nodes ?? [];
  const tokens: string[] = [];
  for (const node of nodes) {
    if (!isRecord(node)) continue;
    for (const field of ["node_id", "node", "id", "name"]) {
      const value = stringValue(node[field]);
      if (value) tokens.push(value.toLowerCase());
    }
  }
  return Array.from(new Set(tokens));
}

function artifactReference(artifact: RunArtifactRecord): string {
  return artifact.relative_path || artifact.path || artifact.name;
}

function artifactNodeId(artifact: RunArtifactRecord): string | null {
  const direct = stringValue(artifact.node_id ?? undefined);
  if (direct) return direct;
  const source = artifact.source || "";
  const nodeStateMatch = /node_state:([^\\/]+?)(?:\.json)?$/i.exec(source);
  if (nodeStateMatch?.[1]) return nodeStateMatch[1];
  const statePathMatch = /(?:^|[/\\])states[/\\][^/\\]+[/\\]([^/\\]+?)(?:\.json)?$/i.exec(
    artifact.relative_path || artifact.path || ""
  );
  return statePathMatch?.[1] || null;
}

function failedNodeId(node: Record<string, unknown>, fallback: string): string {
  return (
    stringValue(node.node_id) ||
    stringValue(node.node) ||
    stringValue(node.id) ||
    stringValue(node.name) ||
    fallback
  );
}

function failedNodeName(node: Record<string, unknown>): string | null {
  return stringValue(node.name) || stringValue(node.node) || null;
}

function failedNodeErrorMessages(node: Record<string, unknown>): string[] {
  return [
    ...fieldList(node, ["errors", "error", "error_message", "message"]),
    ...fieldList(node, ["stderr", "stderr_excerpt", "traceback"]),
  ];
}

function collectRunErrorMessages(runSummary?: RunSummaryPreview | null): string[] {
  const messages: string[] = [];
  const summaryErrors = runSummary?.errors ?? [];
  for (const item of summaryErrors) {
    if (isRecord(item)) {
      const node = firstPrintableField(item, ["node_id", "node", "id", "name"]);
      const itemMessages = fieldList(item, ["errors", "error", "error_message", "message"]);
      if (itemMessages.length) {
        messages.push(...itemMessages.map((message) => (node ? `${node}: ${message}` : message)));
      } else {
        const fallback = printableScalar(item);
        if (fallback) messages.push(fallback);
      }
    } else {
      const message = printableScalar(item);
      if (message) messages.push(message);
    }
  }

  for (const [index, node] of (runSummary?.failed_nodes ?? []).entries()) {
    if (!isRecord(node)) continue;
    const nodeId = failedNodeId(node, `failed_node_${index + 1}`);
    const itemMessages = failedNodeErrorMessages(node);
    if (itemMessages.length) {
      messages.push(...itemMessages.map((message) => `${nodeId}: ${message}`));
    } else {
      messages.push(`${nodeId}: failed`);
    }
  }

  return Array.from(new Set(messages));
}

function compareArtifactRecords(
  a: RunArtifactRecord,
  b: RunArtifactRecord,
  runSummary?: RunSummaryPreview | null
): number {
  const aScore = artifactPriority(a, runSummary);
  const bScore = artifactPriority(b, runSummary);
  if (aScore !== bScore) return aScore - bScore;
  const aName = `${a.relative_path || a.path || ""} ${a.name}`.toLowerCase();
  const bName = `${b.relative_path || b.path || ""} ${b.name}`.toLowerCase();
  return aName.localeCompare(bName);
}

function artifactPriority(
  artifact: RunArtifactRecord,
  runSummary?: RunSummaryPreview | null
): number {
  const classification = classifyArtifact(artifact);
  let priority = classification.priority;
  if (isFailedNodeArtifact(artifact, runSummary)) priority -= 14;
  if (getArtifactWarnings(artifact).length) priority -= 5;
  if (!artifact.exists) priority -= 3;
  return priority;
}

function isSummaryTable(artifact: RunArtifactRecord): boolean {
  const text = lowerArtifactText(artifact);
  return artifact.kind === "csv" && hasAnyToken(text, ["summary", "table", "qc", "metrics"]);
}

function keyArtifactPriority(
  artifact: RunArtifactRecord,
  runSummary?: RunSummaryPreview | null
): number {
  const classification = classifyArtifact(artifact);
  const hasWarnings = getArtifactWarnings(artifact).length > 0;
  const failedLog =
    classification.category === "logs" && isFailedNodeArtifact(artifact, runSummary);
  let priority =
    classification.category === "summary"
      ? 0
      : classification.category === "pipeline"
        ? 10
        : classification.category === "reports"
          ? 20
          : classification.category === "qc"
            ? 30
            : failedLog
              ? 36
              : classification.category === "tables"
                ? 46
                : classification.category === "logs"
                  ? 56
                  : classification.priority + 80;
  if (hasWarnings) priority -= 4;
  if (!artifact.exists) priority -= 3;
  return priority;
}

export function mergeSummaryWarnings(...sources: unknown[]): string[] {
  return Array.from(new Set(sources.flatMap((source) => stringWarnings(source))));
}

export function getRunWarnings(run: WarningCarrier): string[] {
  return mergeSummaryWarnings(run);
}

export function extractRunPaths(
  run: Pick<RunLinkRecord, "pipeline_path" | "summary_path"> | null | undefined,
  projectDir?: string | null
): RunPathEntry[] {
  return [
    { label: "Pipeline YAML", path: cleanPath(run?.pipeline_path) },
    { label: "Summary JSON", path: cleanPath(run?.summary_path) },
    { label: "Project directory", path: cleanPath(projectDir) },
  ];
}

export function canOpenExternalPath(host: ExternalPathHost): boolean {
  return typeof host?.medimage?.openExternalPath === "function";
}

export function artifactPath(artifact: Pick<RunArtifactRecord, "path"> | null | undefined): string | null {
  return cleanPath(artifact?.path);
}

export function isPreviewableArtifactName(name: string): boolean {
  return PREVIEWABLE_ARTIFACT_SUFFIXES.has(artifactSuffix(name));
}

export function isPreviewableArtifact(artifact: Pick<RunArtifactRecord, "name" | "previewable">): boolean {
  return Boolean(artifact.previewable) && isPreviewableArtifactName(artifact.name);
}

export function getArtifactCategoryLabel(category: RunArtifactCategoryKey): string {
  return categoryMeta(category).label;
}

export function classifyArtifact(artifact: RunArtifactRecord): ArtifactClassification {
  const text = lowerArtifactText(artifact);
  const kind = artifact.kind.toLowerCase();
  const suffix = (artifact.suffix || artifactSuffix(artifact.name)).toLowerCase();
  const tags: string[] = [];
  if (!artifact.exists) tags.push("missing");
  if (getArtifactWarnings(artifact).length) tags.push("warnings");
  if (isPreviewableArtifact(artifact)) tags.push("previewable");
  if (!isPreviewableArtifact(artifact)) tags.push("metadata-only");

  let category: RunArtifactCategoryKey = "other_binary";
  let reason = "Fallback for binary, NIfTI, MAT, or uncategorized artifacts.";

  if (
    artifact.source === "run_link.summary_path" ||
    artifact.name.toLowerCase() === "summary.json" ||
    /(^|[/\\])summary\.json$/.test(artifact.path.toLowerCase())
  ) {
    category = "summary";
    reason = "Run summary JSON from the run link.";
  } else if (
    artifact.source === "run_link.pipeline_path" ||
    suffix === ".yaml" ||
    suffix === ".yml" ||
    hasAnyToken(text, ["pipeline.yaml", "pipeline.yml"])
  ) {
    category = "pipeline";
    reason = "Pipeline YAML associated with this run.";
  } else if (kind === "log" || hasAnyToken(text, [".log", "stdout", "stderr", "log_path"])) {
    category = "logs";
    reason = "Execution log or node log artifact.";
  } else if (
    kind === "csv" ||
    suffix === ".csv" ||
    hasAnyToken(text, ["table.csv", "summary_table", "subject_qc_table"])
  ) {
    category = "tables";
    reason = "Tabular CSV artifact.";
  } else if (
    (kind === "markdown" || kind === "text") &&
    hasAnyToken(text, ["report", "/reports/", "readme"])
  ) {
    category = "reports";
    reason = "Report markdown or text artifact.";
  } else if (
    hasAnyToken(text, ["qc", "quality", "motion", "mean_fd", "fd_", "metrics"]) &&
    !["binary", "image", "nifti", "matlab"].includes(kind)
  ) {
    category = "qc";
    reason = "QC or metric artifact inferred from name, path, or source.";
  } else if (kind === "json" || suffix === ".json") {
    category = "json";
    reason = "Generic JSON artifact.";
  } else if (kind === "image" || [".png", ".jpg", ".jpeg"].includes(suffix)) {
    category = "images";
    reason = "Image or figure artifact.";
  }

  tags.push(category);
  const meta = categoryMeta(category);
  return {
    category,
    label: meta.label,
    priority: meta.priority,
    tags: Array.from(new Set(tags)),
    reason,
  };
}

export function isFailedNodeArtifact(
  artifact: RunArtifactRecord,
  runSummary?: RunSummaryPreview | null
): boolean {
  const text = `${lowerArtifactText(artifact)} ${getArtifactWarnings(artifact).join(" ")}`.toLowerCase();
  if (hasAnyToken(text, ["failed", "failure", "stderr", "error.log"])) return true;
  return failedNodeTokens(runSummary).some((token) => text.includes(token));
}

export function sortArtifacts(
  artifacts: RunArtifactRecord[],
  runSummary?: RunSummaryPreview | null
): RunArtifactRecord[] {
  return [...artifacts].sort((a, b) => compareArtifactRecords(a, b, runSummary));
}

export function groupArtifacts(
  artifacts: RunArtifactRecord[],
  runSummary?: RunSummaryPreview | null
): ArtifactGroup[] {
  const sorted = sortArtifacts(artifacts, runSummary);
  return ARTIFACT_CATEGORY_DEFINITIONS.map((definition) => ({
    category: definition.key,
    label: definition.label,
    artifacts: sorted.filter((artifact) => classifyArtifact(artifact).category === definition.key),
  })).filter((group) => group.artifacts.length > 0);
}

export function filterArtifacts(
  artifacts: RunArtifactRecord[],
  filters: RunArtifactFilters = {}
): RunArtifactRecord[] {
  const category = filters.category ?? "all";
  const kind = filters.kind && filters.kind !== "all" ? filters.kind : "";
  const source = filters.source && filters.source !== "all" ? filters.source : "";
  const state = filters.state ?? "all";

  return artifacts.filter((artifact) => {
    const classification = classifyArtifact(artifact);
    if (category !== "all" && classification.category !== category) return false;
    if (kind && artifact.kind !== kind) return false;
    if (source && artifact.source !== source) return false;
    if (state === "exists" && !artifact.exists) return false;
    if (state === "missing" && artifact.exists) return false;
    if (state === "warnings" && !getArtifactWarnings(artifact).length) return false;
    if (state === "previewable" && !isPreviewableArtifact(artifact)) return false;
    return true;
  });
}

export function getKeyArtifactReason(
  artifact: RunArtifactRecord,
  runSummary?: RunSummaryPreview | null
): string {
  const classification = classifyArtifact(artifact);
  if (!artifact.exists) return "Missing artifact to resolve";
  if (getArtifactWarnings(artifact).length) return "Warning-bearing artifact";
  if (classification.category === "summary") return "Summary JSON";
  if (classification.category === "pipeline") return "Pipeline YAML";
  if (classification.category === "reports") return "Report entry";
  if (classification.category === "qc") return "QC entry";
  if (classification.category === "logs" && isFailedNodeArtifact(artifact, runSummary)) {
    return "Failed-node log";
  }
  if (classification.category === "tables") return "CSV summary table";
  if (classification.category === "logs") return "Run log";
  return classification.reason;
}

export function getKeyArtifacts(
  artifacts: RunArtifactRecord[],
  runSummary?: RunSummaryPreview | null,
  limit = 8
): RunArtifactRecord[] {
  const sorted = sortArtifacts(artifacts, runSummary);
  const candidates = sorted.filter((artifact) => {
    const classification = classifyArtifact(artifact);
    const hasWarnings = getArtifactWarnings(artifact).length > 0;
    if (!artifact.exists || hasWarnings) return true;
    if (["summary", "pipeline", "reports", "qc"].includes(classification.category)) return true;
    if (classification.category === "logs" && isFailedNodeArtifact(artifact, runSummary)) return true;
    if (classification.category === "tables" && isSummaryTable(artifact)) return true;
    return false;
  });
  const seen = new Set<string>();
  const keyArtifacts: RunArtifactRecord[] = [];
  for (const artifact of candidates.sort((a, b) => {
    const aScore = keyArtifactPriority(a, runSummary);
    const bScore = keyArtifactPriority(b, runSummary);
    if (aScore !== bScore) return aScore - bScore;
    return compareArtifactRecords(a, b, runSummary);
  })) {
    if (seen.has(artifact.artifact_id)) continue;
    seen.add(artifact.artifact_id);
    keyArtifacts.push(artifact);
    if (keyArtifacts.length >= limit) return keyArtifacts;
  }

  for (const category of ["logs", "tables"] as RunArtifactCategoryKey[]) {
    if (keyArtifacts.length >= limit) break;
    if (keyArtifacts.some((artifact) => classifyArtifact(artifact).category === category)) continue;
    const artifact = sorted.find((item) => classifyArtifact(item).category === category);
    if (artifact && !seen.has(artifact.artifact_id)) {
      seen.add(artifact.artifact_id);
      keyArtifacts.push(artifact);
    }
  }
  return keyArtifacts.slice(0, limit);
}

export function formatArtifactSize(sizeBytes?: number | null): string {
  if (sizeBytes === null || sizeBytes === undefined || !Number.isFinite(sizeBytes)) return "-";
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = sizeBytes / 1024;
  for (const unit of units) {
    if (value < 1024 || unit === units[units.length - 1]) {
      return `${value.toFixed(value < 10 ? 1 : 0)} ${unit}`;
    }
    value /= 1024;
  }
  return `${sizeBytes} B`;
}

export function getArtifactWarnings(artifact: { warnings?: unknown } | null | undefined): string[] {
  return mergeSummaryWarnings(artifact);
}

export function normalizeCsvPreview(value: unknown): CsvPreviewTable | null {
  if (!isRecord(value)) return null;
  const columns = Array.isArray(value.columns)
    ? value.columns.map((item) => String(item))
    : [];
  const rows = Array.isArray(value.rows)
    ? value.rows
        .filter(Array.isArray)
        .map((row) => row.map((item) => String(item)))
    : [];
  return {
    columns,
    rows,
    row_count: numberValue(value.row_count) ?? rows.length,
    displayed_rows: numberValue(value.displayed_rows) ?? rows.length,
    truncated: Boolean(value.truncated),
    columns_truncated: Boolean(value.columns_truncated),
  };
}

export function normalizeJsonPreviewSummary(
  preview: Pick<RunArtifactPreviewResponse, "json" | "json_summary"> | null | undefined
): JsonPreviewSummary | null {
  if (!preview) return null;
  if (isRecord(preview.json_summary)) {
    const type = stringValue(preview.json_summary.type) ?? "unknown";
    const fieldSummaries = Array.isArray(preview.json_summary.field_summaries)
      ? preview.json_summary.field_summaries
          .map(normalizeJsonFieldSummary)
          .filter((item): item is JsonFieldSummary => item !== null)
      : [];
    return {
      type,
      size: numberValue(preview.json_summary.size),
      top_level_keys: Array.isArray(preview.json_summary.top_level_keys)
        ? preview.json_summary.top_level_keys.map((item) => String(item))
        : [],
      status:
        typeof preview.json_summary.status === "string" ||
        typeof preview.json_summary.status === "number" ||
        typeof preview.json_summary.status === "boolean" ||
        preview.json_summary.status === null
          ? preview.json_summary.status
          : null,
      warnings: normalizeJsonMessageSummary(preview.json_summary.warnings),
      errors: normalizeJsonMessageSummary(preview.json_summary.errors),
      field_summaries: fieldSummaries,
    };
  }
  if (preview.json !== null && preview.json !== undefined) {
    return buildJsonPreviewSummary(preview.json);
  }
  return null;
}

function jsonSummaryFromArtifact(artifact: RunArtifactRecord): JsonPreviewSummary | null {
  const directSummary = normalizeJsonPreviewSummary({
    json: null,
    json_summary: artifact.json_summary ?? null,
  });
  if (directSummary) return directSummary;
  if (isRecord(artifact.qc_summary)) {
    return normalizeJsonPreviewSummary({
      json: null,
      json_summary: artifact.qc_summary.json_summary ?? null,
    });
  }
  return null;
}

function metricRowsFromValue(value: unknown): QcHighlightMetric[] {
  const rows: QcHighlightMetric[] = [];
  if (Array.isArray(value)) {
    for (const item of value) {
      if (isRecord(item)) {
        const label = firstPrintableField(item, ["label", "name", "key", "metric"]);
        const metricValue = firstPrintableField(item, ["value", "score", "result"]);
        if (label && metricValue) rows.push({ label, value: metricValue });
      }
      if (rows.length >= QC_METRIC_LIMIT) return rows;
    }
  } else if (isRecord(value)) {
    for (const [key, item] of Object.entries(value)) {
      const metricValue = printableScalar(item);
      if (metricValue) rows.push({ label: key, value: metricValue });
      if (rows.length >= QC_METRIC_LIMIT) return rows;
    }
  }
  return rows;
}

function metricRowsFromJsonSummary(summary: JsonPreviewSummary | null): QcHighlightMetric[] {
  if (!summary) return [];
  const metricTokens = ["metric", "mean", "fd", "dvars", "snr", "tsnr", "motion", "threshold"];
  return summary.field_summaries
    .filter((field) => hasAnyToken(field.key.toLowerCase(), metricTokens))
    .slice(0, QC_METRIC_LIMIT)
    .map((field) => {
      const detail =
        field.size !== undefined && field.size !== null
          ? `${field.type}, size ${field.size}`
          : field.type;
      return { label: field.key, value: detail };
    });
}

function qcStatusBooleans(status: unknown): { passed: boolean | null; failed: boolean | null } {
  const normalized = String(status ?? "").trim().toUpperCase();
  if (["PASS", "PASSED", "SUCCESS", "OK", "TRUE"].includes(normalized)) {
    return { passed: true, failed: false };
  }
  if (["FAIL", "FAILED", "ERROR", "FALSE"].includes(normalized)) {
    return { passed: false, failed: true };
  }
  return { passed: null, failed: null };
}

function isQcArtifact(artifact: RunArtifactRecord): boolean {
  const classification = classifyArtifact(artifact);
  if (classification.category === "qc") return true;
  const text = lowerArtifactText(artifact);
  if (classification.category === "reports" && hasAnyToken(text, ["qc", "quality"])) return true;
  if (artifact.kind === "json" && hasAnyToken(text, ["qc", "quality", "motion", "mean_fd", "fd_", "metrics"])) {
    return true;
  }
  return false;
}

function failedLogArtifacts(
  artifacts: RunArtifactRecord[],
  runSummary?: RunSummaryPreview | null
): RunArtifactRecord[] {
  return artifacts.filter((artifact) => {
    const classification = classifyArtifact(artifact);
    return classification.category === "logs" && isFailedNodeArtifact(artifact, runSummary);
  });
}

export function summarizeRunHealth(
  run: Pick<RunLinkRecord, "status" | "warnings"> | null | undefined,
  summaryPreview: RunSummaryPreview | null | undefined,
  artifacts: RunArtifactRecord[] = []
): RunHealthSummary {
  const warningMessages = mergeSummaryWarnings(run, summaryPreview, ...artifacts);
  const errorMessages = collectRunErrorMessages(summaryPreview);
  const missingArtifactCount = artifacts.filter((artifact) => !artifact.exists).length;
  const failedLogCount = failedLogArtifacts(artifacts, summaryPreview).length;
  const nodesFailed = summaryPreview?.nodes_failed ?? (summaryPreview?.failed_nodes?.length || null);

  return {
    status: summaryPreview?.status || run?.status || "UNKNOWN",
    statusTone: getRunStatusToneKey(summaryPreview?.status || run?.status),
    nodesTotal: summaryPreview?.nodes_total ?? null,
    nodesSucceeded: summaryPreview?.nodes_succeeded ?? null,
    nodesFailed,
    nodesSkipped: summaryPreview?.nodes_skipped ?? null,
    warningsCount: warningMessages.length,
    errorsCount: errorMessages.length,
    missingArtifactCount,
    failedLogCount,
    hasMissingArtifacts: missingArtifactCount > 0,
    hasFailedNodeLogs: failedLogCount > 0,
    warningMessages,
    errorMessages,
  };
}

export function extractQcHighlights(
  artifacts: RunArtifactRecord[] = []
): QcArtifactHighlight[] {
  const highlights: QcArtifactHighlight[] = [];
  for (const artifact of sortArtifacts(artifacts).filter(isQcArtifact)) {
    const qcSummary: Record<string, unknown> = isRecord(artifact.qc_summary) ? artifact.qc_summary : {};
    const jsonSummary = jsonSummaryFromArtifact(artifact);
    const status =
      firstPrintableField(qcSummary, ["status", "pipeline_status", "ok", "success"]) ??
      printableScalar(jsonSummary?.status) ??
      null;
    const statusBools = qcStatusBooleans(status);
    const passed = boolValue(qcSummary.passed) ?? boolValue(qcSummary.ok) ?? boolValue(qcSummary.success) ?? statusBools.passed;
    const failed = boolValue(qcSummary.failed) ?? statusBools.failed;
    const warnings = Array.from(
      new Set([
        ...getArtifactWarnings(artifact),
        ...messageList(qcSummary.warnings),
        ...(jsonSummary?.warnings.sample ?? []),
      ])
    );
    const metrics = metricRowsFromValue(qcSummary.metrics);
    const fallbackMetrics = metricRowsFromJsonSummary(jsonSummary);
    highlights.push({
      artifact,
      artifactId: artifact.artifact_id,
      artifactName: artifact.name,
      kind: artifact.kind,
      reference: artifactReference(artifact),
      category: artifact.kind === "json" ? "qc_json" : "qc_report",
      status,
      passed: passed ?? null,
      failed: failed ?? null,
      warnings,
      metrics: metrics.length ? metrics : fallbackMetrics,
      subjectId: firstPrintableField(qcSummary, ["subject_id", "subject"]) ?? null,
      nodeId:
        firstPrintableField(qcSummary, ["node_id", "node"]) ??
        artifactNodeId(artifact),
      errorMessage:
        firstPrintableField(qcSummary, ["error_message", "error"]) ??
        messageList(qcSummary.errors)[0] ??
        jsonSummary?.errors.sample[0] ??
        null,
      topLevelKeys: jsonSummary?.top_level_keys.slice(0, 12) ?? [],
    });
    if (highlights.length >= QC_HIGHLIGHT_LIMIT) return highlights;
  }
  return highlights;
}

export function extractFailedNodeHighlights(
  summaryPreview: RunSummaryPreview | null | undefined,
  artifacts: RunArtifactRecord[] = []
): FailedNodeHighlight[] {
  const byNode = new Map<string, FailedNodeHighlight>();
  const failedNodes = summaryPreview?.failed_nodes ?? [];

  failedNodes.forEach((node, index) => {
    if (!isRecord(node)) return;
    const nodeId = failedNodeId(node, `failed_node_${index + 1}`);
    const errors = failedNodeErrorMessages(node);
    byNode.set(nodeId, {
      nodeId,
      nodeName: failedNodeName(node),
      status: stringValue(node.status) || "FAILED",
      errorExcerpt: errors.length ? compactText(errors.join("\n")) : null,
      artifact: null,
      artifactId: null,
      artifactName: null,
    });
  });

  const errorMessages = collectRunErrorMessages(summaryPreview);
  for (const message of errorMessages) {
    const nodeId = message.includes(":") ? message.split(":", 1)[0].trim() : "run";
    if (!byNode.has(nodeId)) {
      byNode.set(nodeId, {
        nodeId,
        nodeName: null,
        status: "FAILED",
        errorExcerpt: compactText(message),
        artifact: null,
        artifactId: null,
        artifactName: null,
      });
    } else if (!byNode.get(nodeId)?.errorExcerpt) {
      byNode.get(nodeId)!.errorExcerpt = compactText(message.replace(`${nodeId}:`, "").trim());
    }
  }

  const knownNodeIds = Array.from(byNode.keys());
  for (const artifact of failedLogArtifacts(artifacts, summaryPreview)) {
    const text = lowerArtifactText(artifact);
    const artifactNode =
      artifactNodeId(artifact) ||
      knownNodeIds.find((nodeId) => text.includes(nodeId.toLowerCase())) ||
      "log";
    const existing = byNode.get(artifactNode);
    const errorExcerpt = printableScalar(artifact.error_excerpt, RUN_ERROR_EXCERPT_LIMIT) ?? null;
    if (existing) {
      existing.artifact = artifact;
      existing.artifactId = artifact.artifact_id;
      existing.artifactName = artifact.name;
      if (
        errorExcerpt &&
        (!existing.errorExcerpt ||
          existing.errorExcerpt === "failed" ||
          existing.errorExcerpt === `${artifactNode}: failed`)
      ) {
        existing.errorExcerpt = errorExcerpt;
      }
    } else {
      byNode.set(artifactNode, {
        nodeId: artifactNode,
        nodeName: null,
        status: "FAILED",
        errorExcerpt,
        artifact,
        artifactId: artifact.artifact_id,
        artifactName: artifact.name,
      });
    }
  }

  return Array.from(byNode.values()).slice(0, 8);
}

export function buildArtifactProvenanceRows(
  artifacts: RunArtifactRecord[] = []
): ArtifactProvenanceRow[] {
  return artifacts
    .map((artifact) => {
      const classification = classifyArtifact(artifact);
      const warnings = getArtifactWarnings(artifact);
      const state: ArtifactProvenanceRow["state"] = !artifact.exists
        ? "missing"
        : warnings.length
          ? "warnings"
          : isPreviewableArtifact(artifact)
            ? "previewable"
            : "metadata_only";
      return {
        artifactId: artifact.artifact_id,
        artifactName: artifact.name,
        kind: artifact.kind,
        category: classification.category,
        source: artifact.source || "unknown",
        nodeId: artifactNodeId(artifact),
        exists: artifact.exists,
        state,
        reference: artifactReference(artifact),
      };
    })
    .sort((a, b) =>
      `${a.source}|${a.nodeId || ""}|${a.kind}|${a.artifactName}`.localeCompare(
        `${b.source}|${b.nodeId || ""}|${b.kind}|${b.artifactName}`
      )
    );
}

export function markdownPreviewBlocks(
  content: string | null | undefined,
  maxBlocks = 200
): MarkdownPreviewBlock[] {
  if (!content || !content.trim()) return [];
  const blocks: MarkdownPreviewBlock[] = [];
  const codeLines: string[] = [];
  let inCode = false;

  for (const rawLine of content.split(/\r?\n/)) {
    const trimmed = rawLine.trim();
    if (trimmed.startsWith("```")) {
      if (inCode) {
        blocks.push({ type: "code", text: codeLines.join("\n") });
        codeLines.length = 0;
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      codeLines.push(rawLine);
      continue;
    }

    if (!trimmed) continue;
    const heading = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
    } else if (/^[-*]\s+/.test(trimmed)) {
      blocks.push({ type: "list_item", text: trimmed.replace(/^[-*]\s+/, "") });
    } else if (/^\d+[.)]\s+/.test(trimmed)) {
      blocks.push({ type: "list_item", text: trimmed.replace(/^\d+[.)]\s+/, "") });
    } else if (/^-{3,}$/.test(trimmed)) {
      blocks.push({ type: "rule" });
    } else {
      blocks.push({ type: "paragraph", text: rawLine.trimEnd() });
    }

    if (blocks.length >= maxBlocks) return blocks;
  }

  if (inCode && codeLines.length && blocks.length < maxBlocks) {
    blocks.push({ type: "code", text: codeLines.join("\n") });
  }
  return blocks.slice(0, maxBlocks);
}

export function missingSummaryWarning(summaryPath?: string | null): string {
  return summaryPath
    ? `Summary preview is not available for ${summaryPath}.`
    : "Summary preview is not available because this run has no summary_path.";
}

export function compactRawSummary(
  raw: unknown,
  maxChars = RAW_SUMMARY_MAX_CHARS
): RawSummaryCompact {
  if (!isRecord(raw)) return { raw: undefined, raw_truncated: false };
  const encoded = JSON.stringify(raw);
  if (encoded.length <= maxChars) {
    return { raw, raw_truncated: false };
  }
  return {
    raw: {
      truncated: true,
      size_chars: encoded.length,
      top_level_keys: Object.keys(raw).slice(0, 50),
      note: "Raw summary exceeded preview budget and was truncated.",
    },
    raw_truncated: true,
  };
}

export function normalizeRunSummaryPreview(
  value: unknown,
  fallbackRun?: Pick<RunLinkRecord, "run_id" | "status" | "warnings">
): RunSummaryPreview | null {
  if (!isRecord(value)) return null;

  const raw = isRecord(value.raw) ? value.raw : value;
  const failedNodes = arrayField(firstField(value, raw, ["failed_nodes"]));
  const rawCompact = compactRawSummary(value.raw ?? value);
  const nodesFailed =
    numberValue(firstField(value, raw, ["nodes_failed"])) ??
    (failedNodes ? failedNodes.length : undefined);

  return {
    run_id:
      stringValue(firstField(value, raw, ["run_id"])) ??
      fallbackRun?.run_id,
    status:
      stringValue(firstField(value, raw, ["status", "pipeline_status"])) ??
      fallbackRun?.status,
    started_at:
      stringValue(firstField(value, raw, ["started_at", "start_time"])) ?? null,
    finished_at:
      stringValue(firstField(value, raw, ["finished_at", "ended_at", "end_time"])) ?? null,
    nodes_total: numberValue(firstField(value, raw, ["nodes_total", "node_count"])),
    nodes_succeeded: numberValue(
      firstField(value, raw, ["nodes_succeeded", "nodes_success"])
    ),
    nodes_failed: nodesFailed,
    nodes_skipped: numberValue(firstField(value, raw, ["nodes_skipped"])),
    warnings: mergeSummaryWarnings(value, raw, fallbackRun),
    outputs: recordField(firstField(value, raw, ["outputs"])),
    errors: arrayField(firstField(value, raw, ["errors"])),
    failed_nodes: failedNodes?.filter(isRecord),
    raw: rawCompact.raw,
    raw_truncated: Boolean(value.raw_truncated) || rawCompact.raw_truncated,
  };
}

export function getRunStatusToneKey(status: string | null | undefined): RunStatusToneKey {
  const normalized = (status ?? "").toUpperCase();
  if (normalized === "SUCCESS" || normalized === "COMPLETED") return "success";
  if (normalized === "FAILED" || normalized === "BLOCKED") return "danger";
  if (normalized === "RUNNING" || normalized === "REQUESTED" || normalized === "SUBMITTED") {
    return "active";
  }
  return "neutral";
}
