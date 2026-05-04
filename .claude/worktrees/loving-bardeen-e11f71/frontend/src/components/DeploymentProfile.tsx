import { useState } from "react";
import { getDeploymentProfile } from "../api";

interface Props {
  baseUrl: string;
}

interface CheckItem {
  name: string;
  ok: boolean;
  message?: string;
}

export function DeploymentProfile({ baseUrl }: Props) {
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheck() {
    setLoading(true);
    setError(null);
    try {
      const result = await getDeploymentProfile(baseUrl);
      setProfile(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const status = profile?.status as string | undefined;
  const checksPassed = profile?.checks_passed as number | undefined;
  const checksTotal = profile?.checks_total as number | undefined;
  const blockers = (profile?.blockers as string[] | undefined) || [];
  const warnings = (profile?.warnings as string[] | undefined) || [];
  const checks = (profile?.checks as CheckItem[] | undefined) || [];
  const profiles = profile?.profiles as Record<string, unknown> | undefined;
  const environment = profile?.environment as Record<string, unknown> | undefined;

  function getStatusColor(s?: string) {
    switch (s) {
      case "READY":
        return "#4caf50";
      case "WARNING":
        return "#ff9800";
      case "BLOCKED":
        return "#f44336";
      default:
        return "#9e9e9e";
    }
  }

  return (
    <div style={{ padding: 16, borderTop: "2px solid #2196f3", marginTop: 24 }}>
      <h2>Deployment Profile</h2>
      
      <div style={{ marginBottom: 16 }}>
        <button 
          onClick={handleCheck} 
          disabled={loading}
          style={{ 
            backgroundColor: "#2196f3", 
            color: "white",
            padding: "8px 16px",
            border: "none",
            borderRadius: 4,
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Checking..." : "Scan Deployment Profile"}
        </button>
      </div>
      
      {error && (
        <div style={{ color: "#f44336", marginBottom: 16, padding: 12, background: "#ffebee", borderRadius: 4 }}>
          {error}
        </div>
      )}
      
      {profile && (
        <>
          {/* Status Summary */}
          <div style={{ 
            marginBottom: 24, 
            padding: 16, 
            background: getStatusColor(status), 
            borderRadius: 4, 
            color: "white" 
          }}>
            <div style={{ fontSize: 32, fontWeight: "bold" }}>
              {status || "UNKNOWN"}
            </div>
            <div style={{ marginTop: 8, opacity: 0.9 }}>
              Checks: {checksPassed} / {checksTotal} passed
            </div>
          </div>
          
          {/* Stats Grid */}
          <div style={{ 
            display: "grid", 
            gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", 
            gap: 12, 
            marginBottom: 24 
          }}>
            <div style={{ padding: 12, background: "#e8f5e9", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Passed</div>
              <div style={{ fontSize: 20, fontWeight: "bold", color: "#4caf50" }}>
                {checksPassed}/{checksTotal}
              </div>
            </div>
            <div style={{ padding: 12, background: "#ffebee", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Blockers</div>
              <div style={{ fontSize: 20, fontWeight: "bold", color: "#f44336" }}>
                {blockers.length}
              </div>
            </div>
            <div style={{ padding: 12, background: "#fff3e0", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Warnings</div>
              <div style={{ fontSize: 20, fontWeight: "bold", color: "#ff9800" }}>
                {warnings.length}
              </div>
            </div>
          </div>
          
          {/* Profiles */}
          {profiles && (
            <div style={{ marginBottom: 24 }}>
              <h3>Deployment Profiles</h3>
              <div style={{ display: "grid", gap: 12 }}>
                {profiles.local_dev && (
                  <div style={{ padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 8 }}>Local Dev</div>
                    <div style={{ fontSize: 12, color: "#666", fontFamily: "monospace" }}>
                      {(profiles.local_dev as Record<string, string>).backend}
                    </div>
                    <div style={{ fontSize: 12, color: "#666", fontFamily: "monospace" }}>
                      {(profiles.local_dev as Record<string, string>).frontend}
                    </div>
                  </div>
                )}
                {profiles.docker_demo && (
                  <div style={{ padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 8 }}>Docker Demo</div>
                    <div style={{ fontSize: 12, color: "#666" }}>
                      Compose: {(profiles.docker_demo as Record<string, string>).compose_file}
                    </div>
                    <div style={{ fontSize: 12, color: "#666" }}>
                      MATLAB: {(profiles.docker_demo as Record<string, boolean>).matlab_enabled_by_default ? "enabled" : "disabled"}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Blockers */}
          {blockers.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ color: "#f44336" }}>Blockers ({blockers.length})</h3>
              <div style={{ background: "#ffebee", borderRadius: 4, padding: 12 }}>
                {blockers.map((b, idx) => (
                  <div key={idx} style={{ padding: "4px 0", color: "#c62828" }}>
                    ❌ {b}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Warnings */}
          {warnings.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ color: "#ff9800" }}>Warnings ({warnings.length})</h3>
              <div style={{ background: "#fff3e0", borderRadius: 4, padding: 12 }}>
                {warnings.map((w, idx) => (
                  <div key={idx} style={{ padding: "4px 0", color: "#e65100" }}>
                    ⚠️ {w}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* All Checks */}
          <div style={{ marginBottom: 24 }}>
            <h3>All Checks ({checks.length})</h3>
            <div style={{ 
              maxHeight: "400px", 
              overflow: "auto", 
              border: "1px solid #e0e0e0", 
              borderRadius: 4 
            }}>
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
                  <span style={{ flex: 1, fontSize: 13 }}>
                    <strong>{check.name}</strong>
                  </span>
                  <span style={{ fontSize: 12, color: "#666" }}>{check.message}</span>
                </div>
              ))}
            </div>
          </div>
          
          {/* Environment */}
          {environment && (
            <div style={{ marginBottom: 24 }}>
              <h3>Environment</h3>
              <div style={{ padding: 12, background: "#f5f5f5", borderRadius: 4, fontSize: 12, fontFamily: "monospace" }}>
                <div>Platform: {environment.platform as string}</div>
                <div>CWD: {environment.cwd as string}</div>
                <div>Docker: {(environment.docker_version as Record<string, unknown>)?.ok ? "available" : "not available"}</div>
                <div>Node: {(environment.node_version as Record<string, unknown>)?.stdout as string || "not available"}</div>
              </div>
            </div>
          )}
          
          {/* Safety Guarantees */}
          {(profile?.safety as Record<string, boolean> | undefined) && (
            <div>
              <h3>Safety Guarantees</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
                {Object.entries(profile.safety as Record<string, boolean>).map(([key, value]) => (
                  <div 
                    key={key} 
                    style={{ 
                      padding: "8px 12px", 
                      background: value ? "#ffebee" : "#e8f5e9",
                      borderRadius: 4,
                      fontSize: 12
                    }}
                  >
                    {value ? "❌" : "✅"} {key.replace(/_/g, " ")}
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
