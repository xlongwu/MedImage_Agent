from __future__ import annotations

from src.backend.app.runtime.node_registry_plugins.base import NodeRunner, merge_registries
from src.backend.app.runtime.node_registry_plugins.core_nodes import REGISTRY as CORE_REGISTRY
from src.backend.app.runtime.node_registry_plugins.dpabi_nodes import REGISTRY as DPABI_REGISTRY
from src.backend.app.runtime.node_registry_plugins.gpu_nodes import REGISTRY as GPU_REGISTRY
from src.backend.app.runtime.node_registry_plugins.native_preproc_nodes import REGISTRY as NATIVE_PREPROC_REGISTRY
from src.backend.app.runtime.node_registry_plugins.qc_nodes import REGISTRY as QC_REGISTRY
from src.backend.app.runtime.node_registry_plugins.rsfmri_nodes import REGISTRY as RSFMRI_REGISTRY
from src.backend.app.runtime.node_registry_plugins.report_nodes import REGISTRY as REPORT_REGISTRY


_EXTERNAL_LEGACY_NODE_IDS = frozenset({
    "dpabi_sandbox_smoke_run",
    "dpabi_signature_probe",
    "dpabi_single_function_sandbox",
    "dpabi_subject_smooth",
    "dpabi_template_execute",
    "spm_smoke_test",
    "spm_realign_subject",
    "spm_slice_timing_subject",
    "spm_coregister_subject",
    "spm_segment_subject",
    "spm_normalize_subject",
    "spm_smooth_subject",
})


def _external_legacy_node_blocker(context, node):
    """Fail closed for legacy MATLAB/SPM/DPABI process-launch node IDs."""

    return {
        "ok": False,
        "status": "blocked",
        "node_id": node.id,
        "backend": "native_python",
        "errors": [
            "Legacy external execution is retired. Use the reviewed native_preproc_full_execute workflow."
        ],
        "warnings": [],
        "safety_flags": {
            "no_external_tools_executed": True,
            "no_matlab_spm_dpabi": True,
            "project_internal_execution_only": True,
        },
    }


def create_registry() -> dict[str, NodeRunner]:
    internal_dpabi = {
        node_id: runner
        for node_id, runner in DPABI_REGISTRY.items()
        if node_id not in _EXTERNAL_LEGACY_NODE_IDS
    }
    legacy_blockers = {
        node_id: _external_legacy_node_blocker
        for node_id in _EXTERNAL_LEGACY_NODE_IDS
    }
    return merge_registries(
        CORE_REGISTRY,
        internal_dpabi,
        GPU_REGISTRY,
        NATIVE_PREPROC_REGISTRY,
        QC_REGISTRY,
        RSFMRI_REGISTRY,
        REPORT_REGISTRY,
        legacy_blockers,
    )
