from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWLISTED_TEMPLATE_FUNCTIONS = {"y_Smooth", "rest_Smooth"}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return '"' + str(value).replace('"', '\\"') + '"'


def _render_subject_wrapper_template(function_name: str, template_id: str) -> str:
    return f"""pipeline_id: {template_id}
version: "0.1.0"
modality: synthetic-rsfmri
description: "Generated DPABI subject-level single-function wrapper template for {function_name}. Synthetic data only."

template_metadata:
  generated_by: "dpabi_template_library"
  function_name: "{function_name}"
  template_type: "dpabi_subject_single_function_wrapper"
  synthetic_only: true
  requires_approval: true
  approved_by_default: false
  full_dpabi_execution: false
  dparsf_run_allowed: false
  dparsfa_run_allowed: false
  dpabi_gui_allowed: false

execution:
  stop_on_failure: true
  run_id: "run_{template_id}_001"
  scheduler:
    mode: "local_parallel"
    max_workers: 2
    matlab_max_workers: 1

nodes:
  - id: create_synthetic_bids
    name: Create Synthetic BIDS Dataset
    agent: data-inspector
    backend: python
    depends_on: []
    inputs: []
    outputs:
      - "./examples/synthetic_bids/rawdata/dataset_description.json"
      - "./examples/synthetic_bids/rawdata/participants.tsv"
    params:
      output_dir: "./examples/synthetic_bids/rawdata"
      subjects:
        - sub-001
        - sub-002
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: data_inspection
    name: Data Inspection
    agent: data-inspector
    backend: python
    depends_on:
      - create_synthetic_bids
    inputs:
      - "./examples/synthetic_bids/rawdata"
    outputs:
      - "./work/dataset_index/dataset_index.json"
      - "./work/dataset_index/data_completeness_report.json"
      - "./work/dataset_index/subject_table.csv"
    params:
      rawdata_dir: "./examples/synthetic_bids/rawdata"
      output_dir: "./work/dataset_index"
      read_nifti_metadata: true
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: environment_check
    name: Environment Check
    agent: system
    backend: matlab
    depends_on: []
    inputs: []
    outputs:
      - "./work/environment_check.json"
    params: {{}}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_signature_probe
    name: DPABI Signature Probe
    agent: dpabi-runner
    backend: matlab-dpabi
    depends_on:
      - environment_check
    inputs: []
    outputs:
      - "./work/dpabi/dpabi_function_signatures.json"
    params: {{}}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_wrapper_contracts
    name: DPABI Wrapper Contracts
    agent: dpabi-runner
    backend: python
    depends_on:
      - dpabi_signature_probe
    inputs:
      - "./work/dpabi/dpabi_function_signatures.json"
    outputs:
      - "./work/dpabi/dpabi_wrapper_contracts.json"
      - "./work/dpabi/dpabi_wrapper_contracts.yaml"
      - "./reports/dpabi/dpabi_signature_probe_report.md"
    params:
      signatures_path: "./work/dpabi/dpabi_function_signatures.json"
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_subject_smooth
    name: Approved DPABI Subject Smooth
    agent: dpabi-runner
    backend: matlab-dpabi
    depends_on:
      - data_inspection
      - dpabi_wrapper_contracts
    inputs:
      - "./work/dataset_index/dataset_index.json"
      - "./work/dpabi/dpabi_wrapper_contracts.json"
    outputs: []
    params:
      function_name: "{function_name}"
      fwhm: [4, 4, 4]
      approved: false
      synthetic_only: true
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: dpabi_subject_wrapper_report
    name: DPABI Subject Wrapper Report
    agent: dpabi-runner
    backend: python
    depends_on:
      - dpabi_subject_smooth
    inputs: []
    outputs:
      - "./reports/dpabi/dpabi_subject_wrapper_summary.json"
      - "./reports/dpabi/dpabi_subject_wrapper_report.md"
    params: {{}}
    parallel_level: project
    gpu_supported: false
    cache: false
"""


