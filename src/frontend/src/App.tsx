import { useEffect, useState } from "react";
import { getHealth } from "./api";
import WorkflowShell from "./components/workflow/WorkflowShell";
import AdvancedModePanel from "./components/workflow/AdvancedModePanel";

export default function App() {
  const baseUrl = "http://127.0.0.1:8000";
  const [mode, setMode] = useState<"user" | "advanced">("user");
  const [health, setHealth] = useState<boolean | null>(null);
  const [apiError, setApiError] = useState("");

  useEffect(() => {
    checkHealth();
  }, []);

  async function checkHealth() {
    setApiError("");
    try {
      const result = await getHealth(baseUrl);
      setHealth(!!result);
    } catch {
      setHealth(false);
      setApiError("Cannot connect to backend. Start it with:\nuvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000");
    }
  }

  return (
    <div>
      {/* Header */}
      <header style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "10px 24px", background: "#1976d2", color: "#fff",
      }}>
        <div>
          <span style={{ fontSize: 18, fontWeight: 700 }}>MedImage Agent</span>
          <span style={{ marginLeft: 12, fontSize: 12, opacity: 0.8 }}>
            {health === null ? "Checking..." : health ? "Backend Connected" : "Backend Offline"}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {!health && (
            <button onClick={checkHealth} style={{ padding: "4px 12px", fontSize: 12, background: "#fff", color: "#1976d2", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
              Retry
            </button>
          )}
          <button
            onClick={() => setMode(mode === "user" ? "advanced" : "user")}
            style={{
              padding: "6px 16px", fontSize: 13, fontWeight: 600, borderRadius: 4, cursor: "pointer",
              background: mode === "advanced" ? "#4caf50" : "rgba(255,255,255,0.2)",
              color: "#fff", border: "1px solid rgba(255,255,255,0.3)",
            }}
          >
            {mode === "user" ? "Advanced Mode" : "User Mode"}
          </button>
        </div>
      </header>

      {/* API error banner */}
      {apiError && (
        <div style={{ padding: "12px 24px", background: "#fff3e0", borderBottom: "1px solid #ffe0b2", fontSize: 13, color: "#e65100", whiteSpace: "pre-line" }}>
          {apiError}
        </div>
      )}

      {/* Mode content */}
      {mode === "user" ? (
        <WorkflowShell />
      ) : (
        <AdvancedModePanel baseUrl={baseUrl} />
      )}

      {/* Footer */}
      <footer style={{ textAlign: "center", padding: 16, color: "#999", fontSize: 12, borderTop: "1px solid #eee" }}>
        MedImage Agent v0.2.0 — Research use only. Not for clinical diagnosis.
      </footer>
    </div>
  );
}
