const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const sourcePath = path.join(__dirname, "..", "src", "components", "projectRunsPanelModel.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const transpiled = ts.transpileModule(source, {
  fileName: sourcePath,
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
  reportDiagnostics: true,
});

const diagnostics = transpiled.diagnostics ?? [];
assert.equal(diagnostics.length, 0, diagnostics.map((item) => item.messageText).join("\n"));

const moduleState = { exports: {} };
vm.runInNewContext(
  transpiled.outputText,
  {
    exports: moduleState.exports,
    module: moduleState,
    require,
  },
  { filename: sourcePath }
);

const {
  ARTIFACT_CATEGORIES,
  artifactPath,
  buildArtifactProvenanceRows,
  canOpenExternalPath,
  classifyArtifact,
  compactRawSummary,
  extractFailedNodeHighlights,
  extractQcHighlights,
  extractRunPaths,
  filterArtifacts,
  formatArtifactSize,
  getArtifactWarnings,
  getArtifactCategoryLabel,
  getKeyArtifactReason,
  getKeyArtifacts,
  getRunStatusToneKey,
  getRunWarnings,
  groupArtifacts,
  isFailedNodeArtifact,
  isPreviewableArtifact,
  isPreviewableArtifactName,
  markdownPreviewBlocks,
  mergeSummaryWarnings,
  missingSummaryWarning,
  normalizeCsvPreview,
  normalizeJsonPreviewSummary,
  normalizeRunSummaryPreview,
  sortArtifacts,
  summarizeRunHealth,
} = moduleState.exports;

function assertJsonEqual(actual, expected) {
  assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected);
}

const run = {
  pipeline_path: "D:\\projects\\demo\\pipeline.yaml",
  summary_path: "D:\\projects\\demo\\summary.json",
  warnings: ["summary missing", "", 42, "pipeline path stale"],
};

assertJsonEqual(getRunWarnings(run), ["summary missing", "pipeline path stale"]);
assertJsonEqual(getRunWarnings({ warnings: null }), []);
assertJsonEqual(getRunWarnings(null), []);

assertJsonEqual(extractRunPaths(run, "D:\\projects\\demo"), [
  { label: "Pipeline YAML", path: "D:\\projects\\demo\\pipeline.yaml" },
  { label: "Summary JSON", path: "D:\\projects\\demo\\summary.json" },
  { label: "Project directory", path: "D:\\projects\\demo" },
]);
assertJsonEqual(extractRunPaths({ pipeline_path: "", summary_path: null }, null), [
  { label: "Pipeline YAML", path: null },
  { label: "Summary JSON", path: null },
  { label: "Project directory", path: null },
]);

assert.equal(canOpenExternalPath({}), false);
assert.equal(canOpenExternalPath({ medimage: { openExternalPath: "not a function" } }), false);
assert.equal(canOpenExternalPath({ medimage: { openExternalPath: () => Promise.resolve(true) } }), true);

const artifact = {
  name: "qc_metrics.json",
  path: "D:\\projects\\demo\\reports\\qc_metrics.json",
  previewable: true,
  warnings: ["artifact missing", "", 17],
};
assert.equal(artifactPath(artifact), "D:\\projects\\demo\\reports\\qc_metrics.json");
assert.equal(artifactPath({ path: " " }), null);
assert.equal(isPreviewableArtifactName("qc_report.md"), true);
assert.equal(isPreviewableArtifactName("node.log"), true);
assert.equal(isPreviewableArtifactName("bold.nii.gz"), false);
assert.equal(isPreviewableArtifact(artifact), true);
assert.equal(isPreviewableArtifact({ name: "bold.nii", previewable: true }), false);
assert.equal(isPreviewableArtifact({ name: "qc_metrics.json", previewable: false }), false);
assert.equal(formatArtifactSize(null), "-");
assert.equal(formatArtifactSize(512), "512 B");
assert.equal(formatArtifactSize(1536), "1.5 KB");
assert.equal(formatArtifactSize(2 * 1024 * 1024), "2.0 MB");
assertJsonEqual(getArtifactWarnings(artifact), ["artifact missing"]);
assert.equal(getArtifactCategoryLabel("summary"), "Summary");
assert.equal(ARTIFACT_CATEGORIES.some((item) => item.key === "qc" && item.label === "QC"), true);

