import { useState } from "react";
import { detectGpu, runGpuBenchmark } from "../api";

interface GpuBenchmarkPanelProps {
  baseUrl: string;
}

export default function GpuBenchmarkPanel({ baseUrl }: GpuBenchmarkPanelProps) {
  const [gpuInfo, setGpuInfo] = useState<Record<string, unknown> | null>(null);
  const [benchmarkResult, setBenchmarkResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDetectGpu = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await detectGpu(baseUrl);
      setGpuInfo(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRunBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await runGpuBenchmark(baseUrl, {
        subject_id: "sub-001",
        input_nii: "./derivatives/spm_smooth/sub-001/func/sub-001_task-rest_bold_smooth.nii",
        derivatives_dir: "./derivatives",
        tr: 2.0,
        freq_band: [0.01, 0.08],
        prefer_gpu: true,
        require_gpu: false,
        benchmark_compare_cpu_gpu: true
      });
      setBenchmarkResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "16px" }}>
      <h2>GPU Benchmark Panel</h2>
      
      <div style={{ marginBottom: "16px" }}>
        <button onClick={handleDetectGpu} disabled={loading} style={{ marginRight: "8px" }}>
          Detect GPU
        </button>
        <button onClick={handleRunBenchmark} disabled={loading}>
          Run ALFF Benchmark
        </button>
      </div>

      {loading && <div>Loading...</div>}
      {error && <div style={{ color: "red" }}>Error: {error}</div>}

      {gpuInfo && (
        <div style={{ marginTop: "16px" }}>
          <h3>GPU Detection Result</h3>
          <pre style={{ background: "#f5f5f5", padding: "12px", borderRadius: "4px", overflow: "auto" }}>
            {JSON.stringify(gpuInfo, null, 2)}
          </pre>
        </div>
      )}

      {benchmarkResult && (
        <div style={{ marginTop: "16px" }}>
          <h3>Benchmark Result</h3>
          <pre style={{ background: "#f5f5f5", padding: "12px", borderRadius: "4px", overflow: "auto" }}>
            {JSON.stringify(benchmarkResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
