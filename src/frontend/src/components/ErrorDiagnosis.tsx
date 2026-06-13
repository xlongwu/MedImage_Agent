import { useState } from "react";
import { diagnoseRun, retryDryRun, retryExecute, getRetryRun } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
  defaultRunId?: string;
};

export function ErrorDiagnosis({
  baseUrl,
  defaultRunId = "run_subject_preprocess_001"
}: Props) {
  const [runId, setRunId] = useState(defaultRunId);
  const [diagnosis, setDiagnosis] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  const [dryRunResult, setDryRunResult] = useState<Record<string, unknown> | null>(null);
  const [retryResult, setRetryResult] = useState<Record<string, unknown> | null>(null);
  const [retryStatus, setRetryStatus] = useState("IDLE");
  const [retryError, setRetryError] = useState("");
  const [retryRunId, setRetryRunId] = useState("");

  async function handleDiagnose() {
    setError("");
    setStatus("LOADING");
    setDiagnosis(null);
    setDryRunResult(null);
    setRetryResult(null);

    try {
      const result = await diagnoseRun(baseUrl, runId);
      setDiagnosis(result);
      setStatus("DONE");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleDryRun() {
    setRetryError("");
    setRetryStatus("LOADING");
    setDryRunResult(null);
    setRetryResult(null);

    try {
      const result = await retryDryRun(baseUrl, runId, retryRunId || undefined);
      setDryRunResult(result);
      setRetryStatus("DONE");
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : String(err));
      setRetryStatus("ERROR");
    }
  }

  async function handleExecute() {
    setRetryError("");
    setRetryStatus("LOADING");
    setRetryResult(null);

    try {
      const result = await retryExecute(
        baseUrl,
        runId,
        "examples/project_config_dataset.yaml",
        retryRunId || undefined,
        true
      );
      setRetryResult(result);
      setRetryStatus("DONE");
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : String(err));
      setRetryStatus("ERROR");
    }
  }

  const issues = (diagnosis?.issues as Array<Record<string, unknown>>) || [];
  const issuesTotal = (diagnosis?.issues_total as number) || 0;
  const pipelineStatus = (diagnosis?.status as string) || "UNKNOWN";

  return (
    <div>
      <div className="formGrid">
        <label>
          Run ID
          <input
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={handleDiagnose} disabled={status === "LOADING"}>
          {status === "LOADING" ? "诊断中..." : "运行错误诊断"}
        </button>
        {diagnosis ? <StatusBadge status={pipelineStatus} /> : null}
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {diagnosis ? (
        <div>
          <h3>诊断摘要</h3>
          <div className="jsonBlock">
            <div>Run ID: {String(diagnosis.run_id)}</div>
            <div>Pipeline Status: {pipelineStatus}</div>
            <div>Issues Total: {issuesTotal}</div>
          </div>

          <h3>Retry Plan 控制</h3>
          <div className="formGrid">
            <label>
              Retry Run ID (可选)
              <input
                value={retryRunId}
                onChange={(e) => setRetryRunId(e.target.value)}
                placeholder="例如: retry_run_subject_preprocess_001_001"
              />
            </label>
          </div>
          <div className="row">
            <button onClick={handleDryRun} disabled={retryStatus === "LOADING"}>
              {retryStatus === "LOADING" && !dryRunResult ? "Dry Run 中..." : "Dry Run"}
            </button>
            <button onClick={handleExecute} disabled={retryStatus === "LOADING"}>
              {retryStatus === "LOADING" && !retryResult ? "执行中..." : "批准并执行 Retry"}
            </button>
          </div>
          {retryError ? <div className="errorBox">{retryError}</div> : null}

          {dryRunResult ? (
            <div>
              <h4>Dry Run 结果</h4>
              <div className="jsonBlock">
                <div>Mode: {String(dryRunResult.mode)}</div>
                <div>Retry Run ID: {String(dryRunResult.retry_run_id)}</div>
                <div>Steps Total: {String(dryRunResult.steps_total)}</div>
                <div>Steps Executable: {String(dryRunResult.steps_executable)}</div>
                <div>Steps Skipped: {String(dryRunResult.steps_skipped)}</div>
              </div>
              {(dryRunResult.steps as Array<Record<string, unknown>>)?.length ? (
                <div className="issueList">
                  {(dryRunResult.steps as Array<Record<string, unknown>>).map((step, index) => (
                    <div key={index} className="issueCard">
                      <div className="issueHeader">
                        <strong>{String(step.step_id)}</strong>
                        <span>{step.executable ? "✅ 可执行" : "⏭️ 跳过"}</span>
                      </div>
                      <div className="issueMeta">
                        <span>Action: {String(step.action)}</span>
                        <span>Node: {String(step.node)}</span>
                        <span>Subject: {String(step.subject_id) || "N/A"}</span>
                      </div>
                      <div className="issueMessage">{String(step.reason)}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {retryResult ? (
            <div>
              <h4>Retry 执行结果</h4>
              <div className="jsonBlock">
                <div>Mode: {String(retryResult.mode)}</div>
                <div>Retry Run ID: {String(retryResult.retry_run_id)}</div>
                <div>Approved: {String(retryResult.approved)}</div>
                <div>Steps Total: {String(retryResult.steps_total)}</div>
                <div>Steps Executed: {String(retryResult.steps_executed)}</div>
                <div>Steps Failed: {String(retryResult.steps_failed)}</div>
                <div>Steps Skipped: {String(retryResult.steps_skipped)}</div>
              </div>
              <JsonBlock value={retryResult} emptyText="无执行数据" />
            </div>
          ) : null}

          <h3>问题列表</h3>
          {issues.length > 0 ? (
            <div className="issueList">
              {issues.map((issue, index) => (
                <div key={index} className="issueCard">
                  <div className="issueHeader">
                    <strong>{(issue.issue_id as string) || `Issue ${index + 1}`}</strong>
                    <StatusBadge status={(issue.status as string) || "UNKNOWN"} />
                  </div>
                  <div className="issueMeta">
                    <span>Scope: {(issue.scope as string) || "N/A"}</span>
                    <span>Subject: {(issue.subject_id as string) || "N/A"}</span>
                    <span>Node: {(issue.node as string) || "N/A"}</span>
                    <span>Category: {(issue.category as string) || "UNKNOWN"}</span>
                  </div>
                  <div className="issueMessage">
                    {(issue.message as string) || "No message"}
                  </div>
                  {(issue.matched_error_ids as string[])?.length ? (
                    <div className="issueMatches">
                      <strong>匹配的错误模式:</strong>
                      <ul>
                        {(issue.matched_error_ids as string[]).map((id, i) => (
                          <li key={i}>{id}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {(issue.suggested_fixes as string[])?.length ? (
                    <div className="issueFixes">
                      <strong>建议修复:</strong>
                      <ul>
                        {(issue.suggested_fixes as string[]).map((fix, i) => (
                          <li key={i}>{fix}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <div className="issueRetry">
                    <strong>重试建议:</strong>{" "}
                    <code>{(issue.retry_recommendation as string) || "MANUAL_REVIEW"}</code>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">未发现问题</div>
          )}

          <h3>完整诊断 JSON</h3>
          <JsonBlock value={diagnosis} emptyText="无诊断数据" />
        </div>
      ) : null}
    </div>
  );
}