function artifactRecord(overrides) {
  return {
    artifact_id: overrides.artifact_id,
    name: overrides.name,
    kind: overrides.kind,
    path: overrides.path ?? `D:\\projects\\demo\\work\\pipeline_runs\\run-a\\${overrides.name}`,
    relative_path: overrides.relative_path ?? `work\\pipeline_runs\\run-a\\${overrides.name}`,
    exists: overrides.exists ?? true,
    size_bytes: overrides.size_bytes ?? 128,
    modified_at: overrides.modified_at ?? "2026-06-05T01:00:00Z",
    previewable: overrides.previewable ?? true,
    warnings: overrides.warnings ?? [],
    source: overrides.source,
    suffix: overrides.suffix,
    node_id: overrides.node_id,
    category: overrides.category,
    error_excerpt: overrides.error_excerpt,
    json_summary: overrides.json_summary,
    qc_summary: overrides.qc_summary,
  };
}

const classificationSummary = artifactRecord({
  artifact_id: "a-summary",
  name: "summary.json",
  kind: "json",
  source: "run_link.summary_path",
});
const classificationPipeline = artifactRecord({
  artifact_id: "a-pipeline",
  name: "run-a.yaml",
  kind: "yaml",
  previewable: false,
  source: "run_link.pipeline_path",
  suffix: ".yaml",
});
const classificationReport = artifactRecord({
  artifact_id: "a-report",
  name: "qc_report.md",
  kind: "markdown",
  source: "summary.reports",
});
const classificationQc = artifactRecord({
  artifact_id: "a-qc",
  name: "qc_metrics.json",
  kind: "json",
  source: "summary.artifacts",
  warnings: ["minor motion note"],
  qc_summary: {
    status: "PASS",
    passed: true,
    failed: false,
    warnings: ["json warning"],
    metrics: [{ label: "mean_fd", value: "0.12" }],
    subject_id: "sub-01",
    node_id: "motion_qc_subject",
    error_message: null,
    json_summary: {
      type: "object",
      size: 6,
      top_level_keys: ["status", "mean_fd", "warnings", "errors", "subjects", "thresholds"],
      status: "PASS",
      warnings: { count: 1, sample: ["json warning"] },
      errors: { count: 0, sample: [] },
      field_summaries: [
        { key: "mean_fd", type: "number" },
        { key: "subjects", type: "array", size: 1, sample_types: ["object"] },
      ],
    },
  },
});
const classificationLog = artifactRecord({
  artifact_id: "a-log",
  name: "motion_qc_subject.stderr.log",
  kind: "log",
  source: "node_state:motion_qc_subject.json",
  node_id: "motion_qc_subject",
  error_excerpt: "Traceback\nRuntimeError: motion failed",
});
const classificationCsv = artifactRecord({
  artifact_id: "a-csv",
  name: "qc_table.csv",
  kind: "csv",
  source: "summary.outputs",
});
const classificationJson = artifactRecord({
  artifact_id: "a-json",
  name: "node_state.json",
  kind: "json",
  source: "summary.node_states",
});
const classificationImage = artifactRecord({
  artifact_id: "a-image",
  name: "qc_figure.png",
  kind: "image",
  previewable: false,
  source: "summary.outputs",
});
const classificationBinary = artifactRecord({
  artifact_id: "a-binary",
  name: "bold.nii.gz",
  kind: "nifti",
  previewable: false,
  source: "summary.outputs",
  suffix: ".nii.gz",
});
const classificationMat = artifactRecord({
  artifact_id: "a-mat",
  name: "motion_params.mat",
  kind: "matlab",
  previewable: false,
  source: "summary.outputs",
  suffix: ".mat",
});
const classificationMissing = artifactRecord({
  artifact_id: "a-missing",
  name: "missing_report.md",
  kind: "markdown",
  exists: false,
  previewable: false,
  source: "summary.reports",
  warnings: ["ARTIFACT_FILE_MISSING: missing_report.md"],
});
const runSummaryForArtifacts = {
  failed_nodes: [{ node_id: "motion_qc_subject", status: "FAILED" }],
};
const artifactSet = [
  classificationCsv,
  classificationBinary,
  classificationReport,
  classificationQc,
  classificationPipeline,
  classificationLog,
  classificationSummary,
  classificationJson,
  classificationImage,
  classificationMissing,
  classificationMat,
];

