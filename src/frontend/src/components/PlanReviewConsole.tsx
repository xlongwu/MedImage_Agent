import React, { useState } from "react";
import { DEFAULT_API_BASE, fetchToolCatalog, generatePlanFromGoal, validatePlan } from "../api";

type PlanData = Record<string, unknown> | null;

type CatalogItem = {
  id: string; name: string; backend: string; parallel_level: string;
  description: string; requires_approval: boolean; manual_required: boolean;
  risk_level: string; inputs: string[]; outputs: string[]; tags: string[];
};

export default function PlanReviewConsole() {
  const baseUrl = DEFAULT_API_BASE;
  const [goal, setGoal] = useState("");
  const [provider, setProvider] = useState("mock");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlanData>(null);
  const [error, setError] = useState("");

  // ── Tool Catalog ──
  const [catalogMap, setCatalogMap] = useState<Record<string, CatalogItem>>({});
  const [catalogError, setCatalogError] = useState("");

  // ── Edit + re-validate ──
  const [planJson, setPlanJson] = useState("");
  const [validateLoading, setValidateLoading] = useState(false);
  const [jsonError, setJsonError] = useState("");
  const [reValidation, setReValidation] = useState<Record<string, unknown> | null>(null);

  // ── Node detail panel ──
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Load full catalog on mount
  React.useEffect(() => {
    fetchToolCatalog(baseUrl)
      .then((data) => {
        const map: Record<string, CatalogItem> = {};
        const items = (data?.items ?? []) as Array<Record<string, unknown>>;
        for (const item of items) {
          const id = String(item.id ?? "");
          map[id] = {
            id, name: String(item.name ?? id), backend: String(item.backend ?? "?"),
            parallel_level: String(item.parallel_level ?? "?"),
            description: String(item.description ?? ""),
            requires_approval: Boolean(item.requires_approval),
            manual_required: Boolean(item.manual_required),
            risk_level: String(item.risk_level ?? "?"),
            inputs: Array.isArray(item.inputs) ? item.inputs as string[] : [],
            outputs: Array.isArray(item.outputs) ? item.outputs as string[] : [],
            tags: Array.isArray(item.tags) ? item.tags as string[] : [],
          };
        }
        setCatalogMap(map);
        setCatalogError("");
      })
      .catch(() => setCatalogError("Tool Catalog unavailable — node metadata limited."));
  }, [baseUrl]);

  async function handleGenerate() {
    setError(""); setResult(null); setPlanJson("");
    setReValidation(null); setJsonError(""); setSelectedNodeId(null);
    if (!goal.trim()) { setError("Please enter a goal."); return; }
    setLoading(true);
    try {
      const data = await generatePlanFromGoal(baseUrl, { goal: goal.trim(), provider });
      setResult(data);
      const plan = data?.plan;
      if (plan && typeof plan === "object") setPlanJson(JSON.stringify(plan, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }

  async function handleRevalidate() {
    setJsonError(""); setReValidation(null);
    let plan: Record<string, unknown>;
    try { plan = JSON.parse(planJson); }
    catch (e) { setJsonError(e instanceof Error ? e.message : String(e)); return; }
    setValidateLoading(true);
    try { setReValidation(await validatePlan(baseUrl, plan) as Record<string, unknown>); }
    catch (e) { setJsonError(e instanceof Error ? e.message : String(e)); }
    finally { setValidateLoading(false); }
  }

  // ── Derived data ──
  const validation = (reValidation ?? result?.validation ?? {}) as Record<string, unknown>;
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
  const reValidated = reValidation !== null;

  const selectedCatalog = selectedNodeId ? catalogMap[selectedNodeId] : null;

  // Compute summary chips
  const highRiskCount = highRiskNodes.length;
  const approvalCount = approvalNodes.length;
  const unknownMetaCount = nodes.filter(n => {
    const id = String(n.id ?? "");
    return id && !catalogMap[id];
  }).length;
  const catalogCount = Object.keys(catalogMap).length;

  function riskBadge(level: string) {
    const colors: Record<string, string> = { high: "#c62828", medium: "#e65100", low: "#2e7d32", unknown: "#999" };
    return <span style={{ color: colors[level] || "#999", fontWeight: 700, fontSize: 12 }}>{level.toUpperCase()}</span>;
  }

  return (
    <div style={{ padding: 20, maxWidth: 1020, margin: "0 auto" }}>
      <h2>Plan Review Console</h2>

      {/* ── Input ── */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontWeight: 600, display: "block", marginBottom: 4 }}>Goal</label>
        <input type="text" value={goal} onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. 对 rs-fMRI 数据做 realign 和 motion QC"
          style={{ width: "100%", padding: "8px 12px", borderRadius: 4, border: "1px solid #ccc", fontSize: 14 }}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()} />
      </div>

      <div style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ fontWeight: 600 }}>Provider:</label>
        <select value={provider} onChange={(e) => setProvider(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 4, border: "1px solid #ccc" }}>
          <option value="mock">mock</option>
          <option value="rule_based">rule_based</option>
          <option value="openai_compatible">openai_compatible</option>
        </select>
        <button onClick={handleGenerate} disabled={loading}
          style={{ padding: "8px 20px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
          {loading ? "Generating..." : "Generate Plan"}
        </button>
        {/* Summary chips */}
        {result && (
          <>
            <span style={chipStyle("#e3f2fd", "#1565c0")}>📋 {nodes.length} nodes</span>
            {catalogCount > 0 && <span style={chipStyle("#e8f5e9", "#2e7d32")}>📦 {catalogCount} tools</span>}
            {highRiskCount > 0 && <span style={chipStyle("#ffebee", "#c62828")}>⚡ {highRiskCount} high risk</span>}
            {approvalCount > 0 && <span style={chipStyle("#fff3e0", "#e65100")}>🔒 {approvalCount} approval</span>}
            {unknownMetaCount > 0 && <span style={chipStyle("#f3e5f5", "#7b1fa2")}>❓ {unknownMetaCount} unknown meta</span>}
          </>
        )}
      </div>

      {catalogError && <div style={{ padding: 8, background: "#fff3e0", borderRadius: 4, marginBottom: 12, fontSize: 13, color: "#e65100" }}>⚠️ {catalogError}</div>}

      {error && <div style={{ padding: 12, background: "#ffebee", borderRadius: 4, marginBottom: 16, color: "#c62828", fontSize: 14 }}>{error}</div>}

      {/* ── Plan JSON Editor ── */}
      {result && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <h4 style={{ margin: 0 }}>Candidate Plan JSON</h4>
            <button onClick={handleRevalidate} disabled={validateLoading}
              style={{ padding: "6px 14px", background: "#4caf50", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 13 }}>
              {validateLoading ? "Validating..." : "Re-validate"}
            </button>
            {reValidated && <span style={{ fontSize: 12, color: "#777" }}>(using re-validation result)</span>}
          </div>
          {jsonError && <div style={{ padding: 8, background: "#ffebee", borderRadius: 4, marginBottom: 8, color: "#c62828", fontSize: 13 }}>JSON Parse Error: {jsonError}</div>}
          <textarea value={planJson}
            onChange={(e) => { setPlanJson(e.target.value); setReValidation(null); setJsonError(""); }}
            rows={14}
            style={{ width: "100%", fontFamily: "monospace", fontSize: 12, padding: 8, borderRadius: 4, border: "1px solid #ccc" }}
            spellCheck={false} />
        </div>
      )}

      {/* ── Result ── */}
      {result && (
        <div style={{ display: "flex", gap: 16 }}>
          {/* Left: plan table + validation */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Status */}
            <div style={{ padding: 12, borderRadius: 4, marginBottom: 12, fontSize: 14,
              background: result.ok ? "#e8f5e9" : "#fff3e0", color: result.ok ? "#2e7d32" : "#e65100" }}>
              <strong>{result.ok ? "✓ Plan generated and validated" : "✗ Plan generation failed"}</strong>
              {result.provider && <span> — provider: {String(result.provider)}</span>}
            </div>

            {(errors.length > 0 || warnings.length > 0) && (
              <div style={{ marginBottom: 12 }}>
                {errors.map((e, i) => <div key={`e-${i}`} style={{ color: "#c62828", fontSize: 13 }}>❌ {e}</div>)}
                {warnings.map((w, i) => <div key={`w-${i}`} style={{ color: "#e65100", fontSize: 13 }}>⚠️ {w}</div>)}
              </div>
            )}

            {/* Risk Summary */}
            <div style={{ marginBottom: 12, padding: 10, background: "#f5f5f5", borderRadius: 4 }}>
              <h4 style={{ margin: "0 0 6px 0", fontSize: 14 }}>Risk Summary{reValidated ? " (re-validated)" : ""}</h4>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "3px 16px", fontSize: 12 }}>
                <span>Total nodes: <b>{String(riskSummary.nodes_total ?? "?")}</b></span>
                <span>Requires approval: <b style={{ color: riskSummary.requires_approval ? "#c62828" : "#2e7d32" }}>{String(riskSummary.requires_approval ?? "?")}</b></span>
                <span>Approval count: <b>{String(riskSummary.approval_required_count ?? "?")}</b></span>
                <span>High risk: <b style={{ color: (Number(riskSummary.high_risk_count) || 0) > 0 ? "#c62828" : "#333" }}>{String(riskSummary.high_risk_count ?? "?")}</b></span>
                <span>Manual required: <b>{String(riskSummary.manual_required ?? "?")}</b></span>
                <span>Unknown nodes: <b>{String(riskSummary.unknown_nodes_count ?? "?")}</b></span>
              </div>
              <div style={{ marginTop: 6, fontSize: 11, color: "#777", lineHeight: 1.6 }}>
                <div>🔴 <b>High risk</b> — requires careful manual review before execution</div>
                <div>🟠 <b>Requires approval</b> — must pass approval gate before pipeline runs</div>
                <div>🟣 <b>Uncataloged</b> — metadata not yet complete; treat as unknown risk</div>
              </div>
            </div>

            {/* Validation */}
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: "0 0 6px 0", fontSize: 14 }}>Validation{reValidated ? " (re-validated)" : ""}</h4>
              {valErrors.length > 0 && valErrors.map((e, i) => (
                <div key={`ve-${i}`} style={{ color: "#c62828", fontSize: 12 }}>❌ [{String(e.code ?? "?")}] {String(e.message ?? "")}</div>))}
              {valWarnings.length > 0 && valWarnings.map((w, i) => (
                <div key={`vw-${i}`} style={{ color: "#e65100", fontSize: 12 }}>⚠️ [{String(w.code ?? "?")}] {String(w.message ?? "")}</div>))}
              {approvalNodes.length > 0 && <div style={{ fontSize: 12, color: "#c62828" }}>🔒 Approval required: {approvalNodes.join(", ")}</div>}
              {highRiskNodes.length > 0 && <div style={{ fontSize: 12, color: "#e65100" }}>⚡ High risk: {highRiskNodes.join(", ")}</div>}
              {unknownNodes.length > 0 && <div style={{ fontSize: 12, color: "#7b1fa2" }}>❓ Unknown: {unknownNodes.join(", ")}</div>}
              {topoOrder.length > 0 && <div style={{ fontSize: 12, color: "#555" }}>→ {topoOrder.join(" → ")}</div>}
            </div>

            {/* Nodes table */}
            <h4 style={{ margin: "0 0 6px 0", fontSize: 14 }}>Candidate Plan: {String(plan.pipeline_id ?? "?")} ({nodes.length} nodes)</h4>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#eee", textAlign: "left" }}>
                  <th style={{ padding: "3px 6px", border: "1px solid #ddd" }}>#</th>
                  <th style={{ padding: "3px 6px", border: "1px solid #ddd" }}>Node ID</th>
                  <th style={{ padding: "3px 6px", border: "1px solid #ddd" }}>Name</th>
                  <th style={{ padding: "3px 6px", border: "1px solid #ddd" }}>Risk</th>
                  <th style={{ padding: "3px 6px", border: "1px solid #ddd" }}>Appr</th>
                  <th style={{ padding: "3px 6px", border: "1px solid #ddd" }}>Tags</th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((node, i) => {
                  const nid = String(node.id ?? "");
                  const cat = catalogMap[nid];
                  const sel = nid === selectedNodeId;
                  return (
                    <tr key={i}
                      onClick={() => setSelectedNodeId(sel ? null : nid)}
                      style={{
                        cursor: "pointer",
                        background: sel ? "#e3f2fd" : (cat?.risk_level === "high" ? "#fff5f5" : "transparent"),
                        borderBottom: "1px solid #eee",
                      }}>
                      <td style={{ padding: "3px 6px", border: "1px solid #ddd" }}>{i + 1}</td>
                      <td style={{ padding: "3px 6px", border: "1px solid #ddd", fontWeight: 600 }}>{nid}</td>
                      <td style={{ padding: "3px 6px", border: "1px solid #ddd", color: cat ? "#333" : "#999", fontStyle: cat ? "normal" : "italic" }}>
                        {cat?.name ?? <span title="Not in Tool Catalog">Unknown metadata ⚠️</span>}
                      </td>
                      <td style={{ padding: "3px 6px", border: "1px solid #ddd" }}>{cat ? riskBadge(cat.risk_level) : "—"}</td>
                      <td style={{ padding: "3px 6px", border: "1px solid #ddd" }}>
                        {cat?.requires_approval ? "🔒" : "—"}
                      </td>
                      <td style={{ padding: "3px 6px", border: "1px solid #ddd" }}>{(cat?.tags ?? []).slice(0, 3).join(", ") || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Depends-on detail row for selected */}
            {selectedNodeId && (
              <div style={{ marginTop: 6, fontSize: 12, color: "#555" }}>
                Depends on: {(nodes.find(n => String(n.id) === selectedNodeId) as Record<string,unknown> | undefined)?
                  .depends_on as string[] | undefined)?.join(", ") || "—"}
              </div>
            )}
          </div>

          {/* Right: node detail panel */}
          <div style={{ width: 260, flexShrink: 0 }}>
            {selectedNodeId && (
              <div style={{ padding: 12, background: "#fafafa", borderRadius: 4, border: "1px solid #e0e0e0", fontSize: 13 }}>
                <h4 style={{ margin: "0 0 8px 0", fontSize: 14 }}>Node Detail</h4>
                {selectedCatalog ? (
                  <>
                    <div style={{ marginBottom: 4 }}><b>ID:</b> {selectedCatalog.id}</div>
                    <div style={{ marginBottom: 4 }}><b>Name:</b> {selectedCatalog.name}</div>
                    <div style={{ marginBottom: 4 }}><b>Description:</b> {selectedCatalog.description || "—"}</div>
                    <div style={{ marginBottom: 4 }}><b>Backend:</b> {selectedCatalog.backend}</div>
                    <div style={{ marginBottom: 4 }}><b>Parallel:</b> {selectedCatalog.parallel_level}</div>
                    <div style={{ marginBottom: 4 }}><b>Risk:</b> {riskBadge(selectedCatalog.risk_level)}</div>
                    <div style={{ marginBottom: 4 }}><b>Approval:</b> {selectedCatalog.requires_approval ? "🔒 Required" : "✅ Not required"}</div>
                    <div style={{ marginBottom: 4 }}><b>Manual:</b> {selectedCatalog.manual_required ? "👤 Required" : "—"}</div>
                    <div style={{ marginBottom: 4 }}><b>Inputs:</b> {selectedCatalog.inputs.join(", ") || "—"}</div>
                    <div style={{ marginBottom: 4 }}><b>Outputs:</b> {selectedCatalog.outputs.join(", ") || "—"}</div>
                    <div><b>Tags:</b> {selectedCatalog.tags.join(", ") || "—"}</div>
                  </>
                ) : (
                  <div style={{ color: "#c62828" }}>
                    ⚠️ Unknown node — not found in Tool Catalog.<br/>
                    This node cannot be validated and should not be executed.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function chipStyle(bg: string, color: string): React.CSSProperties {
  return { padding: "3px 10px", background: bg, color, borderRadius: 12, fontSize: 12, fontWeight: 600 };
}
