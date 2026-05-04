from __future__ import annotations

from pathlib import Path

import yaml

from backend.app.runtime.agent_plan import create_agent_plan


def test_agent_plan_does_not_execute_pipeline(tmp_path: Path):
    project_config = tmp_path / "project_config.yaml"
    pipeline = tmp_path / "pipeline.yaml"

    project_config.write_text(
        yaml.safe_dump({
            "project": {"name": "test_project", "root_dir": "."},
            "third_party": {"spm_dir": "./third_party/spm12", "dpabi_dir": "./third_party/DPABI"},
            "runtime": {"work_dir": str(tmp_path / "work"), "log_dir": str(tmp_path / "logs"), "report_dir": str(tmp_path / "reports")},
            "safety": {"rawdata_readonly": True},
        }),
        encoding="utf-8",
    )

    pipeline.write_text(
        yaml.safe_dump({
            "pipeline_id": "test_plan_pipeline",
            "version": "0.1.0",
            "modality": "test",
            "description": "plan only",
            "execution": {"run_id": "run_plan_only"},
            "nodes": [
                {
                    "id": "data_inspection",
                    "name": "Data Inspection",
                    "agent": "data-inspector",
                    "backend": "python",
                    "depends_on": [],
                    "inputs": [],
                    "outputs": ["./work/dataset_index/dataset_index.json"],
                    "params": {},
                    "parallel_level": "project",
                    "gpu_supported": False,
                    "cache": False,
                }
            ],
        }),
        encoding="utf-8",
    )

    plan = create_agent_plan(
        agent_run_id="agent_test",
        project_config_path=str(project_config),
        pipeline_path=str(pipeline),
    )

    assert plan["ok"] is True
    assert plan["mode"] == "PLAN"
    assert plan["requires_approval"] is True
    assert plan["approved"] is False
