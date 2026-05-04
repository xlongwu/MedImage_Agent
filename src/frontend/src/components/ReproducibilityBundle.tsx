import { useState } from "react";
import {
  listBundles,
  createBundle,
  inspectBundle,
} from "../api";

type Props = {
  baseUrl: string;
};

type BundleItem = {
  bundle_id: string;
  created_at: string;
  bundle_dir: string;
  zip_path: string;
  zip_sha256: string;
  zip_size_bytes: number;
  files_copied: number;
  files_skipped: number;
  manifest_path: string;
};

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function ReproducibilityBundle({ baseUrl }: Props) {
  const [bundles, setBundles] = useState<BundleItem[]>([]);
  const [selectedBundle, setSelectedBundle] = useState<BundleItem | null>(null);
  const [bundleDetail, setBundleDetail] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOptions, setCreateOptions] = useState({
    bundle_id: "",
    include_logs: true,
    include_reports: true,
    include_artifact_index: true,
    max_file_size_bytes: 2000000,
  });

  async function handleListBundles() {
    setLoading(true);
    setError(null);
    try {
      const result = (await listBundles(baseUrl)) as { bundles?: BundleItem[] };
      setBundles(result.bundles || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateBundle() {
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        include_logs: createOptions.include_logs,
        include_reports: createOptions.include_reports,
        include_artifact_index: createOptions.include_artifact_index,
        max_file_size_bytes: createOptions.max_file_size_bytes,
      };
      if (createOptions.bundle_id.trim()) {
        payload.bundle_id = createOptions.bundle_id.trim();
      }
      const result = await createBundle(baseUrl, payload);
      if (result.ok) {
        await handleListBundles();
        setCreateOptions({
          bundle_id: "",
          include_logs: true,
          include_reports: true,
          include_artifact_index: true,
          max_file_size_bytes: 2000000,
        });
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleInspectBundle(bundleId: string) {
    setLoading(true);
    setError(null);
    try {
      const result = await inspectBundle(baseUrl, bundleId);
      setBundleDetail(result);
      const bundle = bundles.find((b) => b.bundle_id === bundleId);
      if (bundle) {
        setSelectedBundle(bundle);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16, borderTop: "2px solid #795548", marginTop: 24 }}>
      <h2>Reproducibility Bundle</h2>

      <div style={{ marginBottom: 16 }}>
        <button onClick={handleListBundles} disabled={loading} style={{ marginRight: 8 }}>
          {loading ? "Loading..." : "List Bundles"}
        </button>
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: 16, padding: 12, background: "#ffebee", borderRadius: 4 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Create Bundle Section */}
      <div style={{ marginBottom: 24, padding: 16, background: "#f5f5f5", borderRadius: 4 }}>
        <h3>Create New Bundle</h3>
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>
            Bundle ID (optional, auto-generated if empty)
          </label>
          <input
            type="text"
            value={createOptions.bundle_id}
            onChange={(e) => setCreateOptions({ ...createOptions, bundle_id: e.target.value })}
            placeholder="bundle_YYYYMMDD_HHMMSS"
            style={{ width: "100%", maxWidth: 300 }}
          />
        </div>

        <div style={{ marginBottom: 12, display: "flex", gap: 16, flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              checked={createOptions.include_logs}
              onChange={(e) => setCreateOptions({ ...createOptions, include_logs: e.target.checked })}
            />
            Include Logs
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              checked={createOptions.include_reports}
              onChange={(e) => setCreateOptions({ ...createOptions, include_reports: e.target.checked })}
            />
            Include Reports
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              checked={createOptions.include_artifact_index}
              onChange={(e) => setCreateOptions({ ...createOptions, include_artifact_index: e.target.checked })}
            />
            Include Artifact Index
          </label>
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>
            Max File Size (bytes)
          </label>
          <input
            type="number"
            value={createOptions.max_file_size_bytes}
            onChange={(e) => setCreateOptions({ ...createOptions, max_file_size_bytes: parseInt(e.target.value) || 2000000 })}
            style={{ width: 150 }}
          />
          <span style={{ marginLeft: 8, fontSize: 12, color: "#666" }}>
            ({formatBytes(createOptions.max_file_size_bytes)})
          </span>
        </div>

        <button onClick={handleCreateBundle} disabled={loading} style={{ backgroundColor: "#4caf50", color: "white" }}>
          {loading ? "Creating..." : "Create Bundle"}
        </button>
      </div>

      {/* Bundles List */}
      {bundles.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h3>Existing Bundles ({bundles.length})</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f5f5f5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Bundle ID</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Created</th>
                  <th style={{ padding: 8, textAlign: "right" }}>ZIP Size</th>
                  <th style={{ padding: 8, textAlign: "center" }}>Files</th>
                  <th style={{ padding: 8, textAlign: "center" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {bundles.map((bundle) => (
                  <tr key={bundle.bundle_id} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={{ padding: 8, fontFamily: "monospace", fontSize: 12 }}>
                      {bundle.bundle_id}
                    </td>
                    <td style={{ padding: 8, fontSize: 12 }}>
                      {new Date(bundle.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: 8, textAlign: "right" }}>
                      {formatBytes(bundle.zip_size_bytes)}
                    </td>
                    <td style={{ padding: 8, textAlign: "center" }}>
                      {bundle.files_copied} copied, {bundle.files_skipped} skipped
                    </td>
                    <td style={{ padding: 8, textAlign: "center" }}>
                      <button
                        onClick={() => handleInspectBundle(bundle.bundle_id)}
                        style={{ fontSize: 11, padding: "2px 8px" }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bundle Detail */}
      {selectedBundle && bundleDetail && (
        <div style={{ padding: 16, background: "#fafafa", borderRadius: 4 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Bundle Detail: {selectedBundle.bundle_id}</h3>
            <button onClick={() => { setSelectedBundle(null); setBundleDetail(null); }} style={{ fontSize: 12 }}>
              Close
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 16 }}>
            <div style={{ padding: 12, background: "white", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>ZIP Size</div>
              <div style={{ fontSize: 18, fontWeight: "bold" }}>{formatBytes(selectedBundle.zip_size_bytes)}</div>
            </div>
            <div style={{ padding: 12, background: "white", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Files Copied</div>
              <div style={{ fontSize: 18, fontWeight: "bold" }}>{selectedBundle.files_copied}</div>
            </div>
            <div style={{ padding: 12, background: "white", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Files Skipped</div>
              <div style={{ fontSize: 18, fontWeight: "bold" }}>{selectedBundle.files_skipped}</div>
            </div>
          </div>

          <div style={{ marginBottom: 12 }}>
            <strong>ZIP SHA256:</strong>
            <code style={{ display: "block", marginTop: 4, padding: 8, background: "#f5f5f5", borderRadius: 4, fontSize: 11, wordBreak: "break-all" }}>
              {selectedBundle.zip_sha256}
            </code>
          </div>

          <div style={{ marginBottom: 12 }}>
            <strong>Bundle Directory:</strong>
            <code style={{ display: "block", marginTop: 4, padding: 8, background: "#f5f5f5", borderRadius: 4, fontSize: 11 }}>
              {selectedBundle.bundle_dir}
            </code>
          </div>

          <div style={{ marginBottom: 12 }}>
            <strong>ZIP Path:</strong>
            <code style={{ display: "block", marginTop: 4, padding: 8, background: "#f5f5f5", borderRadius: 4, fontSize: 11 }}>
              {selectedBundle.zip_path}
            </code>
          </div>

          {(bundleDetail.manifest as Record<string, unknown> | undefined)?.safety && (
            <div style={{ marginTop: 16 }}>
              <h4>Safety Checks</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
                {Object.entries((bundleDetail.manifest as Record<string, unknown>).safety as Record<string, boolean>).map(([key, value]) => (
                  <div key={key} style={{ padding: 8, background: value ? "#ffebee" : "#e8f5e9", borderRadius: 4, fontSize: 12 }}>
                    <span style={{ color: value ? "#c62828" : "#2e7d32" }}>
                      {value ? "❌" : "✅"}
                    </span>{" "}
                    {key.replace(/_/g, " ")}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
