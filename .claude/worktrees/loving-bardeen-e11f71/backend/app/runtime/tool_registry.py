from __future__ import annotations

from dataclasses import dataclass, field


class ToolExecutionError(Exception):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    read_only: bool
    writes_files: bool
    destructive: bool
    requires_confirmation: bool
    parallel_safe: bool
    allowed_read_paths: list[str] = field(default_factory=list)
    allowed_write_paths: list[str] = field(default_factory=list)


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "pipeline.plan": ToolSpec(
        name="pipeline.plan",
        description="Read project config and pipeline YAML and generate an execution plan.",
        read_only=False,
        writes_files=True,
        destructive=False,
        requires_confirmation=False,
        parallel_safe=True,
        allowed_read_paths=["examples/", "specs/", "work/"],
        allowed_write_paths=["work/agent_runs/"],
    ),
    "pipeline.execute": ToolSpec(
        name="pipeline.execute",
        description="Execute an approved pipeline plan.",
        read_only=False,
        writes_files=True,
        destructive=False,
        requires_confirmation=True,
        parallel_safe=False,
        allowed_read_paths=["examples/", "work/", "matlab/", "third_party/"],
        allowed_write_paths=["work/", "logs/", "reports/", "derivatives/"],
    ),
}


def get_tool_spec(name: str) -> ToolSpec:
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ToolExecutionError(f"Unknown tool: {name}") from exc


def list_tool_specs() -> list[ToolSpec]:
    return list(TOOL_REGISTRY.values())


def assert_tool_allowed(name: str, approved: bool = False) -> ToolSpec:
    spec = get_tool_spec(name)
    if spec.requires_confirmation and not approved:
        raise ToolExecutionError(
            f"Tool requires explicit approval before execution: {name}"
        )
    return spec