assert.equal(classifyArtifact(classificationSummary).category, "summary");
assert.equal(classifyArtifact(classificationPipeline).category, "pipeline");
assert.equal(classifyArtifact(classificationReport).category, "reports");
assert.equal(classifyArtifact(classificationQc).category, "qc");
assert.equal(classifyArtifact(classificationLog).category, "logs");
assert.equal(classifyArtifact(classificationCsv).category, "tables");
assert.equal(classifyArtifact(classificationJson).category, "json");
assert.equal(classifyArtifact(classificationImage).category, "images");
assert.equal(classifyArtifact(classificationBinary).category, "other_binary");
assert.equal(classifyArtifact(classificationMat).category, "other_binary");
assert.equal(isPreviewableArtifact(classificationBinary), false);
assert.equal(isPreviewableArtifact(classificationMat), false);
assert.equal(isFailedNodeArtifact(classificationLog, runSummaryForArtifacts), true);

const groupedArtifacts = groupArtifacts(artifactSet, runSummaryForArtifacts);
assertJsonEqual(groupedArtifacts.map((group) => [group.category, group.artifacts.length]), [
  ["summary", 1],
  ["pipeline", 1],
  ["reports", 2],
  ["qc", 1],
  ["logs", 1],
  ["tables", 1],
  ["json", 1],
  ["images", 1],
  ["other_binary", 2],
]);
assertJsonEqual(
  filterArtifacts(artifactSet, { category: "reports" }).map((item) => item.artifact_id).sort(),
  ["a-missing", "a-report"]
);
assertJsonEqual(
  filterArtifacts(artifactSet, { state: "missing" }).map((item) => item.artifact_id),
  ["a-missing"]
);
assertJsonEqual(
  filterArtifacts(artifactSet, { state: "warnings" }).map((item) => item.artifact_id).sort(),
  ["a-missing", "a-qc"]
);
assertJsonEqual(
  filterArtifacts(artifactSet, { state: "previewable" })
    .map((item) => item.artifact_id)
    .sort(),
  ["a-csv", "a-json", "a-log", "a-qc", "a-report", "a-summary"]
);
assertJsonEqual(
  filterArtifacts(artifactSet, { kind: "json", source: "summary.artifacts" }).map((item) => item.artifact_id),
  ["a-qc"]
);
const sortedArtifactIds = sortArtifacts(artifactSet, runSummaryForArtifacts).map((item) => item.artifact_id);
assert.equal(sortedArtifactIds[0], "a-summary");
assert.equal(sortedArtifactIds.indexOf("a-missing") < sortedArtifactIds.indexOf("a-report"), true);
assert.equal(sortedArtifactIds.indexOf("a-log") < sortedArtifactIds.indexOf("a-csv"), true);

const keyArtifactIds = getKeyArtifacts(artifactSet, runSummaryForArtifacts).map((item) => item.artifact_id);
assertJsonEqual(keyArtifactIds.slice(0, 6), [
  "a-summary",
  "a-pipeline",
  "a-missing",
  "a-report",
  "a-qc",
  "a-log",
]);
assert.equal(getKeyArtifactReason(classificationLog, runSummaryForArtifacts), "Failed-node log");
assert.equal(getKeyArtifactReason(classificationMissing, runSummaryForArtifacts), "Missing artifact to resolve");

const csvPreview = normalizeCsvPreview({
  columns: ["subject_id", "mean_fd", "status"],
  rows: [
    ["sub-01", 0.12, "PASS"],
    ["sub-02", 0.32, "WARN"],
  ],
  row_count: "2",
  displayed_rows: 2,
  truncated: false,
});
assertJsonEqual(csvPreview, {
  columns: ["subject_id", "mean_fd", "status"],
  rows: [
    ["sub-01", "0.12", "PASS"],
    ["sub-02", "0.32", "WARN"],
  ],
  row_count: 2,
  displayed_rows: 2,
  truncated: false,
  columns_truncated: false,
});
assert.equal(normalizeCsvPreview(null), null);

