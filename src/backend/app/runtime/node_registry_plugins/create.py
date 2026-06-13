from __future__ import annotations

from src.backend.app.runtime.node_registry_plugins.base import NodeRunner, merge_registries
from src.backend.app.runtime.node_registry_plugins.core_nodes import REGISTRY as CORE_REGISTRY
from src.backend.app.runtime.node_registry_plugins.dpabi_nodes import REGISTRY as DPABI_REGISTRY
from src.backend.app.runtime.node_registry_plugins.gpu_nodes import REGISTRY as GPU_REGISTRY
from src.backend.app.runtime.node_registry_plugins.spm_nodes import REGISTRY as SPM_REGISTRY
from src.backend.app.runtime.node_registry_plugins.qc_nodes import REGISTRY as QC_REGISTRY
from src.backend.app.runtime.node_registry_plugins.rsfmri_nodes import REGISTRY as RSFMRI_REGISTRY
from src.backend.app.runtime.node_registry_plugins.report_nodes import REGISTRY as REPORT_REGISTRY


def create_registry() -> dict[str, NodeRunner]:
    return merge_registries(
        CORE_REGISTRY,
        DPABI_REGISTRY,
        GPU_REGISTRY,
        SPM_REGISTRY,
        QC_REGISTRY,
        RSFMRI_REGISTRY,
        REPORT_REGISTRY,
    )
