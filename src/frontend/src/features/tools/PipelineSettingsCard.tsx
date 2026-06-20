import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ProjectDetail } from "../../lib/types/project";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { ModelStatus } from "../../lib/types/model";

export interface PipelineSettingsCardProps {
  project: ProjectDetail;
  model: ModelStatus;
  dataset: DatasetSummary;
  executionMode: ExecutionMode;
  externalSmokeApprovedRun: boolean;
  externalSmokeApprovedBy: string;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  onExternalSmokeApprovedRunChange: (value: boolean) => void;
  onExternalSmokeApprovedByChange: (value: string) => void;
  onConfigure: () => void;
}

export function PipelineSettingsCard({
  project,
  model,
  dataset,
  executionMode,
  externalSmokeApprovedRun,
  externalSmokeApprovedBy,
  onExecutionModeChange,
  onExternalSmokeApprovedRunChange,
  onExternalSmokeApprovedByChange,
  onConfigure,
}: PipelineSettingsCardProps) {
  const executionModes: Array<{ value: ExecutionMode; label: string }> = [
    { value: "simulated", label: "Simulated" },
    { value: "external_smoke", label: "External Smoke" },
    { value: "rsfmri_python", label: "rs-fMRI Python" },
  ];
  return (
    <section className="settings-card">
      <div className="card-row">
        <div className="card-title">Pipeline Settings</div>
        <button onClick={onConfigure}>Configure</button>
      </div>
      {[
        ["Pipeline", project.current_pipeline_id],
        ["Model", `${model.model_name} ${model.version}`],
        ["Input", project.sequences.join(", ")],
        ["Output", "Segmentation + metrics"],
        ["Dataset", dataset.health_status],
      ].map(([key, value]) => (
        <div className="setting-line" key={key}>
          <span>{key}</span>
          <strong>{value}</strong>
        </div>
      ))}
      <div className="execution-mode-group" aria-label="Execution mode">
        {executionModes.map((item) => (
          <button
            key={item.value}
            className={executionMode === item.value ? "selected" : ""}
            onClick={() => onExecutionModeChange(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <p className="mode-note">
        {executionMode === "external_smoke"
          ? externalSmokeApprovedRun
            ? "Approved smoke will launch MATLAB/SPM/DPABI after run-level approval is recorded."
            : "Generates an auditable SPM/DPABI smoke package without launching MATLAB."
          : executionMode === "rsfmri_python"
            ? "Runs the synthetic Python rs-fMRI quickstart adapter."
            : "Runs the fast in-memory demo task stream."}
      </p>
      {executionMode === "external_smoke" ? (
        <div className="external-approval-box">
          <label className="check-line">
            <input
              type="checkbox"
              checked={externalSmokeApprovedRun}
              onChange={(event) => onExternalSmokeApprovedRunChange(event.target.checked)}
            />
            Run approved MATLAB smoke
          </label>
          <input
            value={externalSmokeApprovedBy}
            onChange={(event) => onExternalSmokeApprovedByChange(event.target.value)}
            placeholder="Approved by"
            disabled={!externalSmokeApprovedRun}
            aria-label="Approved by"
          />
        </div>
      ) : null}
    </section>
  );
}