const backendJsonSummary = normalizeJsonPreviewSummary({
  json: null,
  json_summary: {
    type: "object",
    size: 6,
    top_level_keys: ["status", "warnings", "errors", "subjects"],
    status: "PASS",
    warnings: { count: 1, sample: ["minor motion note"] },
    errors: { count: 0, sample: [] },
    field_summaries: [
      { key: "subjects", type: "array", size: 2, sample_types: ["object"] },
      { key: "thresholds", type: "object", size: 1, keys: ["mean_fd"] },
    ],
  },
});
assert.equal(backendJsonSummary.status, "PASS");
assertJsonEqual(backendJsonSummary.top_level_keys, ["status", "warnings", "errors", "subjects"]);
assert.equal(backendJsonSummary.warnings.count, 1);
assert.equal(backendJsonSummary.field_summaries[0].type, "array");
assert.equal(backendJsonSummary.field_summaries[0].size, 2);

const fallbackJsonSummary = normalizeJsonPreviewSummary({
  json: {
    ok: true,
    warnings: ["fallback warning"],
    errors: [],
    subjects: [{ subject_id: "sub-01" }],
    thresholds: { mean_fd: 0.2 },
  },
  json_summary: null,
});
assert.equal(fallbackJsonSummary.status, true);
assertJsonEqual(fallbackJsonSummary.top_level_keys, [
  "ok",
  "warnings",
  "errors",
  "subjects",
  "thresholds",
]);
assert.equal(fallbackJsonSummary.warnings.count, 1);
assert.equal(fallbackJsonSummary.field_summaries.find((item) => item.key === "subjects").size, 1);

const markdownBlocks = markdownPreviewBlocks(
  "# QC Report\n\nAll clear.\n\n- mean FD passed\n\n```text\nsafe <b>literal</b>\n```"
);
assertJsonEqual(markdownBlocks, [
  { type: "heading", level: 1, text: "QC Report" },
  { type: "paragraph", text: "All clear." },
  { type: "list_item", text: "mean FD passed" },
  { type: "code", text: "safe <b>literal</b>" },
]);

const summaryPreview = normalizeRunSummaryPreview(
  {
    status: "FAILED",
    start_time: "2026-06-05T01:00:00Z",
    end_time: "2026-06-05T01:02:00Z",
    nodes_total: "3",
    nodes_success: 1,
    failed_nodes: [{ node_id: "motion_qc_subject", status: "FAILED" }],
    warnings: ["summary warning", ""],
    outputs: ["summary.json", "pipeline.yaml"],
    raw: {
      run_id: "run-summary",
      warnings: ["raw warning"],
      errors: ["node failed"],
    },
  },
  {
    run_id: "run-fallback",
    status: "SUCCESS",
    warnings: ["run warning"],
  }
);
assert.equal(summaryPreview.run_id, "run-summary");
assert.equal(summaryPreview.status, "FAILED");
assert.equal(summaryPreview.started_at, "2026-06-05T01:00:00Z");
assert.equal(summaryPreview.finished_at, "2026-06-05T01:02:00Z");
assert.equal(summaryPreview.nodes_total, 3);
assert.equal(summaryPreview.nodes_succeeded, 1);
assert.equal(summaryPreview.nodes_failed, 1);
assertJsonEqual(summaryPreview.outputs, { items: ["summary.json", "pipeline.yaml"] });
assertJsonEqual(summaryPreview.warnings, ["summary warning", "raw warning", "run warning"]);
assertJsonEqual(summaryPreview.failed_nodes, [{ node_id: "motion_qc_subject", status: "FAILED" }]);

const healthSummary = summarizeRunHealth(
  { status: "FAILED", warnings: ["run warning"] },
  summaryPreview,
  artifactSet
);
assert.equal(healthSummary.status, "FAILED");
assert.equal(healthSummary.nodesTotal, 3);
assert.equal(healthSummary.nodesSucceeded, 1);
assert.equal(healthSummary.nodesFailed, 1);
assert.equal(healthSummary.warningsCount >= 4, true);
assert.equal(healthSummary.errorsCount >= 1, true);
assert.equal(healthSummary.hasMissingArtifacts, true);
assert.equal(healthSummary.missingArtifactCount, 1);
assert.equal(healthSummary.hasFailedNodeLogs, true);
assert.equal(healthSummary.failedLogCount, 1);

