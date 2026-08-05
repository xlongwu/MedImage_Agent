from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PipelineValidationError(Exception):
    pass


@dataclass
class PipelineNode:
    id: str
    name: str
    agent: str
    backend: str
    contract_version: str | None = None
    depends_on: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    parallel_level: str = "project"
    gpu_supported: bool = False
    cache: bool = False


@dataclass
class PipelineSpec:
    pipeline_id: str
    version: str
    modality: str
    description: str
    execution: dict[str, Any]
    nodes: list[PipelineNode]


def validate_pipeline_dict(data: dict[str, Any]) -> PipelineSpec:
    if not isinstance(data, dict):
        raise PipelineValidationError("Pipeline data must be a dictionary")

    required_fields = ["pipeline_id", "version", "nodes"]
    for field_name in required_fields:
        if field_name not in data:
            raise PipelineValidationError(f"Missing required field: {field_name}")

    nodes_data = data.get("nodes", [])
    if not nodes_data:
        raise PipelineValidationError("Pipeline must have at least one node")

    node_ids = set()
    for i, node_data in enumerate(nodes_data):
        if not isinstance(node_data, dict):
            raise PipelineValidationError(f"Node {i} must be a dictionary")

        node_required = ["id", "backend"]
        for req in node_required:
            if req not in node_data:
                raise PipelineValidationError(f"Node {i} missing required field: {req}")

        node_id = node_data["id"]
        if node_id in node_ids:
            raise PipelineValidationError(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)

    for _i, node_data in enumerate(nodes_data):
        for dep in node_data.get("depends_on", []):
            if dep not in node_ids:
                raise PipelineValidationError(
                    f"Node '{node_data['id']}' depends on unknown node: {dep}"
                )

    nodes = []
    for node_data in nodes_data:
        node = PipelineNode(
            id=node_data["id"],
            contract_version=node_data.get("contract_version"),
            name=node_data.get("name", node_data["id"]),
            agent=node_data.get("agent", "system"),
            backend=node_data["backend"],
            depends_on=node_data.get("depends_on", []),
            inputs=node_data.get("inputs", []),
            outputs=node_data.get("outputs", []),
            params=node_data.get("params", {}),
            parallel_level=node_data.get("parallel_level", "project"),
            gpu_supported=node_data.get("gpu_supported", False),
            cache=node_data.get("cache", False),
        )
        nodes.append(node)

    return PipelineSpec(
        pipeline_id=data["pipeline_id"],
        version=data["version"],
        modality=data.get("modality", "unknown"),
        description=data.get("description", ""),
        execution=data.get("execution", {}),
        nodes=nodes,
    )


def load_pipeline_yaml(path: str | Path) -> PipelineSpec:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            "Missing dependency: PyYAML. Install with: pip install pyyaml"
        ) from exc

    path = Path(path)
    if not path.exists():
        raise PipelineValidationError(f"Pipeline file not found: {path}")

    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    return validate_pipeline_dict(data)
