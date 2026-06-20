import { useEffect, useState } from "react";
import { getPipeline, listPipelines } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
  selectedPipeline: string;
  onSelectPipeline: (value: string) => void;
};

export function PipelineExplorer({ baseUrl, selectedPipeline, onSelectPipeline }: Props) {
  const [pipelines, setPipelines] = useState<string[]>([]);
  const [pipelineDetail, setPipelineDetail] = useState<unknown>(null);
  const [status, setStatus] = useState<string>("IDLE");
  const [error, setError] = useState<string>("");

  async function refreshPipelines() {
    setStatus("LOADING");
    setError("");
    try {
      const result = await listPipelines(baseUrl);
      setPipelines(result.pipelines || []);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function loadPipeline(path: string) {
    const name = path.split("/").pop() || path;
    onSelectPipeline(path);
    setPipelineDetail(null);
    setError("");

    try {
      const result = await getPipeline(baseUrl, name);
      setPipelineDetail(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refreshPipelines();
  }, [baseUrl]);

  return (
    <div>
      <div className="row">
        <button onClick={refreshPipelines}>刷新 Pipeline</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="pipelineList">
        {pipelines.map((pipeline) => (
          <button
            key={pipeline}
            className={pipeline === selectedPipeline ? "listItem selected" : "listItem"}
            onClick={() => loadPipeline(pipeline)}
          >
            {pipeline}
          </button>
        ))}
      </div>

      <JsonBlock value={pipelineDetail} emptyText="请选择一个 pipeline" />
    </div>
  );
}