const qcHighlights = extractQcHighlights(artifactSet);
assert.equal(qcHighlights.length >= 1, true);
const qcHighlight = qcHighlights.find((item) => item.artifactId === "a-qc");
assert.equal(qcHighlight.status, "PASS");
assert.equal(qcHighlight.passed, true);
assert.equal(qcHighlight.failed, false);
assert.equal(qcHighlight.subjectId, "sub-01");
assert.equal(qcHighlight.nodeId, "motion_qc_subject");
assertJsonEqual(qcHighlight.metrics, [{ label: "mean_fd", value: "0.12" }]);
assert.equal(qcHighlight.warnings.includes("minor motion note"), true);
assert.equal(qcHighlights.some((item) => item.artifactId === "a-binary"), false);

const failedNodeHighlights = extractFailedNodeHighlights(summaryPreview, artifactSet);
const failedNode = failedNodeHighlights.find((item) => item.nodeId === "motion_qc_subject");
assert.equal(failedNode.status, "FAILED");
assert.equal(failedNode.artifactId, "a-log");
assert.equal(failedNode.errorExcerpt.includes("motion failed"), true);

const provenanceRows = buildArtifactProvenanceRows(artifactSet);
const qcProvenance = provenanceRows.find((item) => item.artifactId === "a-qc");
assert.equal(qcProvenance.category, "qc");
assert.equal(qcProvenance.source, "summary.artifacts");
assert.equal(qcProvenance.state, "warnings");
const missingProvenance = provenanceRows.find((item) => item.artifactId === "a-missing");
assert.equal(missingProvenance.exists, false);
assert.equal(missingProvenance.state, "missing");
const binaryProvenance = provenanceRows.find((item) => item.artifactId === "a-binary");
assert.equal(binaryProvenance.category, "other_binary");
assert.equal(binaryProvenance.state, "metadata_only");
assert.equal(extractQcHighlights([classificationBinary]).length, 0);
assert.equal(extractFailedNodeHighlights(null, [classificationBinary]).length, 0);

assert.equal(
  missingSummaryWarning("D:\\projects\\demo\\work\\pipeline_runs\\run-a\\summary.json"),
  "Summary preview is not available for D:\\projects\\demo\\work\\pipeline_runs\\run-a\\summary.json."
);
assert.equal(
  missingSummaryWarning(null),
  "Summary preview is not available because this run has no summary_path."
);
assertJsonEqual(mergeSummaryWarnings({ warnings: ["a", "b"] }, { warnings: ["b", "c"] }), [
  "a",
  "b",
  "c",
]);

const compact = compactRawSummary({ payload: "x".repeat(200) }, 60);
assert.equal(compact.raw_truncated, true);
assert.equal(compact.raw.truncated, true);
assert.equal(compact.raw.top_level_keys[0], "payload");

assert.equal(getRunStatusToneKey("SUCCESS"), "success");
assert.equal(getRunStatusToneKey("completed"), "success");
assert.equal(getRunStatusToneKey("FAILED"), "danger");
assert.equal(getRunStatusToneKey("blocked"), "danger");
assert.equal(getRunStatusToneKey("RUNNING"), "active");
assert.equal(getRunStatusToneKey("submitted"), "active");
assert.equal(getRunStatusToneKey("unknown"), "neutral");

// ── deriveRunHealth smoke ────────────────────────────────────────────────
const runStatusSourcePath = path.join(__dirname, "..", "src", "lib", "runStatus.ts");
const runStatusSource = fs.readFileSync(runStatusSourcePath, "utf8");
const runStatusTranspiled = ts.transpileModule(runStatusSource, {
  fileName: runStatusSourcePath,
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});
const runStatusModule = { exports: {} };
vm.runInNewContext(
  runStatusTranspiled.outputText,
  { exports: runStatusModule.exports, module: runStatusModule, require },
  { filename: runStatusSourcePath },
);
const { deriveRunHealth } = runStatusModule.exports;

// null run
const h0 = deriveRunHealth(null, null);
assert.equal(h0.level, "unknown");

