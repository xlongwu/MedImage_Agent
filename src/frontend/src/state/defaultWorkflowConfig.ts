import type { WorkflowState } from "./workflowTypes";

export const defaultWorkflowConfig: WorkflowState = {
  step: 0,
  dataSource: "none",
  datasetPath: "",
  preprocessing: {
    sliceTiming: { enabled: true, tr: null, referenceSlice: "middle" },
    realignment: { enabled: true },
    coregistration: { enabled: true },
    segmentation: { enabled: true },
    normalization: { enabled: true, voxelSize: [3, 3, 3] },
    smoothing: { enabled: true, fwhm: [6, 6, 6] },
    nuisanceRegression: {
      enabled: true,
      model: "friston24",
      includeWM: false,
      includeCSF: false,
      includeLinearTrend: true,
    },
    temporalFiltering: { enabled: true, lowHz: 0.01, highHz: 0.08 },
  },
  analysis: {
    enabled: true,
    alffFalff: { enabled: true, lowHz: 0.01, highHz: 0.08 },
    reho: { enabled: true, neighborhood: 27 },
    functionalConnectivity: { enabled: true, roiCount: 4, generateSeedMap: false },
    groupSummary: { enabled: true },
    reportExport: { enabled: true, validateAfterExport: true },
  },
  runId: null,
  runStatus: "IDLE",
};

export const STEP_LABELS = [
  "Project Intro",
  "Select Data",
  "Preprocessing",
  "Analysis",
  "Confirm & Run",
  "Results",
];
