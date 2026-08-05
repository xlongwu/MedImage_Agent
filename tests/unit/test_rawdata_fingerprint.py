"""Tests for rawdata_fingerprint — pure, read-only metadata hashing."""

from __future__ import annotations

import time

from src.backend.app.schemas.desktop import RawdataFingerprint
from src.backend.app.services.rawdata_fingerprint import build_rawdata_fingerprint


def test_missing_root_returns_warning():
    result = build_rawdata_fingerprint(["/nonexistent/path"])
    assert result.ok is True
    assert len(result.missing_roots) >= 1
    assert result.file_count == 0


def test_empty_root():
    """Empty directory → file_count 0."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        result = build_rawdata_fingerprint([td])
        assert result.file_count == 0
        assert result.total_size_bytes == 0


def test_two_files_count_and_size(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world!")
    result = build_rawdata_fingerprint([str(tmp_path)])
    assert result.file_count == 2
    assert result.total_size_bytes == 11


def test_newest_mtime_updates(tmp_path):
    f = tmp_path / "old.txt"
    f.write_text("old")
    time.sleep(0.01)
    result1 = build_rawdata_fingerprint([str(tmp_path)])
    m1 = result1.newest_mtime

    time.sleep(0.02)
    (tmp_path / "new.txt").write_text("new")
    result2 = build_rawdata_fingerprint([str(tmp_path)])
    m2 = result2.newest_mtime
    assert m2 is not None and m1 is not None
    assert m2 >= m1


def test_fingerprint_changes_on_file_added(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    fp1 = build_rawdata_fingerprint([str(tmp_path)]).fingerprint
    (tmp_path / "b.txt").write_text("y")
    fp2 = build_rawdata_fingerprint([str(tmp_path)]).fingerprint
    assert fp1 != fp2


def test_fingerprint_changes_on_size_change(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("small")
    fp1 = build_rawdata_fingerprint([str(tmp_path)]).fingerprint
    f.write_text("much larger content")
    fp2 = build_rawdata_fingerprint([str(tmp_path)]).fingerprint
    assert fp1 != fp2


def test_relative_path_hash_deterministic(tmp_path):
    (tmp_path / "z.txt").write_text("z")
    (tmp_path / "a.txt").write_text("a")
    h1 = build_rawdata_fingerprint([str(tmp_path)]).relative_path_hash
    h2 = build_rawdata_fingerprint([str(tmp_path)]).relative_path_hash
    assert h1 == h2


def test_suffix_filtering_includes_nii_gz(tmp_path):
    (tmp_path / "t1.nii").write_text("nii")
    (tmp_path / "t2.nii.gz").write_text("niigz")
    (tmp_path / "t3.json").write_text("json")
    result = build_rawdata_fingerprint(
        [str(tmp_path)],
        include_suffixes={".nii", ".nii.gz"},
    )
    assert result.file_count == 2


def test_max_files_truncates(tmp_path):
    for i in range(10):
        (tmp_path / f"{i:04d}.txt").write_text("x")
    result = build_rawdata_fingerprint([str(tmp_path)], max_files=5)
    assert result.truncated is True
    assert result.file_count == 5


def test_creates_no_files(tmp_path):
    before = {str(p) for p in tmp_path.rglob("*")}
    build_rawdata_fingerprint([str(tmp_path)])
    after = {str(p) for p in tmp_path.rglob("*")}
    assert after == before


def test_returns_rawdata_fingerprint_instance():
    result = build_rawdata_fingerprint(["/nonexistent"])
    assert isinstance(result, RawdataFingerprint)
    d = result.model_dump()
    assert d["file_count"] == 0


def test_does_not_modify_mtime(tmp_path):
    f = tmp_path / "marker.txt"
    f.write_text("untouched")
    orig = f.stat().st_mtime
    build_rawdata_fingerprint([str(tmp_path)])
    assert f.stat().st_mtime == orig
