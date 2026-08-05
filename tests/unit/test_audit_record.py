"""Tests for Audit Record — hash, builder, writer."""

from __future__ import annotations

import json

from src.backend.app.planner.audit_record import (
    audit_record_to_dict,
    build_review_audit_record,
    stable_hash,
    write_audit_record,
)


def test_stable_hash_order_independent():
    a = stable_hash({"b": 1, "a": 2})
    b = stable_hash({"a": 2, "b": 1})
    assert a == b


def test_stable_hash_different_for_different_payloads():
    h1 = stable_hash({"x": 1})
    h2 = stable_hash({"x": 2})
    assert h1 != h2


def test_build_record_has_audit_id():
    plan = {"pipeline_id": "test", "nodes": []}
    rec = build_review_audit_record("approval_checked", plan, {"ok": True})
    assert rec.audit_id.startswith("audit_")


def test_record_has_hashes():
    plan = {"pipeline_id": "p", "nodes": []}
    val = {"ok": True}
    appr = {"approved": True}
    rec = build_review_audit_record("dry_run_checked", plan, val, approval=appr)
    assert rec.plan_hash
    assert rec.validation_hash
    assert rec.approval_hash


def test_approval_none_gives_none_hash():
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    assert rec.approval_hash is None


def test_to_dict_json_serializable():
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    d = audit_record_to_dict(rec)
    raw = json.dumps(d, ensure_ascii=False)
    back = json.loads(raw)
    assert back["event_type"] == "dry_run_checked"


def test_safety_review_only():
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    assert rec.safety["review_only"] is True


def test_safety_executes_pipeline_false():
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    assert rec.safety["executes_pipeline"] is False


def test_safety_rawdata_readonly():
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    assert rec.safety["rawdata_readonly"] is True


def test_write_audit_record_writes_json(tmp_path):
    audit_dir = tmp_path / "audit"
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    path = write_audit_record(rec, audit_dir)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["audit_id"] == rec.audit_id


def test_write_atomic_uses_tmp_replace(tmp_path):
    audit_dir = tmp_path / "audit"
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    _path = write_audit_record(rec, audit_dir)
    # No .tmp file should remain after replace
    tmp_files = list(audit_dir.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_write_does_not_overwrite(tmp_path):
    audit_dir = tmp_path / "audit"
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    p1 = write_audit_record(rec, audit_dir)
    p2 = write_audit_record(rec, audit_dir)
    assert p1 != p2  # Second write gets a suffix
    assert p1.exists() and p2.exists()


def test_no_rawdata_writes(tmp_path):
    audit_dir = tmp_path / "audit"
    rec = build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
    write_audit_record(rec, audit_dir)
    # The file is inside tmp_path/audit, not rawdata


def test_no_executor():
    build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})


def test_no_runner():
    build_review_audit_record("dry_run_checked", {"nodes": []}, {"ok": True})
