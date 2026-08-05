from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.app.runtime.tool_execution_context import ToolExecutionContext


@dataclass
class NodeExecutionContext:
    run_id: str
    project_config: dict[str, Any]
    work_dir: str
    log_dir: str
    matlab_command: str
    spm_dir: str
    dpabi_dir: str
    derivatives_dir: str = "./derivatives"
    tool_execution_context: ToolExecutionContext | None = None


NodeRunner = Callable[..., dict[str, Any]]


def merge_registries(*registries: Mapping[str, NodeRunner]) -> dict[str, NodeRunner]:
    merged: dict[str, NodeRunner] = {}
    for registry in registries:
        for node_id, runner in registry.items():
            if node_id in merged:
                raise ValueError(f"Duplicate node id registered: {node_id}")
            merged[node_id] = runner
    return merged