def write_dpabi_template_library(
    work_dir: str,
    report_dir: str,
    matrix_path: str = "./work/dpabi/dpabi_wrapper_compatibility_matrix.json",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    matrix_file = Path(matrix_path)
    matrix = _read_json(matrix_file)

    if not matrix:
        return {
            "ok": False,
            "node_id": "dpabi_template_library",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid compatibility matrix: {matrix_file}"],
        }

    template_root = Path(work_dir) / "dpabi" / "templates"
    pipeline_dir = template_root / "pipelines"
    report_out = Path(report_dir) / "dpabi"

    pipeline_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    generated_templates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in matrix.get("rows", []):
        function_name = row.get("function_name")
        readiness = row.get("readiness")

        if readiness != "PROMOTABLE_TO_TEMPLATE":
            skipped.append({
                "function_name": function_name,
                "reason": f"readiness={readiness}",
            })
            continue

        if function_name not in ALLOWLISTED_TEMPLATE_FUNCTIONS:
            skipped.append({
                "function_name": function_name,
                "reason": "not_allowlisted_for_template_generation",
            })
            continue

        template_id = f"dpabi_{function_name.lower()}_subject_wrapper_template"
        template_path = pipeline_dir / f"{template_id}.yaml"

        template_path.write_text(
            _render_subject_wrapper_template(function_name, template_id),
            encoding="utf-8",
        )

        generated_templates.append({
            "template_id": template_id,
            "function_name": function_name,
            "template_path": str(template_path),
            "template_type": "dpabi_subject_single_function_wrapper",
            "synthetic_only": True,
            "requires_approval": True,
            "approved_by_default": False,
            "readiness_source": readiness,
        })

    index = {
        "ok": True,
        "node_id": "dpabi_template_library",
        "backend": "python",
        "matrix_path": str(matrix_file),
        "templates_total": len(generated_templates),
        "templates": generated_templates,
        "skipped": skipped,
        "safety": {
            "templates_executed": False,
            "full_dpabi_execution": False,
            "dparsf_run_allowed": False,
            "dpabi_gui_allowed": False,
            "rawdata_modified": False,
            "files_deleted": False,
        },
        "warnings": warnings,
        "errors": errors,
    }

    index_path = template_root / "dpabi_template_index.json"
    manifest_path = template_root / "dpabi_template_manifest.yaml"
    report_path = report_out / "dpabi_template_library_report.md"

    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest_lines = []
    manifest_lines.append('version: "0.1.0"')
    manifest_lines.append("templates:")
    for item in generated_templates:
        manifest_lines.append(f"  - template_id: {_yaml_scalar(item['template_id'])}")
        manifest_lines.append(f"    function_name: {_yaml_scalar(item['function_name'])}")
        manifest_lines.append(f"    template_path: {_yaml_scalar(item['template_path'])}")
        manifest_lines.append(f"    synthetic_only: {_yaml_scalar(item['synthetic_only'])}")
        manifest_lines.append(f"    requires_approval: {_yaml_scalar(item['requires_approval'])}")
        manifest_lines.append(f"    approved_by_default: {_yaml_scalar(item['approved_by_default'])}")
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    lines = []
    lines.append("# DPABI Template Library Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Matrix: `{matrix_file}`")
    lines.append(f"- Templates generated: {len(generated_templates)}")
    lines.append(f"- Skipped functions: {len(skipped)}")
    lines.append("")
    lines.append("## Generated Templates")
    lines.append("")
    if generated_templates:
        lines.append("| Template ID | Function | Path | Requires Approval |")
        lines.append("|---|---|---|---:|")
        for item in generated_templates:
            lines.append(
                f"| {item['template_id']} | {item['function_name']} | "
                f"`{item['template_path']}` | {item['requires_approval']} |"
            )
    else:
        lines.append("No templates were generated.")
    lines.append("")
    lines.append("## Skipped")
    lines.append("")
    if skipped:
        for item in skipped:
            lines.append(f"- {item.get('function_name')}: {item.get('reason')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Generated templates are not executed automatically. Each generated template defaults to approved=false.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "dpabi_template_library",
        "backend": "python",
        "outputs": [str(index_path), str(manifest_path), str(report_path)]
        + [item["template_path"] for item in generated_templates],
        "metrics": {
            "templates_total": len(generated_templates),
            "skipped_total": len(skipped),
        },
        "warnings": warnings,
        "errors": errors,
    }
