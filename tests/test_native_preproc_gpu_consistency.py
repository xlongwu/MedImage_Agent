"""Real-device CPU/CuPy comparisons for released native Tier 1 stages."""
from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pytest

from src.backend.app.native_preproc.stages.alff_falff import compute_alff_falff_maps
from src.backend.app.native_preproc.stages.functional_connectivity import compute_roi_functional_connectivity
from src.backend.app.native_preproc.stages.nuisance_regression import regress_confounds_with_backend
from src.backend.app.native_preproc.stages.temporal_filtering import temporal_filter_4d
from src.backend.app.native_preproc.stages.smoothing import smooth_spatial_with_backend
from src.backend.app.native_preproc.stages.atlas_resampling import resample_atlas_with_backend
from src.backend.app.native_preproc.stages.alff_falff import run_alff
from src.backend.app.native_preproc.stages.functional_connectivity import run_functional_connectivity
from src.backend.app.native_preproc.stages.nuisance_regression import run_nuisance_regression
from src.backend.app.native_preproc.stages.temporal_filtering import run_temporal_filtering
from src.backend.app.native_preproc.io.nifti_io import load_nifti, save_nifti
from src.backend.app.tools.reho_compute import compute_reho_cupy, compute_reho_numpy
from src.backend.app.services.native_preproc_full import run_native_full_execute
from tests.integration.native_preproc_fixtures import make_synthetic_native_inputs, native_full_request
from src.backend.app.schemas.native_preproc_api import NativeComputePolicy


def _require_cupy_device() -> None:
    try:
        cp = importlib.import_module("cupy")
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip("CuPy is installed but no CUDA device is available")
        cp.asarray([1.0], dtype=cp.float32).sum().item()
    except ImportError:
        pytest.skip("CuPy is not installed")
    except Exception as exc:
        pytest.skip(f"CuPy CUDA runtime is unavailable: {exc}")


GPU_POLICY = NativeComputePolicy(backend="gpu", precision="float32", chunk_size=7)


@pytest.mark.gpu
def test_native_alff_falff_cpu_cupy_consistency() -> None:
    _require_cupy_device()
    rng = np.random.default_rng(1)
    bold = rng.normal(size=(4, 3, 2, 24)).astype(np.float32)
    mask = np.ones(bold.shape[:3], dtype=np.uint8)
    cpu = compute_alff_falff_maps(bold, tr=2.0, mask_3d=mask)
    gpu = compute_alff_falff_maps(bold, tr=2.0, mask_3d=mask, compute_policy=GPU_POLICY)
    assert gpu[2]["compute"]["actual_backend"] == "gpu-cupy"
    assert np.allclose(cpu[0], gpu[0], rtol=1e-4, atol=7e-4)
    assert np.allclose(cpu[1], gpu[1], rtol=1e-5, atol=1e-6)


@pytest.mark.gpu
def test_native_temporal_filter_cpu_cupy_consistency() -> None:
    _require_cupy_device()
    rng = np.random.default_rng(2)
    bold = rng.normal(size=(3, 3, 2, 24)).astype(np.float32)
    cpu, _ = temporal_filter_4d(bold, tr=2.0, low_hz=0.01, high_hz=0.08)
    gpu, qc = temporal_filter_4d(bold, tr=2.0, low_hz=0.01, high_hz=0.08, compute_policy=GPU_POLICY)
    assert qc["compute"]["actual_backend"] == "gpu-cupy"
    runtime = qc["compute"]["runtime"]
    assert runtime["transfer_seconds"] >= 0.0
    assert runtime["compute_seconds"] >= 0.0
    assert runtime["total_seconds"] >= runtime["transfer_seconds"] + runtime["compute_seconds"]
    assert np.allclose(cpu, gpu, rtol=1e-4, atol=1e-4)


@pytest.mark.gpu
def test_native_nuisance_regression_cpu_cupy_consistency() -> None:
    _require_cupy_device()
    rng = np.random.default_rng(3)
    bold = rng.normal(size=(3, 2, 2, 24)).astype(np.float32)
    design = np.column_stack([np.ones(24), np.linspace(-1.0, 1.0, 24), rng.normal(size=24)]).astype(np.float32)
    cpu, _ = regress_confounds_with_backend(bold, design)
    gpu, provenance = regress_confounds_with_backend(bold, design, compute_policy=GPU_POLICY)
    assert provenance["actual_backend"] == "gpu-cupy"
    assert np.allclose(cpu, gpu, rtol=1e-4, atol=1e-4)


@pytest.mark.gpu
def test_native_functional_connectivity_cpu_cupy_consistency_with_constant_roi() -> None:
    _require_cupy_device()
    rng = np.random.default_rng(4)
    roi = np.column_stack([rng.normal(size=24), rng.normal(size=24), np.ones(24)]).astype(np.float32)
    cpu = compute_roi_functional_connectivity(roi, roi_names=["a", "b", "constant"])
    gpu = compute_roi_functional_connectivity(roi, roi_names=["a", "b", "constant"], compute_policy=GPU_POLICY)
    assert gpu[2]["compute"]["actual_backend"] == "gpu-cupy"
    assert cpu[3] == gpu[3]
    assert np.allclose(cpu[0], gpu[0], rtol=1e-4, atol=1e-4)
    assert np.allclose(cpu[1], gpu[1], rtol=1e-4, atol=1e-4)