// failed status
const h1 = deriveRunHealth({ status: "FAILED", warnings: [] }, null);
assert.equal(h1.level, "failed");

// failed nodes in summary
const h2 = deriveRunHealth(
  { status: "SUCCESS", warnings: [] },
  { nodes_failed: 2, warnings: [] },
);
assert.equal(h2.level, "failed");

// warning from run
const h3 = deriveRunHealth(
  { status: "SUCCESS", warnings: ["stale pipeline"] },
  null,
);
assert.equal(h3.level, "warning");

// missing summary
const h4 = deriveRunHealth(
  { status: "RUNNING", warnings: [] },
  null,
);
assert.equal(h4.level, "warning");
assert.ok(h4.explanation.includes("No summary preview"));

// ok — submitted
const h5 = deriveRunHealth(
  { status: "SUBMITTED", warnings: [] },
  { nodes_total: 3, nodes_succeeded: 3, nodes_failed: 0, nodes_skipped: 0, warnings: [] },
);
assert.equal(h5.level, "ok");

// ok — completed
const h6 = deriveRunHealth(
  { status: "COMPLETED", warnings: [] },
  { nodes_total: 1, nodes_succeeded: 1, nodes_failed: 0, nodes_skipped: 0, warnings: [] },
);
assert.equal(h6.level, "ok");

// unknown
const h7 = deriveRunHealth(
  { status: "QUEUED", warnings: [] },
  { nodes_total: 0, nodes_succeeded: 0, nodes_failed: 0, nodes_skipped: 0, warnings: [] },
);
assert.equal(h7.level, "unknown");

// ── describeExecuteReviewedStatus smoke ─────────────────────────────────
const executedStatusSourcePath = path.join(__dirname, "..", "src", "lib", "executeReviewedStatus.ts");
const executedStatusSource = fs.readFileSync(executedStatusSourcePath, "utf8");
const executedStatusTranspiled = ts.transpileModule(executedStatusSource, {
  fileName: executedStatusSourcePath,
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});
const executedStatusModule = { exports: {} };
vm.runInNewContext(
  executedStatusTranspiled.outputText,
  { exports: executedStatusModule.exports, module: executedStatusModule, require },
  { filename: executedStatusSourcePath },
);
const { describeExecuteReviewedStatus } = executedStatusModule.exports;

// DRY_RUN_OK
const s0 = describeExecuteReviewedStatus("DRY_RUN_OK");
assert.equal(s0.severity, "success");
assert.equal(s0.canRetryDryRun, true);
assert.equal(s0.canAttemptExecute, true);

// AUDIT_REQUIRED
const s1 = describeExecuteReviewedStatus("AUDIT_REQUIRED");
assert.equal(s1.severity, "error");
assert.equal(s1.canAttemptExecute, false);

// APPROVAL_GATE_BLOCKED
const s2 = describeExecuteReviewedStatus("APPROVAL_GATE_BLOCKED");
assert.equal(s2.severity, "warning");
assert.equal(s2.canAttemptExecute, false);

// EXECUTION_POLICY_BLOCKED
const s3 = describeExecuteReviewedStatus("EXECUTION_POLICY_BLOCKED");
assert.equal(s3.severity, "warning");
assert.ok(s3.title.length > 0);

// EXECUTION_FAILED
const s4 = describeExecuteReviewedStatus("EXECUTION_FAILED");
assert.equal(s4.severity, "error");
assert.equal(s4.canAttemptExecute, true);

// Unknown status fallback
const s5 = describeExecuteReviewedStatus("SOME_NEW_STATUS");
assert.equal(s5.severity, "info");
assert.ok(s5.title.includes("SOME_NEW_STATUS"));
assert.equal(s5.canRetryDryRun, true);

// Undefined / empty
const s6 = describeExecuteReviewedStatus(undefined);
assert.equal(s6.severity, "info");
assert.equal(s6.status, "(empty)");

