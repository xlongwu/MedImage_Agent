import { useCallback, useEffect, useState } from "react";
import {
  prepareProjectDicomConversion,
  type DicomConversionPrepareConfirmations,
  type DicomConversionPrepareRequest,
} from "../lib/api/dicom";
import type { DicomConversionPrepareResponse, DicomConversionPrepareStatus } from "../types";

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
  const [confirmations, setConfirmations] = useState<DicomConversionPrepareConfirmations>({
    mappings_reviewed: false,
    rawdata_readonly: false,
    research_use_only: false,
    no_clinical_use: false,
    external_converter: false,
    rollback_policy: false,
    risk_acknowledgement: false,
    confirm_execution: false,
  });
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
      confirm_execution: value,
    });
  }, []);

  const prepare = useCallback(async () => {
    if (submitting) return;
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
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }, [baseUrl, projectId, confirmations, submitting]);

  // Reset state when project changes
  useEffect(() => {
    setPrepareResponse(null);
    setConversionRunId(initialConversionRunId);
    setError("");
    setConfirmations({
      mappings_reviewed: false,
      rawdata_readonly: false,
      research_use_only: false,
      no_clinical_use: false,
      external_converter: false,
      rollback_policy: false,
      risk_acknowledgement: false,
      confirm_execution: false,
    });
  }, [projectId, initialConversionRunId]);

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
