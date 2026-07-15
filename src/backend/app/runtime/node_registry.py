from __future__ import annotations

from src.backend.app.runtime.node_registry_plugins.base import NodeExecutionContext, NodeRunner
from src.backend.app.runtime.node_registry_plugins.create import create_registry

NODE_REGISTRY: dict[str, NodeRunner] = create_registry()


def get_node_runner(node_id: str) -> NodeRunner:
    try:
        return NODE_REGISTRY[node_id]
    except KeyError as exc:
        raise KeyError(f"No node runner registered for node id: {node_id}") from exc
