import React, { useReducer } from "react";
import type { WorkflowState } from "../../state/workflowTypes";
import { defaultWorkflowConfig, STEP_LABELS } from "../../state/defaultWorkflowConfig";
import { workflowReducer } from "./workflowReducer";
import { WorkflowStepper } from "./WorkflowStepper";
import { IntroCard } from "./IntroCard";
import { DataUploadStep } from "./DataUploadStep";
import { PreprocessingConfigStep } from "./PreprocessingConfigStep";
import { AnalysisConfigStep } from "./AnalysisConfigStep";
import { RunConfirmStep } from "./RunConfirmStep";
import { ResultsOverviewStep } from "./ResultsOverviewStep";

export default function WorkflowShell() {
  const [state, dispatch] = useReducer(workflowReducer, defaultWorkflowConfig);

  const renderStep = () => {
    switch (state.step) {
      case 0: return <IntroCard onStart={() => dispatch({ type: "SET_STEP", step: 1 })} />;
      case 1: return <DataUploadStep state={state} dispatch={dispatch} />;
      case 2: return <PreprocessingConfigStep state={state} dispatch={dispatch} />;
      case 3: return <AnalysisConfigStep state={state} dispatch={dispatch} />;
      case 4: return <RunConfirmStep state={state} dispatch={dispatch} />;
      case 5: return <ResultsOverviewStep state={state} dispatch={dispatch} />;
      default: return <IntroCard onStart={() => dispatch({ type: "SET_STEP", step: 1 })} />;
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
      <WorkflowStepper currentStep={state.step} labels={STEP_LABELS} onStepClick={(s) => dispatch({ type: "SET_STEP", step: s })} />
      <div style={{ marginTop: 24 }}>{renderStep()}</div>
    </div>
  );
}
