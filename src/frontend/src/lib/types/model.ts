export interface ModelStatus {
  project_id: string;
  model_name: string;
  version: string;
  status: string;
  dice_score: number;
  last_trained: string;
  metrics: Record<string, number>;
}

