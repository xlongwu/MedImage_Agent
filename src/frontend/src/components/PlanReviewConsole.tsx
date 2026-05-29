import React, { useState } from "react";
import { DEFAULT_API_BASE, fetchToolCatalog, generatePlanFromGoal } from "../api";

type PlanData = Record<string, unknown> | null;

export default function PlanReviewConsole() {
  const baseUrl = DEFAULT_API_BASE;
  const [goal, setGoal] = useState("");
  const [provider, setProvider] = useState("mock");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlanData>(null);
  const [error, setError] = useState("");
  const [catalogCount, setCatalogCount] = useState<number | null>(null);

  // Load catalog count on mount
  React.useEffect(() => {
    fetchToolCatalog(baseUrl)
      .then((data) => setCatalogCount(data.count))
      .catch(() => setCatalogCount(null));
  }, [baseUrl]);

  async function handleGenerate() {
    setError("");
    setResult(null);
    if (!goal.trim()) {
      setError("Please enter a goal.");
      return;
    }
    setLoading(true);
    try {
      const data = await generatePlanFromGoal(baseUrl, {
        goal: goal.trim(),
        provider,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  const validation = (result?.validation ?? {}) as Record<string, unknown>;
  const riskSummary = (validation?.risk_summary ?? {}) as Record<string, unknown>;
  const plan = (result?.plan ?? {}) as Record<string, unknown>;
  const nodes = (plan?.nodes ?? []) as Array<Record<string, unknown>>;
  const errors = (result?.errors ?? []) as string[];
  const warnings = (result?.warnings ?? []) as string[];
  const valErrors = (validation?.errors ?? []) as Array<Record<string, unknown>>;
  const valWarnings = (validation?.warnings ?? []) as Array<Record<string, unknown>>;
  const approvalNodes = (validation?.approval_required_nodes ?? []) as string[];
  const highRiskNodes = (validation?.high_risk_nodes ?? []) as string[];
  const unknownNodes = (validation?.unknown_nodes ?? []) as string[];
  const topoOrder = (validation?.topological_order ?? []) as string[];

  return (
    <div style={{ padding: 20, maxWidth: 960, margin: "0 auto" }}>
      <h2>Plan Review Console</h2>

      {/* ── Input ── */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontWeight: 600, display: "block", marginBottom: 4 }}>
          Goal
        </label>
        <input
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. 对 rs-fMRI 数据做 realign 和 motion QC"
          style={{ width: "100%", padding: "8px 12px", borderRadius: 4, border: "1px solid #ccc", fontSize: 14 }}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
        />
      </div>

      <div style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "center" }}>
        <label style={{ fontWeight: 600 }}>Provider:</label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 4, border: "1px solid #ccc" }}
        >
          <option value="mock">mock</option>
          <option value="rule_based">rule_based</option>
          <option value="openai_compatible">openai_compatible</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={loading}
          style={{
            padding: "8px 20px", background: "#1976d2", color: "#fff",
            border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600,
          }}
        >
          {loading ? "Generating..." : "Generate Plan"}
        </button>
        {catalogCount !== null && (
          <span style={{ fontSize: 13, color: "#777" }}>
            Tool Catalog: {catalogCount} tools
          </span>
        )}
      </div>

      {error && (
        <div style={{ padding: 12, background: "#ffebee", borderRadius: 4, marginBottom: 16, color: "#c62828", fontSize: 14 }}>
          {error}
        </div>
      )}

      {/* ── Result ── */}
      {result && (
        <>
          {/* Status */}
          <div style={{
            padding: 12, borderRadius: 4, marginBottom: 16, fontSize: 14,
            background: result.ok ? "#e8f5e9" : "#fff3e0",
            color: result.ok ? "#2e7d32" : "#e65100",
          }}>
            <strong>{result.ok ? "✓ Plan generated and validated" : "✗ Plan generation failed"}</strong>
            {result.provider && <span> — provider: {String(result.provider)}</span>}
          </div>

          {/* Errors / Warnings */}
          {(errors.length > 0 || warnings.length > 0) && (
            <div style={{ marginBottom: 16 }}>
              {errors.map((e, i) => (
                <div key={`err-${i}`} style={{ color: "#c62828", fontSize: 13, marginBottom: 2 }}>❌ {e}</div>
              ))}
              {warnings.map((w, i) => (
                <div key={`warn-${i}`} style={{ color: "#e65100", fontSize: 13, marginBottom: 2 }}>⚠️ {w}</div>
              ))}
            </div>
          )}

          {/* Risk Summary */}
          <div style={{ marginBottom: 16, padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
            <h4 style={{ margin: "0 0 8px 0" }}>Risk Summary</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 24px", fontSize: 13 }}>
              <span>Total nodes: <b>{String(riskSummary.nodes_total ?? "?")}</b></span>
              <span>Requires approval: <b style={{ color: riskSummary.requires_approval ? "#c62828" : "#2e7d32" }}>{String(riskSummary.requires_approval ?? "?")}</b></span>
              <span>Approval required count: <b>{String(riskSummary.approval_required_count ?? "?")}</b></span>
              <span>High risk count: <b style={{ color: (Number(riskSummary.high_risk_count) || 0) > 0 ? "#c62828" : "#333" }}>{String(riskSummary.high_risk_count ?? "?")}</b></span>
              <span>Manual required: <b>{String(riskSummary.manual_required ?? "?")}</b></span>
              <span>Unknown nodes: <b>{String(riskSummary.unknown_nodes_count ?? "?")}</b></span>
              <span>Uncataloged metadata: <b>{String(riskSummary.has_uncataloged_metadata ?? "?")}</b></span>
            </div>
          </div>

          {/* Validation detail */}
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ margin: "0 0 8px 0" }}>Validation</h4>
            {valErrors.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                {valErrors.map((e, i) => (
                  <div key={`ve-${i}`} style={{ color: "#c62828", fontSize: 13 }}>
                    ❌ [{String(e.code ?? "?")}] {String(e.message ?? "")}
                  </div>
                ))}
              </div>
            )}
            {valWarnings.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                {valWarnings.map((w, i) => (
                  <div key={`vw-${i}`} style={{ color: "#e65100", fontSize: 13 }}>
                    ⚠️ [{String(w.code ?? "?")}] {String(w.message ?? "")}
                  </div>
                ))}
              </div>
            )}
            {approvalNodes.length > 0 && (
              <div style={{ fontSize: 13, color: "#c62828", marginBottom: 4 }}>
                🔒 Approval required: {approvalNodes.join(", ")}
              </div>
            )}
            {highRiskNodes.length > 0 && (
              <div style={{ fontSize: 13, color: "#e65100", marginBottom: 4 }}>
                ⚡ High risk: {highRiskNodes.join(", ")}
              </div>
            )}
            {unknownNodes.length > 0 && (
              <div style={{ fontSize: 13, color: "#c62828", marginBottom: 4 }}>
                ❓ Unknown: {unknownNodes.join(", ")}
              </div>
            )}
            {topoOrder.length > 0 && (
              <div style={{ fontSize: 13, color: "#555", marginBottom: 4 }}>
                → Topological order: {topoOrder.join(" → ")}
              </div>
            )}
          </div>

          {/* Nodes */}
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ margin: "0 0 8px 0" }}>
              Candidate Plan: {String(plan.pipeline_id ?? "?")} ({nodes.length} nodes)
            </h4>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#eee", textAlign: "left" }}>
                  <th style={{ padding: "4px 8px", border: "1px solid #ddd" }}>#</th>
                  <th style={{ padding: "4px 8px", border: "1px solid #ddd" }}>Node ID</th>
                  <th style={{ padding: "4px 8px", border: "1px solid #ddd" }}>Backend</th>
                  <th style={{ padding: "4px 8px", border: "1px solid #ddd" }}>Depends On</th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((node, i) => (
                  <tr key={i}>
                    <td style={{ padding: "4px 8px", border: "1px solid #ddd" }}>{i + 1}</td>
                    <td style={{ padding: "4px 8px", border: "1px solid #ddd" }}>{String(node.id ?? "?")}</td>
                    <td style={{ padding: "4px 8px", border: "1px solid #ddd" }}>{String(node.backend ?? "?")}</td>
                    <td style={{ padding: "4px 8px", border: "1px solid #ddd" }}>
                      {(Array.isArray(node.depends_on) ? node.depends_on as string[] : []).join(", ") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
