# Phase E：GPU Backend 原型

> 目标版本：v0.3.0 | 预计工期：2–3 周 | 前置条件：Phase A 封版完成，有 CUDA GPU 环境（非强制）

---

## 1. 目标与范围

为 ALFF/fALFF、FC matrix、ReHo 三个计算密集型节点提供可选的 GPU backend（CuPy），保证 CPU 为默认后端，GPU 需显式启用，且 GPU 结果必须与 CPU reference 在误差阈值内一致。

**不做**：SPM/DPABI 的 GPU 加速、多 GPU 并行、自动 backend 选择。

---

## 2. 核心原则

```
默认 backend: cpu_numpy
GPU 可选 backend: gpu_cupy, gpu_torch
启用条件: backend=gpu_cupy + approved_gpu=true
GPU 不可用时自动 fallback 到 CPU
GPU 结果 vs CPU 结果误差必须在阈值内
```

---

## 3. 新增/修改文件清单

```text
backend/app/tools/gpu_capability.py        # 新增：GPU 环境检测
backend/app/tools/alff_compute.py           # 修改：新增 CuPy 路径
backend/app/tools/reho.py                   # 修改：新增 CuPy 路径
backend/app/tools/functional_connectivity.py # 修改：新增 CuPy 路径
backend/app/tools/gpu_benchmark_cli.py      # 修改：增强 benchmark
backend/app/api/routes.py                   # 修改：新增 GPU 端点
examples/pipeline_gpu_alff.yaml             # 新增：pipeline YAML
tests/unit/test_gpu_utils.py                # 修改：增加 GPU 测试
```

---

## 4. 逐步实施步骤

### Step 1：GPU Capability Check

文件：`backend/app/tools/gpu_capability.py`

检查内容：
```text
1. CUDA 是否可用          → import cupy; cupy.cuda.is_available()
2. CuPy 版本             → cupy.__version__
3. GPU 名称              → cupy.cuda.Device().name
4. GPU 显存 (MB)         → cupy.cuda.Device().mem_info
5. Torch CUDA 是否可用   → torch.cuda.is_available() (optional)
6. Driver 版本           → cupy.cuda.runtime.driverGetVersion()
```

输出：
```text
work/gpu/gpu_capability.json
```

无 GPU 时返回：
```json
{
  "ok": true,
  "gpu_available": false,
  "message": "No CUDA-capable GPU detected. CPU backend will be used."
}
```

### Step 2：ALFF/fALFF GPU Backend

在 `alff_compute.py` 中新增 CuPy 路径：

```python
def compute_alff_gpu(data: np.ndarray, tr: float, freq_band: tuple[float, float]) -> dict:
    try:
        import cupy as cp
    except ImportError:
        return {"ok": False, "errors": ["CuPy not installed"], "backend": "cpu-numpy"}

    arr = cp.asarray(data, dtype=cp.float32)
    nt = arr.shape[3]
    freqs = cp.fft.rfftfreq(nt, d=tr)
    spec = cp.fft.rfft(arr, axis=3)
    lo, hi = freq_band
    band_mask = (freqs >= lo) & (freqs <= hi) & (freqs > 0)
    alff = cp.mean(cp.abs(spec[:, :, :, band_mask]), axis=3)
    # ... ALFF/fALFF computation on GPU ...
    return {
        "ok": True,
        "backend": "gpu-cupy",
        "alff": cp.asnumpy(alff),
        "falff": cp.asnumpy(falff),
    }
```

关键：GPU 结果需要与 CPU 结果做数值对比验证：

```python
def validate_gpu_vs_cpu(gpu_result, cpu_result, tolerance=1e-5):
    diff = np.max(np.abs(gpu_result - cpu_result))
    ok = diff < tolerance
    return {"ok": ok, "max_abs_diff": float(diff), "tolerance": tolerance}
```

### Step 3：FC Matrix GPU Backend

在 `functional_connectivity.py` 中新增 CuPy 路径：
- ROI timeseries extraction 仍用 CPU（I/O bound）
- Correlation matrix 计算用 GPU matmul 加速

### Step 4：ReHo GPU Backend

在 `reho.py` 中新增 CuPy 路径：
- ReHo 涉及局部 sliding window，GPU 实现复杂度较高
- Phase E 可先做方案设计 + 基准测试，实现可延后到 v0.3.1

### Step 5：Benchmark CLI

增强 `gpu_benchmark_cli.py`：

```bash
python -m backend.app.tools.gpu_benchmark_cli --node alff --input-size 64,64,32,200 --repeat 3
```

输出：CPU time / GPU time / speedup / max_abs_diff

---

## 5. API 端点

```text
GET  /api/gpu/capability              → GPU 环境检测
POST /api/gpu/benchmark               → 运行 CPU vs GPU benchmark
GET  /api/gpu/benchmark/latest        → 查看最新 benchmark 结果
```

---

## 6. 验收标准

- [ ] 无 GPU 环境时 `gpu_capability` 返回 `gpu_available: false`
- [ ] 无 GPU 环境时所有测试仍然通过（CPU fallback）
- [ ] 无 GPU 环境时 `prefer_gpu=False` 不报错
- [ ] GPU ALFF/fALFF 输出 shape 与 CPU 一致
- [ ] GPU FC 输出 shape 与 CPU 一致
- [ ] CPU vs GPU 数值误差 `max_abs_diff < 1e-5`
- [ ] GPU backend 不设为默认（需要 `approved_gpu=true` 显式启用）
- [ ] GPU capability check 记录 GPU name / memory / driver
- [ ] benchmark 输出 CPU time / GPU time / speedup
- [ ] 所有新代码不影响现有 CPU-only 测试
