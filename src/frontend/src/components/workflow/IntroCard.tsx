import React from "react";

export function IntroCard({ onStart }: { onStart: () => void }) {
  return (
    <div style={{ textAlign: "center", padding: "40px 20px" }}>
      <h1 style={{ fontSize: 28, marginBottom: 12 }}>MedImage Agent</h1>
      <p style={{ fontSize: 16, color: "#555", maxWidth: 600, margin: "0 auto 24px", lineHeight: 1.6 }}>
        A visual, reproducible preprocessing platform for rs-fMRI data.
        Supports SPM, DPABI, and Python-based pipelines with automatic QC,
        dataset evaluation, and report generation.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, maxWidth: 700, margin: "0 auto 32px" }}>
        {[
          { title: "Upload Data", desc: "BIDS / DICOM / NIfTI datasets" },
          { title: "Configure Pipeline", desc: "Choose preprocessing + analysis steps" },
          { title: "Run Processing", desc: "SPM, DPABI, or Python-only backends" },
          { title: "Review Results", desc: "QC reports, metrics, and export packages" },
        ].map((item) => (
          <div key={item.title} style={{ padding: 16, background: "#f5f5f5", borderRadius: 8, border: "1px solid #eee" }}>
            <div style={{ fontWeight: 700, marginBottom: 4, color: "#1976d2" }}>{item.title}</div>
            <div style={{ fontSize: 13, color: "#777" }}>{item.desc}</div>
          </div>
        ))}
      </div>

      <button onClick={onStart} style={btnPrimary}>
        Start New Project
      </button>

      <div style={{ marginTop: 24, fontSize: 12, color: "#999" }}>
        Backend: <a href="http://127.0.0.1:8000/health" target="_blank" style={{ color: "#1976d2" }}>http://127.0.0.1:8000</a>
      </div>
    </div>
  );
}

const btnPrimary: React.CSSProperties = {
  padding: "12px 32px", fontSize: 16, fontWeight: 700,
  background: "#1976d2", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer",
};
