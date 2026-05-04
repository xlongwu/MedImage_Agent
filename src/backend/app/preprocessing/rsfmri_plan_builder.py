from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.preprocessing.rsfmri_step_registry import (
    get_rsfmri_core_step_registry_dict,
)


def build_rsfmri_preprocessing_plan(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    modality: str = "rs-fMRI",
    pipeline_id: str = "rsfmri_core_preprocessing",
) -> dict[str, Any]:
    steps = get_rsfmri_core_step_registry_dict()

    out_dir = Path(work_dir) / "preprocessing" / "rsfmri"
    report_out = Path(report_dir) / "rsfmri"

    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    approval_required_steps = [
        step["step_id"]
        for step in steps
        if step.get("approval_required")
    ]

    matlab_steps = [
        step["step_id"]
        for step in steps
        if step.get("matlab_required")
    ]

    gpu_candidate_steps = [
        step["step_id"]
        for step in steps
        if step.get("gpu_supported")
    ]

    dpabi_steps = [
        step["step_id"]
        for step in steps
        if step.get("backend") == "matlab-dpabi"
    ]

    spm_steps = [
        step["step_id"]
        for step in steps
        if step.get("backend") == "matlab-spm"
    ]

    plan = {
        "ok": True,
        "node_id": "rsfmri_preprocessing_plan",
        "backend": "python",
        "pipeline_id": pipeline_id,
        "modality": modality,
        "version": "0.1.0",
        "description": "Core rs-fMRI preprocessing plan. This is a planning artifact and does not execute preprocessing.",
        "steps_total": len(steps),
        "steps": steps,
        "summary": {
            "approval_required_steps": approval_required_steps,
            "approval_required_count": len(approval_required_steps),
            "matlab_steps": matlab_steps,
            "matlab_steps_count": len(matlab_steps),
            "spm_steps": spm_steps,
            "dpabi_steps": dpabi_steps,
            "gpu_candidate_steps": gpu_candidate_steps,
            "gpu_candidate_count": len(gpu_candidate_steps),
        },
        "safety": {
            "plan_only": True,
            "preprocessing_executed": False,
            "matlab_launched": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dparsfa_run_executed": False,
            "dpabi_gui_called": False,
            "rawdata_modified": False,
            "files_deleted": False,
        },
        "warnings": [],
        "errors": [],
    }

    json_path = out_dir / "rsfmri_preprocessing_plan.json"
    report_path = report_out / "rsfmri_preprocessing_plan_report.md"

    json_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Core Preprocessing Plan")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Pipeline ID: {pipeline_id}")
    lines.append(f"- Modality: {modality}")
    lines.append(f"- Steps total: {len(steps)}")
    lines.append(f"- Approval-required steps: {len(approval_required_steps)}")
    lines.append(f"- MATLAB-required steps: {len(matlab_steps)}")
    lines.append(f"- GPU candidate steps: {len(gpu_candidate_steps)}")
    lines.append("")
    lines.append("## Step DAG")
    lines.append("")
    lines.append("| Step | Backend | Parallel | GPU | Approval | Depends On |")
    lines.append("|---|---|---|---:|---:|---|")

    for step in steps:
        lines.append(
            f"| {step['step_id']} | {step['backend']} | "
            f"{step['parallel_level']} | {step['gpu_supported']} | "
            f"{step['approval_required']} | {', '.join(step['depends_on']) or '-'} |"
        )

    lines.append("")
    lines.append("## DPABI Safety")
    lines.append("")
    lines.append("- DPARSF_run is not used.")
    lines.append("- DPARSFA_run is not used.")
    lines.append("- DPABI GUI is not used.")
    lines.append("- DPABI steps require explicit wrappers and approval.")
    lines.append("")
    lines.append("## Safety State")
    lines.append("")
    for key, value in plan["safety"].items():
        lines.append(f"- {key}: {value}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    plan["outputs"] = [str(json_path), str(report_path)]
    return plan