@pytest.mark.gpu
def test_native_gpu_stage_artifacts_are_reloadable_and_provenance_is_truthful(tmp_path) -> None:
    _require_cupy_device()
    rng = np.random.default_rng(5)
    bold = rng.normal(size=(3, 3, 3, 24)).astype(np.float32)
    input_bold = tmp_path / "sub-001_bold.nii.gz"
    save_nifti(input_bold, bold, np.eye(4))

    filtered = run_temporal_filtering(input_bold, tmp_path / "filtered", tr=2.0, compute_policy=GPU_POLICY)
    alff = run_alff(input_bold, tmp_path / "alff", tr=2.0, compute_policy=GPU_POLICY)
    motion = tmp_path / "motion.tsv"
    np.savetxt(motion, rng.normal(size=(24, 6)), delimiter="\t")
    regression = run_nuisance_regression(
        input_bold,
        tmp_path / "regression",
        motion_parameters=motion,
        polynomial_order=1,
        compute_policy=GPU_POLICY,
    )
    roi = tmp_path / "roi.tsv"
    np.savetxt(roi, rng.normal(size=(24, 3)), delimiter="\t")
    fc = run_functional_connectivity(roi, tmp_path / "fc", compute_policy=GPU_POLICY)

    for result in (filtered, alff, regression, fc):
        assert result.status in {"succeeded", "warning"}, result.errors
        assert result.backend == "gpu"
        assert result.provenance.backend == "gpu"
        assert result.parameters["compute"]["actual_backend"] == "gpu-cupy"
        for artifact in result.output_artifacts:
            assert artifact.path
    filtered_artifact = next(item for item in filtered.output_artifacts if item.artifact_type == "filtered_bold")
    assert load_nifti(filtered_artifact.path).data.shape == bold.shape


@pytest.mark.gpu
@pytest.mark.parametrize("neighborhood", [7, 19, 27])
def test_experimental_reho_gpu_exactly_matches_tie_corrected_cpu_reference(neighborhood: int) -> None:
    _require_cupy_device()
    rng = np.random.default_rng(6 + neighborhood)
    # Quantisation deliberately creates ties; a double-argsort implementation
    # would fail this comparison even when random continuous data appears safe.
    bold = rng.integers(-2, 3, size=(5, 5, 5, 12), endpoint=False).astype(np.float32)
    bold[2, 2, 2, :] = 1.0  # constant neighbourhood member
    mask = np.ones(bold.shape[:3], dtype=bool)
    mask[1, 1, 1] = False
    cpu = compute_reho_numpy(bold, neighborhood=neighborhood, gm_mask=mask)
    gpu = compute_reho_cupy(bold, neighborhood=neighborhood, gm_mask=mask, z_chunk_size=2)
    assert cpu["ok"] == gpu["ok"]
    assert np.array_equal(np.asarray(cpu["reho"]) != 0, np.asarray(gpu["reho"]) != 0)
    assert np.allclose(cpu["reho"], gpu["reho"], rtol=1e-5, atol=1e-5)


@pytest.mark.gpu
def test_full_native_workflow_uses_gpu_stages_without_a_bypass(tmp_path) -> None:
    _require_cupy_device()
    inputs = make_synthetic_native_inputs(tmp_path)
    request = native_full_request(inputs, run_id="gpu-native-full-e2e").model_copy(
        update={"compute_policy": NativeComputePolicy(backend="gpu")}
    )
    result = run_native_full_execute("gpu-native-e2e", request, project_dir=str(tmp_path))
    assert result.ok is True
    assert result.status == "succeeded"
    for stage_id in {"alff", "falff", "temporal_filtering", "nuisance_regression", "functional_connectivity", "smoothing", "atlas_resampling"}:
        stage = next(item for item in result.stage_results if item.stage_id == stage_id)
        assert stage.status in {"succeeded", "warning"}
        assert stage.backend == "gpu"
        assert stage.output_artifacts
    assert result.safety_flags["rawdata_readonly_confirmed"] is True
    assert result.safety_flags["no_external_tools_executed"] is True
    performance_model = Path(result.run_dir).parent / "gpu_performance_profiles.json"
    assert performance_model.exists()


@pytest.mark.gpu
def test_spatial_smoothing_and_label_resampling_match_cpu_contracts() -> None:
    _require_cupy_device()
    rng = np.random.default_rng(33)
    image = rng.normal(size=(6, 5, 4, 3)).astype(np.float32)
    sigma = (1.1, 0.8, 0.6)
    cpu_smoothed, _ = smooth_spatial_with_backend(image, sigma, compute_policy=NativeComputePolicy(backend="cpu"))
    gpu_smoothed, gpu_smoothing = smooth_spatial_with_backend(image, sigma, compute_policy=GPU_POLICY)
    assert gpu_smoothing["actual_backend"] == "gpu-cupy"
    assert np.allclose(cpu_smoothed, gpu_smoothed, rtol=1e-4, atol=1e-4)

    atlas = np.zeros((5, 5, 5), dtype=np.int16)
    atlas[:2] = 1
    atlas[2:] = 3
    affine = np.eye(4)
    cpu_atlas, _ = resample_atlas_with_backend(
        atlas, affine, (6, 5, 5), affine, compute_policy=NativeComputePolicy(backend="cpu")
    )
    gpu_atlas, gpu_resampling = resample_atlas_with_backend(
        atlas, affine, (6, 5, 5), affine, compute_policy=GPU_POLICY
    )
    assert gpu_resampling["actual_backend"] == "gpu-cupy"
    assert np.array_equal(np.rint(cpu_atlas).astype(np.int16), np.rint(gpu_atlas).astype(np.int16))
    assert set(np.unique(np.rint(gpu_atlas).astype(np.int16))) <= {0, 1, 3}
