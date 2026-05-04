import React, { useState } from "react";
import { AgentControls } from "../AgentControls";
import { ErrorDiagnosis } from "../ErrorDiagnosis";
import { RsfmriMotionQcPanel } from "../RsfmriMotionQcPanel";
import { RsfmriSliceTimingPanel } from "../RsfmriSliceTimingPanel";
import { RsfmriCoregistrationQcPanel } from "../RsfmriCoregistrationQcPanel";
import { RsfmriNormalizationQcPanel } from "../RsfmriNormalizationQcPanel";
import { RsfmriNuisanceRegressionPanel } from "../RsfmriNuisanceRegressionPanel";
import { RsfmriAlffFalffPanel } from "../RsfmriAlffFalffPanel";
import { RsfmriFunctionalConnectivityPanel } from "../RsfmriFunctionalConnectivityPanel";
import { RsfmriGroupSummaryPanel } from "../RsfmriGroupSummaryPanel";
import { RsfmriReportExporterPanel } from "../RsfmriReportExporterPanel";
import { RsfmriReleaseReadinessPanel } from "../RsfmriReleaseReadinessPanel";
import { RsfmriReportValidatorPanel } from "../RsfmriReportValidatorPanel";
import { RsfmriRehoPanel } from "../RsfmriRehoPanel";
import { RsfmriTemporalFilteringPanel } from "../RsfmriTemporalFilteringPanel";
import { RsfmriSmoothingQcPanel } from "../RsfmriSmoothingQcPanel";
import { RsfmriSegmentationTissueQcPanel } from "../RsfmriSegmentationTissueQcPanel";
import { RsfmriStRealignMotionChainPanel } from "../RsfmriStRealignMotionChainPanel";
import { RsfmriPreprocessingPlanPanel } from "../RsfmriPreprocessingPlanPanel";
import { PipelineExplorer } from "../PipelineExplorer";
import { ReportViewer } from "../ReportViewer";
import { RunMonitor } from "../RunMonitor";
import { StatusBadge } from "../StatusBadge";
import { TextViewer } from "../TextViewer";
import { JsonBlock } from "../JsonBlock";
import { Section } from "../Section";
import SessionMemoryBrowserPanel from "../SessionMemoryBrowserPanel";
import InsightsDashboardPanel from "../InsightsDashboardPanel";
import AdvisorCenterPanel from "../AdvisorCenterPanel";

interface Props { baseUrl: string; }

const MENU = [
  { id: "system", label: "System Status" },
  { id: "pipeline", label: "Pipeline & Agent" },
  { id: "preproc", label: "SPM Preprocessing" },
  { id: "postproc", label: "Post-Processing" },
  { id: "reports", label: "Reports & QC" },
  { id: "insights", label: "Memory & Insights" },
  { id: "release", label: "Docs & Release" },
];

export default function AdvancedModePanel({ baseUrl }: Props) {
  const [tab, setTab] = useState("system");
  const [selectedPipeline, setSelectedPipeline] = useState("");

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 60px)" }}>
      {/* Sidebar */}
      <div style={{ width: 200, background: "#263238", color: "#fff", padding: "12px 0", flexShrink: 0 }}>
        <div style={{ padding: "0 16px 12px", fontWeight: 700, fontSize: 14, borderBottom: "1px solid #37474f", marginBottom: 8 }}>
          Advanced Mode
        </div>
        {MENU.map((item) => (
          <div
            key={item.id}
            onClick={() => setTab(item.id)}
            style={{
              padding: "8px 16px", cursor: "pointer", fontSize: 13,
              background: tab === item.id ? "#37474f" : "transparent",
              borderLeft: tab === item.id ? "3px solid #4caf50" : "3px solid transparent",
            }}
          >
            {item.label}
          </div>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: 16, overflow: "auto", maxHeight: "calc(100vh - 60px)" }}>
        {tab === "system" && (
          <>
            <Section title="API Health"><StatusBadge status="HEALTHY" /></Section>
            <Section title="Pipeline Explorer"><PipelineExplorer baseUrl={baseUrl} selectedPipeline={selectedPipeline} onSelectPipeline={setSelectedPipeline} /></Section>
            <Section title="Run Monitor"><RunMonitor baseUrl={baseUrl} /></Section>
          </>
        )}
        {tab === "pipeline" && (
          <>
            <Section title="Agent Controls"><AgentControls baseUrl={baseUrl} selectedPipeline={selectedPipeline} onAgentRunLoaded={() => {}} /></Section>
            <Section title="rs-fMRI Preprocessing Plan"><RsfmriPreprocessingPlanPanel baseUrl={baseUrl} /></Section>
            <Section title="Error Diagnosis"><ErrorDiagnosis baseUrl={baseUrl} /></Section>
          </>
        )}
        {tab === "preproc" && (
          <>
            <Section title="SPM Slice Timing + Motion QC"><RsfmriSliceTimingPanel baseUrl={baseUrl} /></Section>
            <Section title="SPM Realign + Motion Chain"><RsfmriStRealignMotionChainPanel baseUrl={baseUrl} /></Section>
            <Section title="SPM Coregistration QC"><RsfmriCoregistrationQcPanel baseUrl={baseUrl} /></Section>
            <Section title="SPM Segmentation Tissue QC"><RsfmriSegmentationTissueQcPanel baseUrl={baseUrl} /></Section>
            <Section title="SPM Normalization QC"><RsfmriNormalizationQcPanel baseUrl={baseUrl} /></Section>
            <Section title="SPM Smoothing QC"><RsfmriSmoothingQcPanel baseUrl={baseUrl} /></Section>
          </>
        )}
        {tab === "postproc" && (
          <>
            <Section title="Nuisance Regression"><RsfmriNuisanceRegressionPanel baseUrl={baseUrl} /></Section>
            <Section title="Temporal Filtering"><RsfmriTemporalFilteringPanel baseUrl={baseUrl} /></Section>
            <Section title="ALFF / fALFF"><RsfmriAlffFalffPanel baseUrl={baseUrl} /></Section>
            <Section title="ReHo"><RsfmriRehoPanel baseUrl={baseUrl} /></Section>
            <Section title="Functional Connectivity"><RsfmriFunctionalConnectivityPanel baseUrl={baseUrl} /></Section>
            <Section title="Motion QC"><RsfmriMotionQcPanel baseUrl={baseUrl} /></Section>
          </>
        )}
        {tab === "reports" && (
          <>
            <Section title="Group Summary"><RsfmriGroupSummaryPanel baseUrl={baseUrl} /></Section>
            <Section title="Report Exporter"><RsfmriReportExporterPanel baseUrl={baseUrl} /></Section>
            <Section title="Report Validator"><RsfmriReportValidatorPanel baseUrl={baseUrl} /></Section>
            <Section title="Report Viewer"><ReportViewer baseUrl={baseUrl} /></Section>
          </>
        )}
        {tab === "insights" && (
          <>
            <Section title="Insights Dashboard"><InsightsDashboardPanel baseUrl={baseUrl} /></Section>
            <Section title="Session Memory"><SessionMemoryBrowserPanel baseUrl={baseUrl} /></Section>
            <Section title="Advisor Center"><AdvisorCenterPanel baseUrl={baseUrl} /></Section>
          </>
        )}
        {tab === "release" && (
          <>
            <Section title="Release Readiness"><RsfmriReleaseReadinessPanel baseUrl={baseUrl} /></Section>
          </>
        )}
      </div>
    </div>
  );
}
