import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, getProjectDataReadiness } from "../lib/api/legacy";
import type { DataReadinessCheck, DataReadinessResponse } from "../types";
import { ActionList, CollapsibleDetails, MetricTile, SafetyBanner, StatusPill } from "./dashboardUi";

type Props = {
  baseUrl?: string;
  projectId: string | null;
  projectState?: string;
};

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};

const checkStatusPill: Record<string, React.CSSProperties> = {
  pass: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  fail: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};

const pill: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 24,
  padding: "0 8px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 900,
};

const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

function CheckRow({ check, hasDicom }: { check: DataReadinessCheck; hasDicom?: boolean }) {
  const isImageValidationDowngrade =
    check.name === "image_validation" &&
    check.status === "warning" &&
    check.details.status === "fail" &&
    hasDicom;

  const displayDetails = { ...check.details };

  // For image_validation downgraded by DICOM detection, override inner status
  if (isImageValidationDowngrade) {
    displayDetails.status = "not_applicable";
  }

  // Hide has_dicom from import_records — it conflicts with dicom_preflight
  const isImportRecords = check.name === "import_records";
  if (isImportRecords && "has_dicom" in displayDetails) {
    delete (displayDetails as Record<string, unknown>).has_dicom;
  }

  return (
    <div style={{
      display: "grid", gap: 5, padding: 10,
      border: "1px solid rgba(137, 150, 171, 0.22)", borderRadius: 6, background: "#fff",
    }}>
      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ ...pill, ...checkStatusPill[check.status] }}>{check.status}</span>
        <strong style={{ fontSize: 13 }}>{check.name}</strong>
      </div>
      <div style={{ fontSize: 12, color: "#344054", lineHeight: 1.5 }}>{check.message}</div>

      {/* DICOM downgrade explanation */}
      {isImageValidationDowngrade && (
        <div style={{
          padding: "6px 8px", border: "1px solid rgba(56, 103, 214, 0.22)",
          borderRadius: 4, background: "rgba(239, 246, 255, 0.82)",
          color: "#2450a6", fontSize: 11,
        }}>
          NIfTI validation is deferred because this project contains raw DICOM data (FunRaw/T1Raw).
          Run Conversion Dry-Run first to plan DICOM-to-NIfTI conversion.
        </div>
      )}

      {/* image_source_discovery note for DICOM-only projects */}
      {check.name === "image_source_discovery" && hasDicom && (
        <div style={{
          padding: "6px 8px", border: "1px solid rgba(56, 103, 214, 0.22)",
          borderRadius: 4, background: "rgba(239, 246, 255, 0.82)",
          color: "#2450a6", fontSize: 11,
        }}>
          Subject/sequence counts above refer to direct NIfTI image sources only.
          DICOM raw sources were detected separately by DICOM preflight.
        </div>
      )}

      {Object.keys(displayDetails).length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "2px 8px", fontSize: 11, color: "#667085" }}>
          {Object.entries(displayDetails).map(([key, value]) => {
            const isNotApplicable =
              isImageValidationDowngrade && key === "status" && value === "not_applicable";
            return (
              <div key={key}>
                <span>{key}: </span>
                <b style={isNotApplicable ? { color: "#2450a6" } : undefined}>
                  {value === null ? "-" : String(value)}
                </b>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function DataReadinessPanel({ baseUrl, projectId, projectState }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<DataReadinessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestRef = useRef(0);

  useEffect(() => {
    if (!projectId) {
      setData(null);
      setError("");
      return;
    }
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoading(true);
    setError("");
    getProjectDataReadiness(effectiveBase, projectId)
      .then((res) => {
        if (requestId !== requestRef.current) return;
        setData(res);
      })
      .catch((err) => {
        if (requestId !== requestRef.current) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (requestId === requestRef.current) setLoading(false);
      });
  }, [effectiveBase, projectId]);

  if (!projectId) {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Data Readiness</h3>
        <div className="empty">Select a project to assess data readiness.</div>
      </section>
    );
  }

  if (loading) {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Data Readiness</h3>
        <div className="empty">Assessing data readiness...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Data Readiness</h3>
        <div className="errorBox">{error}</div>
      </section>
    );
  }

  if (!data) return null;

  const hasDicomRawLayout =
    data.dicom_file_count > 0 && data.image_source_count === 0;

  // Reorder next_actions: prioritise Conversion Dry-Run for DICOM projects
  const sortedActions = hasDicomRawLayout
    ? [
        ...data.next_actions.filter((a) =>
          a.toLowerCase().includes("conversion dry-run")
        ),
        ...data.next_actions.filter(
          (a) =>
            !a.toLowerCase().includes("conversion dry-run") &&
            !a.toLowerCase().includes("verify the imported directory contains nifti or dicom files")
        ),
      ]
    : data.next_actions;

  return (
    <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 15 }}>Data Readiness</h3>
          <span style={{ color: "#667085", fontSize: 12 }}>High-value project readiness summary.</span>
        </div>
        <StatusPill status={data.status} />
      </div>

      {hasDicomRawLayout && (
        <SafetyBanner tone="info">
          <strong>FunRaw / T1Raw DICOM rawdata detected.</strong>{" "}
          This is valid raw input. Converted NIfTI files are not available yet.
          Run <strong>Conversion Dry-Run</strong> before NIfTI QC or preprocessing.
        </SafetyBanner>
      )}

      {(() => {
        const filteredErrors = projectState === "converted_bids"
          ? data.errors.filter((e) => !e.toLowerCase().includes("rawdata"))
          : data.errors;
        const filteredWarnings = projectState === "converted_bids"
          ? data.warnings.filter((w) => !w.toLowerCase().includes("rawdata"))
          : data.warnings;

        return (
          <>
            {filteredErrors.length > 0 ? (
              <div className="errorBox" style={{ marginBottom: 10 }}>{filteredErrors.slice(0, 3).join("\n")}</div>
            ) : null}
            {filteredWarnings.length > 0 ? (
              <SafetyBanner tone="warning">
                {filteredWarnings.slice(0, 2).map((w, i) => <div key={i}>{w}</div>)}
                {filteredWarnings.length > 2 ? <div>+{filteredWarnings.length - 2} more in details</div> : null}
              </SafetyBanner>
            ) : null}
          </>
        );
      })()}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 8, marginBottom: 12 }}>
        <MetricTile label="rawdata exists" value={data.rawdata_dir ? "Yes" : "No"} tone={data.rawdata_dir ? "green" : (projectState === "converted_bids" ? "neutral" : "red")} />
        <MetricTile label="imports recorded" value={data.import_count} />
        <MetricTile label="DICOM preflight" value={data.dicom_file_count > 0 ? "Detected" : "No DICOM"} tone={data.dicom_file_count > 0 ? "blue" : "neutral"} />
        <MetricTile label="Raw DICOM candidates" value={hasDicomRawLayout ? "See preflight" : "N/A"} />
        <MetricTile label="Converted subjects" value={data.subject_count} tone={data.subject_count > 0 ? "green" : "neutral"} />
        <MetricTile label="Converted NIfTI status" value={data.image_source_count > 0 ? "Available" : "Not started"} tone={data.image_source_count > 0 ? "green" : "amber"} />
        <MetricTile label="DICOM files" value={data.dicom_file_count.toLocaleString()} />
        <MetricTile label="DICOM series" value={data.dicom_series_count} />
      </div>

      <CollapsibleDetails title="Detailed readiness checks" summary={`${data.checks.length} checks`}>
        <div style={{ display: "grid", gap: 8 }}>
          {data.checks.map((check) => (
            <CheckRow key={check.name} check={check} hasDicom={hasDicomRawLayout} />
          ))}
        </div>
      </CollapsibleDetails>

      <CollapsibleDetails title="Project paths" summary="rawdata, config, dataset index">
        <div style={{ display: "grid", gap: 6, fontSize: 11, color: "#667085" }}>
          <div><strong>rawdata:</strong> <span style={mono}>{data.rawdata_dir || "-"}</span></div>
          <div><strong>config path:</strong> <span style={mono}>{data.project_config_path || "-"}</span></div>
          <div><strong>dataset index:</strong> <span style={mono}>{data.dataset_index_path || "-"}</span></div>
        </div>
      </CollapsibleDetails>

      {sortedActions.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Next Actions</h4>
          <ActionList actions={sortedActions} rawDicom={hasDicomRawLayout} />
        </div>
      )}
    </section>
  );
}

const metricBox: React.CSSProperties = {
  padding: "8px 10px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6, background: "#fff",
  display: "grid", gap: 2,
  color: "#667085", fontSize: 11, fontWeight: 850,
};
