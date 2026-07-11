import { useCallback, useEffect, useState } from "react";
import {
  prepareProjectDicomConversion,
  type DicomConversionPrepareConfirmations,
  type DicomConversionPrepareRequest,
} from "../lib/api/dicom";
import type { DicomConversionPrepareResponse, DicomConversionPrepareStatus } from "../types";

function emptyConfirmations(): DicomConversionPrepareConfirmations {
  return {
    mappings_reviewed: false,
    rawdata_readonly: false,
    research_use_only: false,
    no_clinical_use: false,
    external_converter: false,
    rollback_policy: false,
    risk_acknowledgement: false,
    approval_audit: false,
    public_endpoint: false,
    frontend_execute: false,
    spm_dpabi_matlab_disabled: false,
    confirm_execution: false,
  };
}

/**
 * 实现dcm2nii任务方案.md §16 — DICOM conversion workflow hook.
 *
 * Orchestrates the prepare → review → execute flow:
 *   1. ``prepare()`` calls the unified backend endpoint to validate all
 *      system preconditions and persist the approval package.
 *   2. The UI reviews the returned readiness state and operator
 *      confirmations.
 *   3. Once ``execution_ready`` is true, the caller may invoke the
 *      existing execute endpoint (handled separately by the execute
 *      panel) using the reserved ``conversion_run_id``.
 *
 * The hook intentionally keeps operator confirmations as the single
 * source of truth for user-side acknowledgements; system-verifiable
 * fields are never stored here.
 */
export function useDicomConversionWorkflow(
  baseUrl: string,
  projectId: string,
  initialConversionRunId: string = "",
) {
  const [prepareResponse, setPrepareResponse] = useState<DicomConversionPrepareResponse | null>(
    null,
  );
  const [conversionRunId, setConversionRunId] = useState<string>(initialConversionRunId);
  const [confirmations, setConfirmations] =
    useState<DicomConversionPrepareConfirmations>(emptyConfirmations);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");

  const status: DicomConversionPrepareStatus = prepareResponse?.status ?? "blocked";
  const technicalReady = prepareResponse?.technical_ready ?? false;
  const approvalReady = prepareResponse?.approval_ready ?? false;
  const executionReady = prepareResponse?.execution_ready ?? false;
  const nextAction = prepareResponse?.next_action ?? "review_conversion_plan";
  const blockingIssues = prepareResponse?.blocking_issues ?? [];
  const missingConfirmations = prepareResponse?.missing_confirmations ?? [];
  const warnings = prepareResponse?.warnings ?? [];

  const toggleConfirmation = useCallback((key: keyof DicomConversionPrepareConfirmations) => {
    setConfirmations((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const setAllConfirmations = useCallback((value: boolean) => {
    setConfirmations({
      mappings_reviewed: value,
      rawdata_readonly: value,
      research_use_only: value,
      no_clinical_use: value,
      external_converter: value,
      rollback_policy: value,
      risk_acknowledgement: value,
      approval_audit: value,
      public_endpoint: value,
      frontend_execute: value,
      spm_dpabi_matlab_disabled: value,
      confirm_execution: value,
    });
  }, []);

  const prepare = useCallback(async (): Promise<DicomConversionPrepareResponse | null> => {
    if (submitting) return null;
    setSubmitting(true);
    setError("");
    try {
      const payload: DicomConversionPrepareRequest = {
        approved_by: "operator",
        selected_mapping_ids: [],
        overwrite_policy: "fail_if_exists",
        confirmations,
      };
      const resp = await prepareProjectDicomConversion(baseUrl, projectId, payload);
      setPrepareResponse(resp);
      if (resp.conversion_run_id) {
        setConversionRunId(resp.conversion_run_id);
      }
      return resp;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setSubmitting(false);
    }
  }, [baseUrl, projectId, confirmations, submitting]);

  // Reset operator state only when the project changes.  A successful prepare
  // returns a new conversion_run_id which the parent passes back into this
  // hook; treating that as a full reset erases the prepared response and makes
  // the UI look unchanged after the operator clicks "Prepare conversion".
  useEffect(() => {
    setPrepareResponse(null);
    setConversionRunId(initialConversionRunId);
    setError("");
    setConfirmations(emptyConfirmations());
  }, [projectId]);

  useEffect(() => {
    if (!initialConversionRunId) return;
    setConversionRunId((current) => current || initialConversionRunId);
  }, [initialConversionRunId]);

  return {
    // State
    prepareResponse,
    conversionRunId,
    confirmations,
    submitting,
    error,
    // Derived
    status,
    technicalReady,
    approvalReady,
    executionReady,
    nextAction,
    blockingIssues,
    missingConfirmations,
    warnings,
    // Actions
    prepare,
    toggleConfirmation,
    setAllConfirmations,
    setConversionRunId,
  };
}

export type UseDicomConversionWorkflow = ReturnType<typeof useDicomConversionWorkflow>;
