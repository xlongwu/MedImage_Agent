import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { DEFAULT_API_BASE } from "../lib/api/client";
import { getProjectNiftiQcSnapshot, getProjectNiftiThumbnail } from "../lib/api/preprocessing";
import type { NiftiQcSnapshotResponse } from "../types";
import { ActionList, MetricTile, SafetyBanner, StatusPill } from "./dashboardUi";

type Props = { baseUrl?: string; projectId: string | null };

const pill: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 22,
  padding: "0 7px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 10,
  fontWeight: 900,
};
const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono","Consolas",monospace',
  fontSize: 10,
  overflowWrap: "anywhere",
};

export default function NiftiQcSnapshotPanel({ baseUrl, projectId }: Props) {
  const { t } = useI18n();
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<NiftiQcSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const reqRef = useRef(0);

  useEffect(() => {
    if (!projectId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Clear stale snapshot when project selection is removed.
      setData(null);
      return;
    }
    const id = reqRef.current + 1;
    reqRef.current = id;
    setLoading(true);
    setError("");
    getProjectNiftiQcSnapshot(effectiveBase, projectId)
      .then((d) => {
        if (id === reqRef.current) setData(d);
      })
      .catch((e) => {
        if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (id === reqRef.current) setLoading(false);
      });
  }, [effectiveBase, projectId]);

  if (!projectId)
    return (
      <Sec>
        <H3>{t("technical.NiftiQcSnapshot.001")}</H3>
        <div className="empty">{t("technical.BoldReferenceReadiness.002")}</div>
      </Sec>
    );
  if (loading)
    return (
      <Sec>
        <H3>{t("technical.NiftiQcSnapshot.001")}</H3>
        <div className="empty">{t("technical.NiftiQcSnapshot.002")}</div>
      </Sec>
    );
  if (error)
    return (
      <Sec>
        <H3>{t("technical.NiftiQcSnapshot.001")}</H3>
        <div className="errorBox">{error}</div>
      </Sec>
    );
  if (!data)
    return (
      <Sec>
        <H3>{t("technical.NiftiQcSnapshot.001")}</H3>
        <div className="empty">{t("technical.NiftiQcSnapshot.003")}</div>
      </Sec>
    );
  const niftiNotApplicable = data.image_count === 0;

  return (
    <Sec>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10,
          marginBottom: 12,
        }}
      >
        <div>
          <H3>{t("technical.NiftiQcSnapshot.001")}</H3>
          <Sub>{t("technical.NiftiQcSnapshot.004")}</Sub>
        </div>
        <StatusPill status={niftiNotApplicable ? "not_applicable" : data.status}>
          {niftiNotApplicable
            ? t("technical.NiftiQcSnapshot.notApplicable")
            : t(`technical.readiness.status.${data.status}` as Parameters<typeof t>[0])}
        </StatusPill>
      </div>
      <SafetyBanner tone="warning">{t("technical.NiftiQcSnapshot.005")}</SafetyBanner>

      {niftiNotApplicable ? (
        <SafetyBanner tone="info">
          {t("technical.NiftiQcSnapshot.notApplicableDescription")}{" "}
          <strong>{t("technical.NiftiQcSnapshot.006")}</strong> {t("technical.NiftiQcSnapshot.007")}
        </SafetyBanner>
      ) : null}

      {/* Counts grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(80px, 1fr))",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <MetricTile
          label={t("technical.NiftiQcSnapshot.inputImages")}
          value={data.image_count}
          tone={data.image_count > 0 ? "green" : "neutral"}
        />
        <MetricTile label={t("technical.NiftiQcSnapshot.readable")} value={data.readable_count} />
        <MetricTile
          label={t("technical.NiftiQcSnapshot.unreadable")}
          value={data.unreadable_count}
          tone={data.unreadable_count > 0 ? "red" : "neutral"}
        />
        <MetricTile label="4D" value={data.four_d_count} />
        <MetricTile
          label={t("technical.NiftiQcSnapshot.warnings")}
          value={data.warning_count}
          tone={data.warning_count > 0 ? "amber" : "neutral"}
        />
      </div>

      {/* Safety flags */}
      {data.safety_flags && Object.keys(data.safety_flags).length > 0 && (
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 12 }}>
          {Object.entries(data.safety_flags).map(([k, v]) => (
            <span
              key={k}
              style={{
                ...pill,
                background: v ? "#e8f5e9" : "#ffebee",
                color: v ? "#176b3b" : "#b53b3b",
                borderColor: v ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)",
              }}
            >
              {k}: {String(v)}
            </span>
          ))}
        </div>
      )}

      {/* Image table */}
      {data.images.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>
            {t("technical.NiftiQcSnapshot.inputImages")} ({data.images.length})
          </h4>
          <div style={{ display: "grid", gap: 6, maxHeight: 360, overflow: "auto" }}>
            {data.images.map((img) => {
              const key = img.image_id;
              const isExpanded = expanded.has(key);
              return (
                <div
                  key={key}
                  style={{
                    padding: 8,
                    border: "1px solid rgba(137,150,171,0.22)",
                    borderRadius: 6,
                    background: "#fff",
                    display: "grid",
                    gap: 4,
                    fontSize: 11,
                  }}
                >
                  {/* Summary row */}
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    {img.subject_id && <strong>{img.subject_id}</strong>}
                    <span style={{ color: "#667085" }}>{img.modality || "?"}</span>
                    <span style={mono}>{img.dimensions?.join("×") || "?"}</span>
                    {img.voxel_spacing?.length > 0 && (
                      <span style={mono}>
                        {img.voxel_spacing
                          .slice(0, 3)
                          .map((v) => v?.toFixed(1))
                          .join("/")}
                        mm
                      </span>
                    )}
                    {img.volume_count != null && <span>{img.volume_count}v</span>}
                    <span
                      style={{
                        ...pill,
                        background: img.readable ? "#e8f5e9" : "#ffebee",
                        color: img.readable ? "#176b3b" : "#b53b3b",
                        borderColor: img.readable ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)",
                      }}
                    >
                      {img.readable ? "✓" : "✗"}
                    </span>
                    {img.warnings.length > 0 && (
                      <span style={{ color: "#9a5a15" }}>⚠{img.warnings.length}</span>
                    )}
                  </div>

                  {/* Path */}
                  <div style={mono}>{img.relative_path || img.path}</div>

                  <button
                    onClick={() =>
                      setExpanded((p) => {
                        const n = new Set(p);
                        if (isExpanded) n.delete(key);
                        else n.add(key);
                        return n;
                      })
                    }
                    style={{ fontSize: 11, fontWeight: 600 }}
                  >
                    {isExpanded
                      ? t("technical.NiftiQcSnapshot.hideDetails")
                      : t("technical.NiftiQcSnapshot.showDetails")}
                  </button>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div style={{ display: "grid", gap: 3, marginTop: 4 }}>
                      {/* Lazy thumbnail loader */}
                      <ThumbnailLoader
                        effectiveBase={effectiveBase}
                        projectId={projectId}
                        imageId={img.image_id}
                      />
                      {img.path !== img.relative_path && (
                        <div>
                          <b>path:</b> <span style={mono}>{img.path}</span>
                        </div>
                      )}
                      {img.dtype && (
                        <div>
                          <b>dtype:</b> {img.dtype}
                        </div>
                      )}
                      {img.orientation && (
                        <div>
                          <b>orientation:</b> {img.orientation}
                        </div>
                      )}
                      {img.affine_determinant != null && (
                        <div>
                          <b>affine det:</b> {img.affine_determinant.toFixed(4)}
                        </div>
                      )}
                      {img.ndim != null && (
                        <div>
                          <b>ndim:</b> {img.ndim}
                        </div>
                      )}

                      {/* Intensity stats */}
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr 1fr",
                          gap: 2,
                          marginTop: 2,
                        }}
                      >
                        <span>
                          <b>min:</b>{" "}
                          {img.intensity_min != null ? img.intensity_min.toFixed(2) : "—"}
                        </span>
                        <span>
                          <b>max:</b>{" "}
                          {img.intensity_max != null ? img.intensity_max.toFixed(2) : "—"}
                        </span>
                        <span>
                          <b>mean:</b>{" "}
                          {img.intensity_mean != null ? img.intensity_mean.toFixed(2) : "—"}
                        </span>
                        <span>
                          <b>std:</b>{" "}
                          {img.intensity_std != null ? img.intensity_std.toFixed(2) : "—"}
                        </span>
                        <span>
                          <b>zero%:</b>{" "}
                          {img.zero_fraction != null ? (100 * img.zero_fraction).toFixed(1) : "—"}
                        </span>
                        <span>
                          <b>NaN:</b> {img.nan_count}
                        </span>
                      </div>

                      {img.warnings.length > 0 && (
                        <div
                          style={{
                            marginTop: 4,
                            padding: 4,
                            border: "1px solid rgba(242,153,74,0.24)",
                            borderRadius: 4,
                            background: "rgba(255,251,242,0.94)",
                            color: "#9a5a15",
                            fontSize: 10,
                          }}
                        >
                          {img.warnings.map((w, i) => (
                            <div key={i}>{w}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data.warnings.length > 0 && <Warn items={data.warnings} />}
      {data.errors.length > 0 && (
        <div className="errorBox" style={{ marginBottom: 8 }}>
          {data.errors.join("\n")}
        </div>
      )}
      {data.next_actions.length > 0 && (
        <div>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>
            {t("technical.BoldReferenceReadiness.011")}
          </h4>
          <ActionList actions={data.next_actions} rawDicom={niftiNotApplicable} />
        </div>
      )}
    </Sec>
  );
}

function Warn({ items }: { items: string[] }) {
  return (
    <div
      style={{
        marginTop: 4,
        padding: 6,
        border: "1px solid rgba(242,153,74,0.24)",
        borderRadius: 4,
        background: "rgba(255,251,242,0.94)",
        color: "#9a5a15",
        fontSize: 11,
      }}
    >
      {items.slice(0, 3).map((w, i) => (
        <div key={i}>{w}</div>
      ))}
    </div>
  );
}
// ── Per-image thumbnail loader (lazy) ───────────────────────────────────────

function ThumbnailLoader({
  effectiveBase,
  projectId,
  imageId,
}: {
  effectiveBase: string;
  projectId: string;
  imageId: string;
}) {
  const { t } = useI18n();
  const [thumbs, setThumbs] = useState<Array<Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  if (thumbs) {
    return (
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
        {thumbs.map((t, i) => (
          <div key={i} style={{ textAlign: "center", fontSize: 9, color: "#667085" }}>
            <img
              src={`data:image/png;base64,${t.png_base64}`}
              alt={String(t.view)}
              style={{
                width: "auto",
                height: 80,
                borderRadius: 3,
                border: "1px solid rgba(137,150,171,0.2)",
              }}
            />
            <div>
              {String(t.view)} s{Number(t.slice_index)}
            </div>
          </div>
        ))}
        {thumbs.length === 0 && (
          <span style={{ fontSize: 10, color: "#9a5a15" }}>
            {t("technical.NiftiQcSnapshot.008")}
          </span>
        )}
      </div>
    );
  }

  if (loading)
    return (
      <button disabled style={{ fontSize: 11 }}>
        {t("technical.NiftiQcSnapshot.009")}
      </button>
    );
  if (err) return <div style={{ fontSize: 10, color: "#b53b3b" }}>{err}</div>;

  return (
    <button
      onClick={async () => {
        setLoading(true);
        setErr("");
        try {
          const d = await getProjectNiftiThumbnail(effectiveBase, projectId, imageId, {
            view: "all",
          });
          setThumbs((d.thumbnails as unknown as Array<Record<string, unknown>>) ?? []);
        } catch (e) {
          setErr(e instanceof Error ? e.message : String(e));
        } finally {
          setLoading(false);
        }
      }}
      style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px" }}
    >
      {t("technical.NiftiQcSnapshot.loadCentralSlices")}
    </button>
  );
}

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <section
    style={{
      padding: 16,
      border: "1px solid rgba(137,150,171,0.28)",
      borderRadius: 8,
      background: "rgba(255,255,255,0.88)",
      marginTop: 4,
    }}
  >
    {children}
  </section>
);
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>
);
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>
);
