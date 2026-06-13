import { useState } from "react";
import { getReleaseReadiness } from "../lib/api/legacy";

type Props = {
  baseUrl: string;
};

type CheckItem = {
  name: string;
  kind?: string;
  ok: boolean;
  severity: string;
  message: string;
};

export function ReleaseReadiness({ baseUrl }: Props) {
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheck() {
    setLoading(true);
    setError(null);
    try {
      const result = await getReleaseReadiness(baseUrl);
      setReadiness(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const status = readiness?.status as string | undefined;
  const readinessScore = readiness?.readiness_score as number | undefined;
  const checksPassed = readiness?.checks_passed as number | undefined;
  const checksTotal = readiness?.checks_total as number | undefined;
  const blockersCount = readiness?.blockers_count as number | undefined;
  const warningsCount = readiness?.warnings_count as number | undefined;
  const checks = (readiness?.checks as CheckItem[] | undefined) || [];
  const blockers = (readiness?.blockers as string[] | undefined) || [];
  const warnings = (readiness?.warnings as string[] | undefined) || [];

  const getStatusColor = (s?: string) => {
    switch (s) {
      case "READY":
        return "#4caf50";
      case "WARNING":
        return "#ff9800";
      case "BLOCKED":
        return "#f44336";
      default:
        return "#607d8b";
    }
  };

  const getSeverityColor = (s: string) => {
    switch (s) {
      case "blocker":
        return "#f44336";
      case "warning":
        return "#ff9800";
      default:
        return "#4caf50";
    }
  };

  return (
    <div style={{ padding: 16, borderTop: "2px solid #673ab7", marginTop: 24 }}>
      <h2>Release Readiness</h2>

      <div style={{ marginBottom: 16 }}>
        <button onClick={handleCheck} disabled={loading} style={{ backgroundColor: "#673ab7", color: "white" }}>
          {loading ? "Checking..." : "Run Readiness Check"}
        </button>
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: 16, padding: 12, background: "#ffebee", borderRadius: 4 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {readiness && (
        <>
          {/* Status Summary */}
          <div style={{ marginBottom: 24, padding: 16, background: getStatusColor(status), borderRadius: 4, color: "white" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
              <div>
                <div style={{ fontSize: 12, opacity: 0.9 }}>Status</div>
                <div style={{ fontSize: 32, fontWeight: "bold" }}>{status}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 12, opacity: 0.9 }}>Readiness Score</div>
                <div style={{ fontSize: 32, fontWeight: "bold" }}>{readinessScore}%</div>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12, marginBottom: 24 }}>
            <div style={{ padding: 12, background: "#e8f5e9", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Passed</div>
              <div style={{ fontSize: 20, fontWeight: "bold", color: "#4caf50" }}>
                {checksPassed}/{checksTotal}
              </div>
            </div>
            <div style={{ padding: 12, background: "#ffebee", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Blockers</div>
              <div style={{ fontSize: 20, fontWeight: "bold", color: "#f44336" }}>
                {blockersCount}
              </div>
            </div>
            <div style={{ padding: 12, background: "#fff3e0", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Warnings</div>
              <div style={{ fontSize: 20, fontWeight: "bold", color: "#ff9800" }}>
                {warningsCount}
              </div>
            </div>
          </div>

          {/* Blockers */}
          {blockers.length > 0 && (
            <div style={{ marginBottom: 16, padding: 12, background: "#ffebee", borderRadius: 4 }}>
              <h3 style={{ marginTop: 0, color: "#c62828" }}>❌ Blockers</h3>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {blockers.map((blocker, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>{blocker}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <div style={{ marginBottom: 16, padding: 12, background: "#fff3e0", borderRadius: 4 }}>
              <h3 style={{ marginTop: 0, color: "#e65100" }}>⚠️ Warnings</h3>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {warnings.map((warning, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {/* All Checks */}
          <div>
            <h3>All Checks ({checks.length})</h3>
            <div style={{ maxHeight: "400px", overflow: "auto", border: "1px solid #e0e0e0", borderRadius: 4 }}>
              {checks.map((check, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "8px 12px",
                    borderBottom: "1px solid #f0f0f0",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    background: check.ok ? "#f5f5f5" : "#ffebee",
                  }}
                >
                  <span style={{ fontSize: 16 }}>{check.ok ? "✅" : "❌"}</span>
                  <span
                    style={{
                      padding: "2px 6px",
                      borderRadius: 4,
                      fontSize: 10,
                      background: getSeverityColor(check.severity),
                      color: "white",
                      textTransform: "uppercase",
                    }}
                  >
                    {check.severity}
                  </span>
                  <span style={{ flex: 1, fontSize: 13 }}>
                    <strong>{check.name}</strong>
                    {check.kind && <span style={{ color: "#666", marginLeft: 4 }}>({check.kind})</span>}
                  </span>
                  <span style={{ fontSize: 12, color: "#666" }}>{check.message}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Safety Guarantees */}
          {(readiness?.safety as Record<string, boolean> | undefined) && (
            <div style={{ marginTop: 24, padding: 12, background: "#e3f2fd", borderRadius: 4 }}>
              <h3 style={{ marginTop: 0 }}>Safety Guarantees</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
                {Object.entries(readiness.safety as Record<string, boolean>).map(([key, value]) => (
                  <div key={key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 16 }}>{value ? "✅" : "❌"}</span>
                    <span style={{ fontSize: 12 }}>{key.replace(/_/g, " ")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
