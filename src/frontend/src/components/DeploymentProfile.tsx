import { useState } from "react";
import type { CSSProperties } from "react";
import { getDeploymentProfile } from "../lib/api/legacy";
import styles from "./DeploymentProfile.module.css";

function cssVars(vars: Record<string, string>): CSSProperties {
  return vars as CSSProperties;
}

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
    <div className={styles.style001}>
      <h2>Deployment Profile</h2>

      <div className={styles.style002}>
        <button
          onClick={handleCheck}
          disabled={loading}
          style={{
            backgroundColor: "#2196f3",
            color: "white",
            padding: "8px 16px",
            border: "none",
            borderRadius: 4,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Checking..." : "Scan Deployment Profile"}
        </button>
      </div>

      {error && <div className={styles.style003}>{error}</div>}

      {profile && (
        <>
          {/* Status Summary */}
          <div
            className={styles.style004}
            style={cssVars({ "--status-bg": getStatusColor(status) })}
          >
            <div className={styles.style005}>{status || "UNKNOWN"}</div>
            <div className={styles.style006}>
              Checks: {checksPassed} / {checksTotal} passed
            </div>
          </div>

          {/* Stats Grid */}
          <div className={styles.style007}>
            <div className={styles.style008}>
              <div className={styles.style009}>Passed</div>
              <div className={styles.style010}>
                {checksPassed}/{checksTotal}
              </div>
            </div>
            <div className={styles.style011}>
              <div className={styles.style012}>Blockers</div>
              <div className={styles.style013}>{blockers.length}</div>
            </div>
            <div className={styles.style014}>
              <div className={styles.style015}>Warnings</div>
              <div className={styles.style016}>{warnings.length}</div>
            </div>
          </div>

          {/* Profiles */}
          {profiles && (
            <div className={styles.style017}>
              <h3>Deployment Profiles</h3>
              <div className={styles.style018}>
                {profiles.local_dev && (
                  <div className={styles.style019}>
                    <div className={styles.style020}>Local Dev</div>
                    <div className={styles.style021}>
                      {(profiles.local_dev as Record<string, string>).backend}
                    </div>
                    <div className={styles.style022}>
                      {(profiles.local_dev as Record<string, string>).frontend}
                    </div>
                  </div>
                )}
                {profiles.docker_demo && (
                  <div className={styles.style023}>
                    <div className={styles.style024}>Docker Demo</div>
                    <div className={styles.style025}>
                      Compose: {(profiles.docker_demo as Record<string, string>).compose_file}
                    </div>
                    <div className={styles.style026}>
                      MATLAB:{" "}
                      {(profiles.docker_demo as Record<string, boolean>).matlab_enabled_by_default
                        ? "enabled"
                        : "disabled"}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Blockers */}
          {blockers.length > 0 && (
            <div className={styles.style027}>
              <h3 className={styles.style028}>Blockers ({blockers.length})</h3>
              <div className={styles.style029}>
                {blockers.map((b, idx) => (
                  <div key={idx} className={styles.style030}>
                    ❌ {b}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <div className={styles.style031}>
              <h3 className={styles.style032}>Warnings ({warnings.length})</h3>
              <div className={styles.style033}>
                {warnings.map((w, idx) => (
                  <div key={idx} className={styles.style034}>
                    ⚠️ {w}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Checks */}
          <div className={styles.style035}>
            <h3>All Checks ({checks.length})</h3>
            <div className={styles.style036}>
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
                  <span className={styles.style037}>{check.ok ? "✅" : "❌"}</span>
                  <span className={styles.style038}>
                    <strong>{check.name}</strong>
                  </span>
                  <span className={styles.style039}>{check.message}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Environment */}
          {environment && (
            <div className={styles.style040}>
              <h3>Environment</h3>
              <div className={styles.style041}>
                <div>Platform: {environment.platform as string}</div>
                <div>CWD: {environment.cwd as string}</div>
                <div>
                  Docker:{" "}
                  {(environment.docker_version as Record<string, unknown>)?.ok
                    ? "available"
                    : "not available"}
                </div>
                <div>
                  Node:{" "}
                  {((environment.node_version as Record<string, unknown>)?.stdout as string) ||
                    "not available"}
                </div>
              </div>
            </div>
          )}

          {/* Safety Guarantees */}
          {(profile?.safety as Record<string, boolean> | undefined) && (
            <div>
              <h3>Safety Guarantees</h3>
              <div className={styles.style042}>
                {Object.entries(profile.safety as Record<string, boolean>).map(([key, value]) => (
                  <div
                    key={key}
                    style={{
                      padding: "8px 12px",
                      background: value ? "#ffebee" : "#e8f5e9",
                      borderRadius: 4,
                      fontSize: 12,
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
