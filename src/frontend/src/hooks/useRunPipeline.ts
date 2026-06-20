import { useState } from "react";
import { runPipeline } from "../lib/api";
import type { PipelineRunRequest, PipelineRunResponse } from "../lib/types/pipeline";

export function useRunPipeline() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function start(payload: PipelineRunRequest): Promise<PipelineRunResponse | null> {
    setLoading(true);
    setError("");
    try {
      return await runPipeline(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { start, loading, error };
}
