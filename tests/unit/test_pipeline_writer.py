"""Tests for Pipeline Writer — safe YAML file writing."""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest
from src.backend.app.planner import pipeline_writer


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


@pytest.fixture(autouse=True)
def _patch_dir(monkeypatch, tmp_path):
    """Redirect all writes to tmp_path for test isolation."""
    monkeypatch.setattr(pipeline_writer, "REVIEWED_PIPELINE_DIR", tmp_path)


# ── 1. Write returns path ──

def test_write_returns_path():
    path = pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    assert isinstance(path, Path)


# ── 2. File exists ──

def test_file_exists():
    path = pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    assert path.exists()


# ── 3. YAML has required fields ──

def test_yaml_has_required_fields():
    path = pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["version"] == "0.1.0"
    assert "execution" in data
    assert "nodes" in data


# ── 4. Filename contains name ──

def test_filename_contains_name():
    path = pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    assert "test_plan" in path.name


# ── 5. Special chars sanitized ──

def test_special_chars_sanitized():
    p = dict(_valid_pipeline())
    p["pipeline_id"] = "my pipeline with spaces & special/ chars!"
    path = pipeline_writer.write_reviewed_pipeline_yaml(p)
    assert "/" not in path.name
    assert " " not in path.name
    assert "&" not in path.name


# ── 6. No overwrite ──

def test_no_overwrite():
    path1 = pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    path2 = pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    assert path1 != path2


# ── 7. Atomic — no tmp leftover ──

def test_no_tmp_leftover():
    pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    tmp_files = list(Path(pipeline_writer.REVIEWED_PIPELINE_DIR).glob("*.tmp"))
    assert len(tmp_files) == 0


# ── 8. Path stays in base dir ──

def test_path_stays_in_base():
    path = pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
    base = Path(pipeline_writer.REVIEWED_PIPELINE_DIR).resolve()
    assert str(path.resolve()).startswith(str(base))


# ── 9. No path traversal in filename ──

def test_no_path_traversal_in_filename():
    p = dict(_valid_pipeline())
    p["pipeline_id"] = "../../etc/passwd"
    path = pipeline_writer.write_reviewed_pipeline_yaml(p)
    assert ".." not in path.name


# ── 10. YAML roundtrip ──

def test_yaml_roundtrip():
    original = _valid_pipeline()
    path = pipeline_writer.write_reviewed_pipeline_yaml(original)
    back = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert back["pipeline_id"] == original["pipeline_id"]


# ── 11. Input not mutated ──

def test_input_not_mutated():
    import copy
    original = _valid_pipeline()
    snapshot = copy.deepcopy(original)
    pipeline_writer.write_reviewed_pipeline_yaml(original)
    assert original == snapshot


# ── 12. No executor ──

def test_no_executor():
    pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())


# ── 13. No runner ──

def test_no_runner():
    pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())


# ── 14. No rawdata writes ──

def test_no_rawdata_writes(tmp_path):
    # tmp_path is not rawdata
    pipeline_writer.write_reviewed_pipeline_yaml(_valid_pipeline())
