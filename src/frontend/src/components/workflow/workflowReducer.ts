import type { WorkflowState, WorkflowAction } from "../../state/workflowTypes";

export function workflowReducer(state: WorkflowState, action: WorkflowAction): WorkflowState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step };
    case "SET_DATA_SOURCE":
      return { ...state, dataSource: action.sourceType, datasetPath: action.path };
    case "SET_PREPROCESSING":
      return { ...state, preprocessing: { ...state.preprocessing, ...action.config } };
    case "SET_ANALYSIS":
      return { ...state, analysis: { ...state.analysis, ...action.config } };
    case "SET_RUN_STATUS":
      return { ...state, runId: action.runId, runStatus: action.status };
    case "RESET":
      return { ...state, step: 0, runId: null, runStatus: "IDLE" };
    default:
      return state;
  }
}
