import type {
  BidsValidationResponse,
  ConversionDryRunRequest,
  ConversionDryRunResponse,
  DataReadinessResponse,
} from "../../types";
import { requestJson } from "./legacyCore";

export async function getDicomPreflight(
  baseUrl: string,
  projectId: string,
  path = "",
  maxFiles = 2000,
) {
  const params = new URLSearchParams({
    project_id: projectId,
    max_files: String(maxFiles),
  });
  if (path.trim()) {
    params.set("path", path.trim());
  }
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/dicom/preflight?${params.toString()}`,
  );
}

export async function getProjectBidsValidation(baseUrl: string, projectId: string) {
  return requestJson<BidsValidationResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/bids-validation`,
  );
}

export async function getProjectDataReadiness(baseUrl: string, projectId: string) {
  return requestJson<DataReadinessResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/data-readiness`,
  );
}

export async function getProjectDicomConversionReleaseReadiness(
  baseUrl: string,
  projectId: string,
  conversionRunId: string,
) {
  return requestJson<import("../../types").DicomConversionReleaseReadinessReport>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/release-readiness/${encodeURIComponent(conversionRunId)}`,
  );
}

export async function persistProjectDicomConversionPlan(
  baseUrl: string,
  projectId: string,
  body: Record<string, unknown>,
) {
  return requestJson<import("../../types").DicomConversionPlanPersistenceResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/approval/persist-plan`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function runConversionDryRun(
  baseUrl: string,
  projectId: string,
  payload?: ConversionDryRunRequest,
) {
  return requestJson<ConversionDryRunResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/dry-run`,
    { method: "POST", body: JSON.stringify(payload ?? {}) },
  );
}

export async function getLatestConversionDryRun(baseUrl: string, projectId: string) {
  return requestJson<ConversionDryRunResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/dry-run/latest`,
  );
}

export async function runProjectDicomConversionExecute(
  baseUrl: string,
  projectId: string,
  body: Record<string, unknown>,
) {
  return requestJson<import("../../types").DicomConversionPublicExecutionResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/execute`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function runProjectDicomConversionPreflight(baseUrl: string, projectId: string) {
  return requestJson<import("../../types").DicomConversionPreflightResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/preflight`,
    { method: "POST" },
  );
}

// ── Prepare (unified approval + execution preparation) ────────────────────
// Per 实现dcm2nii任务方案.md §13, this is the canonical single-call
// orchestration endpoint that performs all preparation steps and returns
// the authoritative readiness state.

export interface DicomConversionPrepareConfirmations {
  mappings_reviewed: boolean;
  rawdata_readonly: boolean;
  research_use_only: boolean;
  no_clinical_use: boolean;
  native_converter: boolean;
  external_converter?: boolean;
  rollback_policy: boolean;
  risk_acknowledgement: boolean;
  approval_audit: boolean;
  public_endpoint: boolean;
  frontend_execute: boolean;
  spm_dpabi_matlab_disabled: boolean;
  confirm_execution: boolean;
}

export interface DicomConversionPrepareRequest {
  approved_by?: string;
  selected_mapping_ids?: string[];
  overwrite_policy?: string;
  confirmations: DicomConversionPrepareConfirmations;
}

export async function prepareProjectDicomConversion(
  baseUrl: string,
  projectId: string,
  payload: DicomConversionPrepareRequest,
) {
  return requestJson<import("../../types").DicomConversionPrepareResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/dicom-conversion/prepare`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

// ── Result registration (实现dcm2nii任务方案.md §17) ──────────────────────
// Registers successful conversion outputs into project metadata so that
// Dashboard, Viewer, and project state can refresh automatically.

export interface DicomConversionResultRegistrationRequest {
  conversion_run_id: string;
  output_root: string;
  execution_status?: string;
  mapping_count?: number;
  nifti_count?: number;
  bold_count?: number;
  t1w_count?: number;
  subject_count?: number;
  manifest_path?: string | null;
  provenance_path?: string | null;
  checksum_verified?: boolean;
}

export async function registerProjectDicomConversionResult(
  baseUrl: string,
  projectId: string,
  payload: DicomConversionResultRegistrationRequest,
) {
  return requestJson<import("../../types").DicomConversionResultRegistrationResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/dicom-conversion/register-result`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}