// ── buildPresetPlanDraft smoke ──────────────────────────────────────────
const handoffSourcePath = path.join(__dirname, "..", "src", "lib", "presetPlanHandoff.ts");
const handoffSource = fs.readFileSync(handoffSourcePath, "utf8");
const handoffTranspiled = ts.transpileModule(handoffSource, {
  fileName: handoffSourcePath,
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const handoffModule = { exports: {} };
vm.runInNewContext(
  handoffTranspiled.outputText,
  { exports: handoffModule.exports, module: handoffModule, require },
  { filename: handoffSourcePath },
);
const { buildPresetPlanDraft } = handoffModule.exports;

const draft = buildPresetPlanDraft("proj-123", {
  ok: true, preset_id: "test_preset", project_id: "proj-123",
  plan: { pipeline_id: "t", nodes: [] },
  validation: { ok: true }, warnings: ["w1"],
  errors: [], next_actions: ["action1"], safety_flags: {},
});
assert.equal(draft.preset_id, "test_preset");
assert.equal(draft.project_id, "proj-123");
assert.equal(draft.source, "pipeline_preset");
assert.equal(draft.goal, "rs-fMRI preprocessing MVP preset");
assert.deepEqual(draft.plan, { pipeline_id: "t", nodes: [] });
assert.equal(draft.warnings.length, 1);
assert.equal(draft.next_actions.length, 1);

// defaults missing fields to empty arrays
const draft2 = buildPresetPlanDraft("p2", {
  ok: true, preset_id: "tp", project_id: "p2",
  plan: {}, validation: {}, warnings: undefined,
  errors: [], next_actions: undefined, safety_flags: {},
});
assert.equal(draft2.warnings.length, 0);
assert.equal(draft2.next_actions.length, 0);

// ── detectExternalToolNodes smoke ────────────────────────────────────────
const extApprovalSourcePath = path.join(__dirname, "..", "src", "lib", "externalToolApproval.ts");
const extApprovalSource = fs.readFileSync(extApprovalSourcePath, "utf8");
const extApprovalTranspiled = ts.transpileModule(extApprovalSource, {
  fileName: extApprovalSourcePath,
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const extApprovalModule = { exports: {} };
vm.runInNewContext(
  extApprovalTranspiled.outputText,
  { exports: extApprovalModule.exports, module: extApprovalModule, require },
  { filename: extApprovalSourcePath },
);
const { detectExternalToolNodes, isExternalToolApprovalComplete } = extApprovalModule.exports;

const r1 = detectExternalToolNodes(null);
assert.equal(r1.required, false);

const r2 = detectExternalToolNodes({ nodes: [{ id: "spm_realign_subject", backend: "matlab-spm" }] });
assert.equal(r2.required, true);
assert.ok(r2.nodeIds.includes("spm_realign_subject"));

const r3 = detectExternalToolNodes({ nodes: [{ id: "contract_smoke", backend: "python" }] });
assert.equal(r3.required, false);

const r4 = detectExternalToolNodes({ nodes: [{ id: "dpabi_smooth", backend: "dpabi" }] });
assert.equal(r4.required, true);
assert.ok(r4.backendIds.includes("dpabi"));

const r5 = detectExternalToolNodes(undefined);
assert.equal(r5.required, false);

const r6 = detectExternalToolNodes({});
assert.equal(r6.required, false);

// ── isExternalToolApprovalComplete smoke ──────────────────────────────────
const req = { required: true, nodeIds: ["spm_realign_subject"], backendIds: ["matlab-spm"], reasons: [] };
const fullState = {
  externalToolAcknowledgement: true, rawdataReadOnlyConfirmed: true,
  outputDirectoryConfirmed: true, riskAcknowledgement: true,
  subjectScopeConfirmed: true, overwritePolicy: "fail_if_exists",
};
const missingOne = { ...fullState, riskAcknowledgement: false };
const badPolicy = { ...fullState, overwritePolicy: "silent_overwrite" };
const noReq = { required: false, nodeIds: [], backendIds: [], reasons: [] };

assert.equal(isExternalToolApprovalComplete(noReq, fullState), true);
assert.equal(isExternalToolApprovalComplete(req, fullState), true);
assert.equal(isExternalToolApprovalComplete(req, missingOne), false);
assert.equal(isExternalToolApprovalComplete(req, badPolicy), false);
assert.equal(isExternalToolApprovalComplete(noReq, missingOne), true);

console.log("ProjectRunsPanel smoke passed");
