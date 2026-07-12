import type { RsfmriQcPlanningReportResponse } from "../../types";
import { requestJson } from "./legacyCore";

export async function generateRsfmriQcPlanningReport(baseUrl: string, projectId: string) {
  return requestJson<RsfmriQcPlanningReportResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/rsfmri-qc/planning-report`,
    { method: "POST" },
  );
}

export async function getLatestRsfmriReportExport(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-exports/latest");
}

export async function getLatestRsfmriReportValidation(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-validations/latest");
}

export async function getRsfmriAlffFalff(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/alff-falff");
}

export async function getRsfmriCoregistrationQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/coregistration-qc");
}

export async function getRsfmriFunctionalConnectivity(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/functional-connectivity");
}

export async function getRsfmriGroupSummary(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/group-summary");
}

export async function getRsfmriNormalizationQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/normalization-qc");
}

export async function getRsfmriNuisanceRegression(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/nuisance-regression");
}

export async function getRsfmriPreprocessingPlan(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/preprocessing-plan");
}

export async function getRsfmriReho(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/reho");
}

export async function getRsfmriSegmentationTissueQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/segmentation-tissue-qc");
}

export async function getRsfmriSmoothingQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/smoothing-qc");
}

export async function getRsfmriSpmRealignMotionQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/spm-realign-motion-qc");
}

export async function getRsfmriSpmSliceTiming(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/spm-slice-timing");
}

export async function getRsfmriStRealignMotionQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/st-realign-motion-qc");
}

export async function getRsfmriTemporalFiltering(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/temporal-filtering");
}

export async function listRsfmriReportExports(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-exports");
}

export async function listRsfmriReportValidations(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-validations");
}

export async function refreshRsfmriPreprocessingPlan(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/preprocessing-plan/refresh", {
    method: "POST",
  });
}

export async function runRsfmriAlffFalff(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string; approved: boolean },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/alff-falff/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriCoregistrationQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/coregistration-qc/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriFunctionalConnectivity(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string; approved: boolean },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/functional-connectivity/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriGroupSummary(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/group-summary/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriNormalizationQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/normalization-qc/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriNuisanceRegression(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string; approved: boolean },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/nuisance-regression/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriReho(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string; approved: boolean },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/reho/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriReportExport(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-export", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriReportValidation(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-validation", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriSegmentationTissueQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/segmentation-tissue-qc/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriSmoothingQc(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string; approved: boolean },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/smoothing-qc/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriSpmRealignMotionQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/spm-realign-motion-qc/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriSpmSliceTiming(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/spm-slice-timing/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriStRealignMotionQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/st-realign-motion-qc/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runRsfmriTemporalFiltering(
  baseUrl: string,
  payload: { project_config_path: string; pipeline_path: string; approved: boolean },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/temporal-filtering/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
