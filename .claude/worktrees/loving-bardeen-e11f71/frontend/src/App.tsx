import { useEffect, useState } from "react";
import { getHealth, getProjectConfig } from "./api";
import { AgentControls } from "./components/AgentControls";
import { ErrorDiagnosis } from "./components/ErrorDiagnosis";
import { RsfmriMotionQcPanel } from "./components/RsfmriMotionQcPanel";
import { RsfmriSliceTimingPanel } from "./components/RsfmriSliceTimingPanel";
import { RsfmriCoregistrationQcPanel } from "./components/RsfmriCoregistrationQcPanel";
import { RsfmriNormalizationQcPanel } from "./components/RsfmriNormalizationQcPanel";
import { RsfmriNuisanceRegressionPanel } from "./components/RsfmriNuisanceRegressionPanel";
import { RsfmriAlffFalffPanel } from "./components/RsfmriAlffFalffPanel";
import { RsfmriFunctionalConnectivityPanel } from "./components/RsfmriFunctionalConnectivityPanel";
import { RsfmriGroupSummaryPanel } from "./components/RsfmriGroupSummaryPanel";
import { RsfmriReportExporterPanel } from "./components/RsfmriReportExporterPanel";
import { RsfmriReleaseReadinessPanel } from "./components/RsfmriReleaseReadinessPanel";
import { RsfmriReportValidatorPanel } from "./components/RsfmriReportValidatorPanel";
import { RsfmriRehoPanel } from "./components/RsfmriRehoPanel";
import { RsfmriTemporalFilteringPanel } from "./components/RsfmriTemporalFilteringPanel";
import { RsfmriSmoothingQcPanel } from "./components/RsfmriSmoothingQcPanel";
import { RsfmriSegmentationTissueQcPanel } from "./components/RsfmriSegmentationTissueQcPanel";
import { RsfmriStRealignMotionChainPanel } from "./components/RsfmriStRealignMotionChainPanel";
import { RsfmriPreprocessingPlanPanel } from "./components/RsfmriPreprocessingPlanPanel";
import { JsonBlock } from "./components/JsonBlock";
import { PipelineExplorer } from "./components/PipelineExplorer";
import { ReportViewer } from "./components/ReportViewer";
import { RunMonitor } from "./components/RunMonitor";
import { Section } from "./components/Section";
import { StatusBadge } from "./components/StatusBadge";
import { TextViewer } from "./components/TextViewer";
import type { AgentRun } from "./types";

