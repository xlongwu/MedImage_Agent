import { useEffect, useState } from "react";

import { getLatestQcDashboardReport } from "../../lib/api/qc";
import {
  getLatestNativeFullPreprocessingRun,
  getProjectBoldReferenceReadiness,
  getProjectMotionQcReadiness,
  getProjectNiftiQcSnapshot,
} from "../../lib/api/preprocessing";
import type {
  BoldReferenceReadinessResponse,
  MotionQcReadinessResponse,
  NativeFullPreprocResponse,
  NiftiQcSnapshotResponse,
  QcDashboardReportResponse,
} from "../../types";

export type QcOverviewEvidence = {
  boldReadiness: BoldReferenceReadinessResponse | null;
  loading: boolean;
  motionReadiness: MotionQcReadinessResponse | null;
  nativeRun: NativeFullPreprocResponse | null;
  niftiSnapshot: NiftiQcSnapshotResponse | null;
  qcReport: QcDashboardReportResponse | null;
};

const emptyEvidence: QcOverviewEvidence = {
  boldReadiness: null,
  loading: false,
  motionReadiness: null,
  nativeRun: null,
  niftiSnapshot: null,
  qcReport: null,
};

export function useQcEvidence(baseUrl: string, projectId: string): QcOverviewEvidence {
  const [state, setState] = useState<{ evidence: QcOverviewEvidence; projectId: string }>({
    evidence: emptyEvidence,
    projectId: "",
  });
  const evidence =
    state.projectId === projectId ? state.evidence : { ...emptyEvidence, loading: true };

  useEffect(() => {
    let cancelled = false;
    let pendingLoads = 5;
    const update = (partial: Partial<QcOverviewEvidence>) => {
      if (cancelled) return;
      pendingLoads -= 1;
      setState((current) => ({
        projectId,
        evidence: {
          ...(current.projectId === projectId
            ? current.evidence
            : { ...emptyEvidence, loading: true }),
          ...partial,
          loading: pendingLoads > 0,
        },
      }));
    };

    void loadOptional(() => getLatestQcDashboardReport(baseUrl, projectId)).then((qcReport) =>
      update({ qcReport }),
    );
    void loadOptional(() => getProjectNiftiQcSnapshot(baseUrl, projectId)).then((niftiSnapshot) =>
      update({ niftiSnapshot }),
    );
    void loadOptional(() => getProjectBoldReferenceReadiness(baseUrl, projectId)).then(
      (boldReadiness) => update({ boldReadiness }),
    );
    void loadOptional(() => getProjectMotionQcReadiness(baseUrl, projectId)).then(
      (motionReadiness) => update({ motionReadiness }),
    );
    void loadOptional(() => getLatestNativeFullPreprocessingRun(baseUrl, projectId)).then(
      (nativeRun) => update({ nativeRun }),
    );

    return () => {
      cancelled = true;
    };
  }, [baseUrl, projectId]);

  return evidence;
}

async function loadOptional<T>(loader: () => Promise<T>): Promise<T | null> {
  try {
    return await loader();
  } catch {
    return null;
  }
}
