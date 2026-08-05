"""Tests for QC Dashboard cache metadata schemas.

Schema-only — no cache storage, no file I/O, no external tools.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.backend.app.schemas.desktop import (
    QcDashboardCacheSummary,
    QcDashboardModuleCacheRecord,
    QcDashboardReportResponse,
    RawdataFingerprint,
)
from src.backend.app.services.rawdata_fingerprint import (
    build_rawdata_fingerprint,
)

# ── RawdataFingerprint tests ────────────────────────────────────────────────


def test_fingerprint_accepts_helper_output():
    fp = build_rawdata_fingerprint(["/nonexistent"])
    assert isinstance(fp, RawdataFingerprint)
    assert fp.file_count == 0


def test_fingerprint_serializes():
    fp = RawdataFingerprint(ok=True, file_count=3, fingerprint="hash123")
    d = fp.model_dump()
    assert d["file_count"] == 3
    assert d["fingerprint"] == "hash123"


def test_fingerprint_missing_root():
    fp = RawdataFingerprint(
        ok=True,
        missing_roots=["/nonexistent"],
        warnings=["Root does not exist"],
    )
    assert fp.file_count == 0
    assert len(fp.missing_roots) == 1


def test_fingerprint_truncated():
    fp = RawdataFingerprint(ok=True, truncated=True, file_count=20000, max_files=20000)
    assert fp.truncated is True


# ── QcDashboardModuleCacheRecord tests ──────────────────────────────────────


def test_cache_record_defaults():
    rec = QcDashboardModuleCacheRecord(module_id="data_readiness")
    assert rec.status == "miss"
    assert rec.hit is False
    assert rec.stale is False


def test_cache_record_hit():
    rec = QcDashboardModuleCacheRecord(
        module_id="nifti_qc_snapshot",
        status="hit",
        hit=True,
        cache_key="key123",
        fingerprint="fp456",
        module_version="1",
        generated_at="2026-01-01T00:00:00Z",
        artifact_path="out/cache/nifti.json",
    )
    assert rec.hit is True
    assert rec.status == "hit"


def test_cache_record_stale():
    rec = QcDashboardModuleCacheRecord(
        module_id="data_readiness",
        status="stale",
        stale=True,
        warnings=["Fingerprint changed"],
    )
    assert rec.stale is True


# ── QcDashboardCacheSummary tests ───────────────────────────────────────────


def test_cache_summary_defaults():
    summary = QcDashboardCacheSummary()
    assert summary.mode == "off"
    assert summary.hit is False


def test_cache_summary_module_hits():
    summary = QcDashboardCacheSummary(
        mode="prefer",
        hit=True,
        fingerprint="fp",
        module_hits={"nifti_qc_snapshot": True, "data_readiness": False},
        module_records=[
            QcDashboardModuleCacheRecord(module_id="nifti_qc_snapshot", status="hit", hit=True),
            QcDashboardModuleCacheRecord(module_id="data_readiness", status="miss"),
        ],
    )
    assert summary.mode == "prefer"
    assert summary.module_hits["nifti_qc_snapshot"] is True
    assert summary.module_hits["data_readiness"] is False
    assert len(summary.module_records) == 2


def test_invalid_cache_mode_rejected():
    with pytest.raises(ValidationError):
        QcDashboardCacheSummary(mode="invalid")


def test_invalid_cache_status_rejected():
    with pytest.raises(ValidationError):
        QcDashboardModuleCacheRecord(module_id="x", status="invalid")


# ── No side effects ─────────────────────────────────────────────────────────


def test_report_response_defaults_cache_off():
    resp = QcDashboardReportResponse(
        ok=True,
        project_id="p1",
        status="ready",
        generated_at="t",
        report_dir="d",
        json_path="j",
        markdown_path="m",
    )
    assert resp.cache.mode == "off"
    assert resp.cache.hit is False


def test_report_response_serializes_cache():
    resp = QcDashboardReportResponse(
        ok=True,
        project_id="p1",
        status="ready",
        generated_at="t",
        report_dir="d",
        json_path="j",
        markdown_path="m",
    )
    d = resp.model_dump()
    assert d["cache"]["mode"] == "off"


def test_schemas_create_no_files(tmp_path):
    before = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    RawdataFingerprint(ok=True)
    QcDashboardModuleCacheRecord(module_id="x")
    QcDashboardCacheSummary()
    after = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    assert after == before
