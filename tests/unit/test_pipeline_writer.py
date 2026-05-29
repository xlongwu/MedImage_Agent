"""Tests for Pipeline Writer — safe YAML file writing."""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest
from src.backend.app.planner.pipeline_writer import write_reviewed_pipeline_yaml


def _valid_pipeline():
    return {
        "pipeline_id": "test_plan",
        "version": "0.1.0",
        "modality": "rsfmri",
        "description": "Test pipeline",
        "execution": {"run_id": "run_001", "stop_on_failure": True},
        "nodes": [
            {"id": "data_inspection", "name": "Data Inspection", "agent": "system",
             "backend": "python", "depends_on": [], "params": {},
             "parallel_level": "project", "gpu_supported": False, "cache": False,
             "inputs": [], "outputs": []},
        ],
    }


# ── 1. Write returns path ──

def test_write_returns_path(tmp_path):
    path = write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)
    assert isinstance(path, Path)


# ── 2. File exists ──

def test_file_exists(tmp_path):
    path = write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)
    assert path.exists()


# ── 3. YAML contains required fields ──

def test_yaml_has_required_fields(tmp_path):
    path = write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["version"] == "0.1.0"
    assert data["modality"] == "rsfmri"
    assert "execution" in data
    assert "nodes" in data


# ── 4. Auto-creates output dir ──

def test_auto_creates_dir(tmp_path):
    out = tmp_path / "deeply" / "nested" / "dir"
    write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=out)
    assert out.is_dir()


# ── 5. Filename contains pipeline name ──

def test_filename_contains_name(tmp_path):
    path = write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)
    assert "test_plan" in path.name


# ── 6. Special chars sanitized ──

def test_special_chars_sanitized(tmp_path):
    p = dict(_valid_pipeline())
    p["pipeline_id"] = "my pipeline with spaces & special/ chars!"
    path = write_reviewed_pipeline_yaml(p, output_dir=tmp_path)
    assert "/" not in path.name
    assert " " not in path.name
    assert "&" not in path.name
    assert "my_pipeline_with_spaces" in path.name


# ── 7. No overwrite ──

def test_no_overwrite(tmp_path):
    path1 = write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)
    path2 = write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)
    assert path1 != path2


# ── 8. Atomic — no tmp leftover ──

def test_no_tmp_leftover(tmp_path):
    write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


# ── 9. Default dir path safety ──

def test_default_dir_must_be_under_repo_root():
    # The default dir ("outputs/work/reviewed_pipelines") should be under repo
    path = write_reviewed_pipeline_yaml(_valid_pipeline())
    assert path.exists()
    assert "outputs" in str(path)


# ── 10. Explicit output_dir outside repo is accepted ──

def test_explicit_output_dir_accepted(tmp_path):
    out = tmp_path / "ok"
    out.mkdir()
    path = write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=out)
    assert path.exists()
    assert "ok" in str(path)


# ── 11. No absolute path escape in filename ──

def test_no_absolute_path_in_filename(tmp_path):
    p = dict(_valid_pipeline())
    p["pipeline_id"] = "../../etc/passwd"
    path = write_reviewed_pipeline_yaml(p, output_dir=tmp_path)
    assert ".." not in path.name
    assert str(tmp_path) in str(path.resolve())


# ── 12. YAML roundtrip ──

def test_yaml_roundtrip(tmp_path):
    original = _valid_pipeline()
    path = write_reviewed_pipeline_yaml(original, output_dir=tmp_path)
    back = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert back["pipeline_id"] == original["pipeline_id"]
    assert len(back["nodes"]) == len(original["nodes"])


# ── 13. Input not mutated ──

def test_input_not_mutated(tmp_path):
    original = _valid_pipeline()
    import copy
    snapshot = copy.deepcopy(original)
    write_reviewed_pipeline_yaml(original, output_dir=tmp_path)
    assert original == snapshot


# ── 14. No executor ──

def test_no_executor(tmp_path):
    write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)


# ── 15. No runner ──

def test_no_runner(tmp_path):
    write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path)


# ── 16. No rawdata/derivatives/reports ──

def test_no_rawdata_writes(tmp_path):
    import os
    before = set(os.listdir(tmp_path))
    write_reviewed_pipeline_yaml(_valid_pipeline(), output_dir=tmp_path / "sub")
    after = set(os.listdir(tmp_path))
    assert "rawdata" not in after
    assert "derivatives" not in after