export default function App() {
  const baseUrl = "http://127.0.0.1:8000";
  const [health, setHealth] = useState<unknown>(null);
  const [projectConfig, setProjectConfig] = useState<unknown>(null);
  const [selectedPipeline, setSelectedPipeline] = useState<string>("");
  const [agentRun, setAgentRun] = useState<AgentRun | null>(null);
  const [error, setError] = useState<string>("");

  async function refreshHealth() {
    setError("");
    try {
      const result = await getHealth(baseUrl);
      setHealth(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function refreshProjectConfig() {
    setError("");
    try {
      const result = await getProjectConfig(baseUrl);
      setProjectConfig(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refreshHealth();
    refreshProjectConfig();
  }, []);

  return (
    <div className="container">
      <header className="header">
        <h1>MedImage Agent</h1>
        <p>最小可视化前端 MVP</p>
      </header>

      {error ? <div className="errorBox">{error}</div> : null}

      <Section title="API 状态" description="后端服务健康检查">
        <div className="row">
          <button onClick={refreshHealth}>刷新</button>
          <StatusBadge status={health ? "HEALTHY" : "UNKNOWN"} />
        </div>
        <JsonBlock value={health} emptyText="未获取到健康状态" />
      </Section>

      <Section title="项目配置" description="当前项目配置">
        <div className="row">
          <button onClick={refreshProjectConfig}>刷新</button>
        </div>
        <JsonBlock value={projectConfig} emptyText="未获取到配置" />
      </Section>

      <Section title="Pipeline 浏览器" description="查看可用的 pipeline">
        <PipelineExplorer
          baseUrl={baseUrl}
          selectedPipeline={selectedPipeline}
          onSelectPipeline={setSelectedPipeline}
        />
      </Section>

      <Section title="Agent 控制" description="创建 Plan 并执行 Pipeline">
        <AgentControls
          baseUrl={baseUrl}
          selectedPipeline={selectedPipeline}
          onAgentRunLoaded={(value) => setAgentRun(value as AgentRun | null)}
        />
      </Section>

      <Section title="Agent Run 汇总" description="查看 Plan、执行结果、复盘">
        <h3>Review Summary</h3>
        <TextViewer text={agentRun?.review_summary} emptyText="暂无复盘摘要" />

        <h3>Proposed Memory Patch</h3>
        <TextViewer text={agentRun?.proposed_memory_patch} emptyText="暂无记忆补丁建议" />
      </Section>

      <Section
        title="rs-fMRI Core Preprocessing Plan"
        description="Define rs-fMRI preprocessing protocol, step registry, DAG, parameter schema, QC metrics, and safety constraints."
      >
        <RsfmriPreprocessingPlanPanel baseUrl={baseUrl} />
      </Section>

      <Section
        title="rs-fMRI SPM Slice Timing + Metadata QC"
        description="Execute SPM slice timing correction on synthetic rs-fMRI BOLD and validate TR, SliceTiming, and slice order."
      >
        <RsfmriSliceTimingPanel baseUrl={baseUrl} />
      </Section>

      <Section
        title="rs-fMRI SPM Realignment + Motion QC"
        description="Execute SPM realign on synthetic rs-fMRI BOLD and compute FD and other motion QC metrics."
      >
        <RsfmriMotionQcPanel baseUrl={baseUrl} />
      </Section>

      <Section
        title="rs-fMRI Slice Timing → Realignment → Motion QC"
        description="Chain SPM slice timing output into SPM realignment and generate motion QC chain report."
      >
        <RsfmriStRealignMotionChainPanel baseUrl={baseUrl} />
      </Section>

      <Section
        title="rs-fMRI SPM Coregistration + Registration QC"
        description="Use mean functional image and synthetic T1w to run SPM coregistration and generate registration QC."
      >
        <RsfmriCoregistrationQcPanel baseUrl={baseUrl} />
      </Section>

      <Section
        title="rs-fMRI SPM Segmentation + Tissue QC"
        description="Run SPM segmentation on coregistered synthetic T1w and generate GM/WM/CSF tissue QC."
      >
        <RsfmriSegmentationTissueQcPanel baseUrl={baseUrl} />
      </Section>

      <Section
        title="rs-fMRI SPM Normalization + Normalization QC"
        description="Use segmentation deformation field to normalize realigned functional image and generate normalization QC."
      >
        <RsfmriNormalizationQcPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI SPM Smoothing + Smoothing QC" description="Apply SPM spatial smoothing to normalized functional images and generate smoothing QC.">
        <RsfmriSmoothingQcPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI Nuisance Regression" description="Build Friston24 confound matrix and run Python nuisance regression on smoothed derivatives. Generates DPABI backend contract without execution.">
        <RsfmriNuisanceRegressionPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI Temporal Filtering" description="Apply Python FFT band-pass filtering to nuisance-regressed derivatives. Generates DPABI backend contract without execution.">
        <RsfmriTemporalFilteringPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI ALFF / fALFF" description="Compute ALFF/fALFF metric maps from filtered derivatives. Generates GPU candidate and DPABI backend contracts without execution.">
        <RsfmriAlffFalffPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI ReHo" description="Compute Regional Homogeneity (KCC) from filtered derivatives. Generates GPU candidate and DPABI backend contracts without execution.">
        <RsfmriRehoPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI Functional Connectivity" description="Extract ROI time series and compute ROI-to-ROI correlation/Fisher-z matrices. Generates GPU candidate and DPABI backend contracts without execution.">
        <RsfmriFunctionalConnectivityPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI Group Dataset Dashboard" description="Read-only aggregation of all subject-level QC, metrics, pipeline runs, and backend contracts into a group-level dashboard.">
        <RsfmriGroupSummaryPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI Report Exporter" description="Package existing JSON/Markdown/CSV/TSV results into a ZIP report package with manifest and SHA256 checksums.">
        <RsfmriReportExporterPanel baseUrl={baseUrl} />
      </Section>

      <Section title="rs-fMRI Report Package Validator" description="Validate exported report package integrity, checksums, ZIP consistency, and safety declarations.">
        <RsfmriReportValidatorPanel baseUrl={baseUrl} />
      </Section>

      <Section title="Project Release Readiness" description="Audit project structure, specs, backend, pipelines, API, frontend, tests, docs, and safety for MVP release readiness.">
        <RsfmriReleaseReadinessPanel baseUrl={baseUrl} />
      </Section>

      <Section title="Run Monitor" description="查看 pipeline summary、project-level state、subject-level state 和日志">
        <RunMonitor baseUrl={baseUrl} />
      </Section>

      <Section title="错误诊断" description="分析运行错误、匹配已知模式、生成重试建议">
        <ErrorDiagnosis baseUrl={baseUrl} />
      </Section>

      <Section title="数据集评估报告" description="查看 QC 报告和推荐">
        <ReportViewer baseUrl={baseUrl} />
      </Section>

      <footer className="footer">
        <p>MedImage Agent MVP - 仅供工程 QC 和预处理研究使用</p>
      </footer>
    </div>
  );
}
