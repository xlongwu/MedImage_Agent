import { useMemo, useState } from "react";
import {
  getArtifacts,
  previewArtifact,
  refreshArtifacts
} from "../api";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
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
  run_id_guess?: string | null;
};

function asArtifacts(payload: Record<string, unknown> | null): ArtifactRecord[] {
  const index = payload?.index as Record<string, unknown> | undefined;
  const artifacts = index?.artifacts;

  if (!Array.isArray(artifacts)) return [];
  return artifacts as ArtifactRecord[];
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function ArtifactBrowser({ baseUrl }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [extensionFilter, setExtensionFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await getArtifacts(baseUrl);
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

    try {
      const result = await refreshArtifacts(baseUrl);
      setPayload(result);
      setStatus("LOADED");
    } catch (e) {
      setError(String(e));
      setStatus("ERROR");
    }
  }

  async function handlePreview(path: string) {
    setPreview(null);
    try {
      const result = await previewArtifact(baseUrl, path);
      setPreview(result);
    } catch (e) {
      setPreview({ error: String(e) });
    }
  }

  const allArtifacts = useMemo(() => asArtifacts(payload), [payload]);

  const categories = useMemo(() => {
    const set = new Set(allArtifacts.map((a) => a.category));
    return Array.from(set).sort();
  }, [allArtifacts]);

  const extensions = useMemo(() => {
    const set = new Set(allArtifacts.map((a) => a.extension));
    return Array.from(set).sort();
  }, [allArtifacts]);

  const filteredArtifacts = useMemo(() => {
    return allArtifacts.filter((a) => {
      const matchesCategory = categoryFilter === "all" || a.category === categoryFilter;
      const matchesExtension = extensionFilter === "all" || a.extension === extensionFilter;
      const matchesSearch =
        search.trim() === "" ||
        a.name.toLowerCase().includes(search.toLowerCase()) ||
        a.path.toLowerCase().includes(search.toLowerCase());
      return matchesCategory && matchesExtension && matchesSearch;
    });
  }, [allArtifacts, categoryFilter, extensionFilter, search]);

  const indexMeta = payload?.index as Record<string, unknown> | undefined;

  return (
    <div style={{ padding: 16, borderTop: "2px solid #9c27b0", marginTop: 24 }}>
      <h2>Artifact Browser</h2>

      <div style={{ marginBottom: 16 }}>
        <button onClick={handleLoad} disabled={status === "LOADING"} style={{ marginRight: 8 }}>
          {status === "LOADING" ? "Loading..." : "Load Artifacts"}
        </button>
        <button onClick={handleRefresh} disabled={status === "LOADING"} style={{ backgroundColor: "#2196f3", color: "white" }}>
          {status === "LOADING" ? "Refreshing..." : "Refresh Index"}
        </button>
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: 16, padding: 12, background: "#ffebee", borderRadius: 4 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {indexMeta && (
        <div style={{ marginBottom: 16, padding: 12, background: "#e3f2fd", borderRadius: 4 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
            <div>
              <strong>Total Artifacts:</strong> {indexMeta.artifacts_total}
            </div>
            <div>
              <strong>Generated:</strong> {new Date(String(indexMeta.generated_at)).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {allArtifacts.length > 0 && (
        <>
          <div style={{ marginBottom: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>
                Category
              </label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="all">All</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>
                Extension
              </label>
              <select
                value={extensionFilter}
                onChange={(e) => setExtensionFilter(e.target.value)}
              >
                <option value="all">All</option>
                {extensions.map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ flex: 1, minWidth: 200 }}>
              <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>
                Search
              </label>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or path..."
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <div style={{ marginBottom: 8, fontSize: 12, color: "#666" }}>
            Showing {filteredArtifacts.length} of {allArtifacts.length} artifacts
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f5f5f5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Name</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Category</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Extension</th>
                  <th style={{ padding: 8, textAlign: "right" }}>Size</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Modified</th>
                  <th style={{ padding: 8, textAlign: "center" }}>Preview</th>
                </tr>
              </thead>
              <tbody>
                {filteredArtifacts.slice(0, 100).map((artifact, idx) => (
                  <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={{ padding: 8 }}>
                      <div style={{ fontWeight: 500 }}>{artifact.name}</div>
                      <div style={{ fontSize: 11, color: "#666", fontFamily: "monospace" }}>
                        {artifact.run_id_guess && (
                          <span style={{ marginRight: 8, color: "#2196f3" }}>
                            [{artifact.run_id_guess}]
                          </span>
                        )}
                        {artifact.path}
                      </div>
                    </td>
                    <td style={{ padding: 8 }}>
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: 4,
                          background: "#e3f2fd",
                          fontSize: 11
                        }}
                      >
                        {artifact.category}
                      </span>
                    </td>
                    <td style={{ padding: 8, fontFamily: "monospace", fontSize: 11 }}>
                      {artifact.extension}
                    </td>
                    <td style={{ padding: 8, textAlign: "right" }}>
                      {formatBytes(artifact.size_bytes)}
                    </td>
                    <td style={{ padding: 8, fontSize: 11 }}>
                      {new Date(artifact.modified_time).toLocaleString()}
                    </td>
                    <td style={{ padding: 8, textAlign: "center" }}>
                      {artifact.preview_supported ? (
                        <button
                          onClick={() => handlePreview(artifact.path)}
                          style={{ fontSize: 11, padding: "2px 8px" }}
                        >
                          View
                        </button>
                      ) : (
                        <span style={{ color: "#999", fontSize: 11 }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredArtifacts.length > 100 && (
            <div style={{ marginTop: 16, textAlign: "center", color: "#666", fontSize: 12 }}>
              ... and {filteredArtifacts.length - 100} more artifacts (use filters to narrow down)
            </div>
          )}
        </>
      )}

      {preview && (
        <div style={{ marginTop: 24, padding: 16, background: "#fafafa", borderRadius: 4 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Preview</h3>
            <button onClick={() => setPreview(null)} style={{ fontSize: 12 }}>
              Close
            </button>
          </div>

          {preview.error ? (
            <div style={{ color: "red" }}>{String(preview.error)}</div>
          ) : (
            <>
              {(preview.artifact as ArtifactRecord | undefined) && (
                <div style={{ marginBottom: 12, padding: 8, background: "#e3f2fd", borderRadius: 4, fontSize: 12 }}>
                  <strong>{(preview.artifact as ArtifactRecord).name}</strong>
                  <span style={{ marginLeft: 8, color: "#666" }}>
                    {(preview.artifact as ArtifactRecord).path}
                  </span>
                </div>
              )}

              <TextViewer
                text={String((preview.preview as Record<string, unknown> | undefined)?.text ?? "")}
                parsed={(preview.preview as Record<string, unknown> | undefined)?.parsed}
                truncated={Boolean((preview.preview as Record<string, unknown> | undefined)?.truncated)}
                previewType={String((preview.preview as Record<string, unknown> | undefined)?.preview_type ?? "text")}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}
