import { useState } from "react";
import { listBundles, createBundle, inspectBundle } from "../lib/api/legacy";
import styles from "./ReproducibilityBundle.module.css";

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
    <div className={styles.style001}>
      <h2>Reproducibility Bundle</h2>

      <div className={styles.style002}>
        <button onClick={handleListBundles} disabled={loading} className={styles.style003}>
          {loading ? "Loading..." : "List Bundles"}
        </button>
      </div>

      {error && (
        <div className={styles.style004}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Create Bundle Section */}
      <div className={styles.style005}>
        <h3>Create New Bundle</h3>
        <div className={styles.style006}>
          <label className={styles.style007}>Bundle ID (optional, auto-generated if empty)</label>
          <input
            type="text"
            value={createOptions.bundle_id}
            onChange={(e) => setCreateOptions({ ...createOptions, bundle_id: e.target.value })}
            placeholder="bundle_YYYYMMDD_HHMMSS"
            style={{ width: "100%", maxWidth: 300 }}
          />
        </div>

        <div className={styles.style008}>
          <label className={styles.style009}>
            <input
              type="checkbox"
              checked={createOptions.include_logs}
              onChange={(e) =>
                setCreateOptions({ ...createOptions, include_logs: e.target.checked })
              }
            />
            Include Logs
          </label>
          <label className={styles.style010}>
            <input
              type="checkbox"
              checked={createOptions.include_reports}
              onChange={(e) =>
                setCreateOptions({ ...createOptions, include_reports: e.target.checked })
              }
            />
            Include Reports
          </label>
          <label className={styles.style011}>
            <input
              type="checkbox"
              checked={createOptions.include_artifact_index}
              onChange={(e) =>
                setCreateOptions({ ...createOptions, include_artifact_index: e.target.checked })
              }
            />
            Include Artifact Index
          </label>
        </div>

        <div className={styles.style012}>
          <label className={styles.style013}>Max File Size (bytes)</label>
          <input
            type="number"
            value={createOptions.max_file_size_bytes}
            onChange={(e) =>
              setCreateOptions({
                ...createOptions,
                max_file_size_bytes: parseInt(e.target.value) || 2000000,
              })
            }
            style={{ width: 150 }}
          />
          <span className={styles.style014}>
            ({formatBytes(createOptions.max_file_size_bytes)})
          </span>
        </div>

        <button onClick={handleCreateBundle} disabled={loading} className={styles.style015}>
          {loading ? "Creating..." : "Create Bundle"}
        </button>
      </div>

      {/* Bundles List */}
      {bundles.length > 0 && (
        <div className={styles.style016}>
          <h3>Existing Bundles ({bundles.length})</h3>
          <div className={styles.style017}>
            <table className={styles.style018}>
              <thead>
                <tr className={styles.style019}>
                  <th className={styles.style020}>Bundle ID</th>
                  <th className={styles.style021}>Created</th>
                  <th className={styles.style022}>ZIP Size</th>
                  <th className={styles.style023}>Files</th>
                  <th className={styles.style024}>Action</th>
                </tr>
              </thead>
              <tbody>
                {bundles.map((bundle) => (
                  <tr key={bundle.bundle_id} className={styles.style025}>
                    <td className={styles.style026}>{bundle.bundle_id}</td>
                    <td className={styles.style027}>
                      {new Date(bundle.created_at).toLocaleString()}
                    </td>
                    <td className={styles.style028}>{formatBytes(bundle.zip_size_bytes)}</td>
                    <td className={styles.style029}>
                      {bundle.files_copied} copied, {bundle.files_skipped} skipped
                    </td>
                    <td className={styles.style030}>
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
        <div className={styles.style031}>
          <div className={styles.style032}>
            <h3 className={styles.style033}>Bundle Detail: {selectedBundle.bundle_id}</h3>
            <button
              onClick={() => {
                setSelectedBundle(null);
                setBundleDetail(null);
              }}
              style={{ fontSize: 12 }}
            >
              Close
            </button>
          </div>

          <div className={styles.style034}>
            <div className={styles.style035}>
              <div className={styles.style036}>ZIP Size</div>
              <div className={styles.style037}>{formatBytes(selectedBundle.zip_size_bytes)}</div>
            </div>
            <div className={styles.style038}>
              <div className={styles.style039}>Files Copied</div>
              <div className={styles.style040}>{selectedBundle.files_copied}</div>
            </div>
            <div className={styles.style041}>
              <div className={styles.style042}>Files Skipped</div>
              <div className={styles.style043}>{selectedBundle.files_skipped}</div>
            </div>
          </div>

          <div className={styles.style044}>
            <strong>ZIP SHA256:</strong>
            <code className={styles.style045}>{selectedBundle.zip_sha256}</code>
          </div>

          <div className={styles.style046}>
            <strong>Bundle Directory:</strong>
            <code className={styles.style047}>{selectedBundle.bundle_dir}</code>
          </div>

          <div className={styles.style048}>
            <strong>ZIP Path:</strong>
            <code className={styles.style049}>{selectedBundle.zip_path}</code>
          </div>

          {(bundleDetail.manifest as Record<string, unknown> | undefined)?.safety && (
            <div className={styles.style050}>
              <h4>Safety Checks</h4>
              <div className={styles.style051}>
                {Object.entries(
                  (bundleDetail.manifest as Record<string, unknown>).safety as Record<
                    string,
                    boolean
                  >,
                ).map(([key, value]) => (
                  <div
                    key={key}
                    style={{
                      padding: 8,
                      background: value ? "#ffebee" : "#e8f5e9",
                      borderRadius: 4,
                      fontSize: 12,
                    }}
                  >
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
