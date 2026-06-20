import { MetricCard } from "./MetricCard";
import type { ModelStatus } from "../../lib/types/model";

export interface ModelCardProps {
  model: ModelStatus;
  loading: boolean;
  error: string;
}

export function ModelCard({ model, loading, error }: ModelCardProps) {
  return (
    <MetricCard
      title={`Model Status ${loading ? "..." : error ? "(fallback)" : ""}`}
      values={[[`${model.model_name} ${model.version}`, "Active model"]]}
      tone="model"
      note={model.status}
    />
  );
}
