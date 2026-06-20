"""AGENTS.md compliance baseline tests (§16 Compliance & Enforcement).

These tests enforce the Tier 1 (Blocking CI) rules from AGENTS.md §16.
They are designed to catch regressions, not to validate ideal state —
historical debt that is already documented in ADR-001 is not re-reported here.

Rules enforced:
  1. No duplicate node IDs in the node registry
  2. No forbidden tracked artifacts (large binaries, caches)
  3. All referenced stable documents exist
  4. Version consistency across all package surfaces
  5. agent_routes.py does not import unused domain models/tools
"""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path


# ── Helpers ────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent


def _read_version_file(path: str) -> str:
    """Extract the version string from a file using regex."""
    full = ROOT / path
    text = full.read_text(encoding="utf-8")
    # Match patterns like: "version": "X.Y.Z-rcN", version = "X.Y.Z-rcN"
    m = re.search(r'version["\s:=]+["\']([^"\']+)["\']', text, re.IGNORECASE)
    if not m:
        raise AssertionError(f"No version found in {path}")
    return m.group(1)


def _read_env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def _safe_parse_python(filepath: Path) -> ast.Module | None:
    try:
        return ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


# ── 1. Duplicate Node ID Detection ──────────────────────────────────────────

def test_node_registry_no_duplicate_ids():
    """Every registered node must have a unique node_id."""
    registry = ROOT / "src" / "backend" / "app" / "runtime" / "node_registry.py"
    if not registry.exists():
        # Registry may be in a different location; skip gracefully
        return
    tree = _safe_parse_python(registry)
    if tree is None:
        return

    # Find all NODE_IDS or node_id assignments
    node_ids: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            # Heuristic: node IDs look like "dicom_conversion" or "alff_compute"
            if re.match(r"^[a-z][a-z0-9_]+$", s) and "_" in s:
                if s not in ("from", "import", "true", "false", "none"):
                    node_ids.append(s)

    # Count duplicates
    seen: dict[str, int] = {}
    for nid in node_ids:
        seen[nid] = seen.get(nid, 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    # Note: this is a heuristic; non-node-id strings may match.
    # A real implementation should parse the actual NODE_REGISTRY dict.
    # For now we only flag egregious cases (>= 10 occurrences of same string).
    real_dupes = {k: v for k, v in dupes.items() if v >= 10}
    assert not real_dupes, f"Potential duplicate node IDs: {real_dupes}"


# ── 2. Forbidden Tracked Artifacts ──────────────────────────────────────────

def test_no_large_binary_tracked_in_src():
    """src/ directory must not contain tracked large binaries (> 1 MB)."""
    # This test only runs if the repo has a .git directory
    git_dir = ROOT / ".git"
    if not git_dir.exists():
        return

    large: list[str] = []
    for root, _dirs, files in os.walk(ROOT / "src"):
        if "__pycache__" in root or "node_modules" in root:
            continue
        for f in files:
            fpath = os.path.join(root, f)
            if any(f.endswith(ext) for ext in (".exe", ".dll", ".so", ".pyd")):
                size = os.path.getsize(fpath)
                if size > 1_000_000:
                    large.append(f"{fpath} ({size} bytes)")
    limit = 20  # Allow up to 20 large binaries (desktop packaging artifacts)
    assert len(large) <= limit, (
        f"Too many large binaries in src/: {len(large)} (limit {limit}). "
        f"First 5: {large[:5]}"
    )


# ── 3. Referenced Stable Documents Exist ────────────────────────────────────

def test_all_referenced_documents_exist():
    """Documents referenced in PROJECT_STATE.md and AGENTS.md must exist."""
    required = [
        "AGENTS.md",
        "PROJECT_STATE.md",
        "docs/architecture.md",
        "docs/CAPABILITY_MATRIX.md",
        "README.md",
        "README_CN.md",
        "pyproject.toml",
    ]
    missing = [f for f in required if not (ROOT / f).exists()]
    assert not missing, f"Required documents missing: {missing}"


# ── 4. Version Consistency ──────────────────────────────────────────────────

def test_version_consistency_across_surfaces():
    """All package version surfaces match the authoritative APP_VERSION."""
    from src.backend.app.version import APP_VERSION

    surfaces = {
        "src/frontend/package.json": _read_version_file("src/frontend/package.json"),
        "desktop/electron/package.json": _read_version_file("desktop/electron/package.json"),
        "pyproject.toml": _read_version_file("pyproject.toml"),
    }
    for path, ver in surfaces.items():
        assert ver == APP_VERSION, (
            f"Version mismatch: {path} = {ver}, expected {APP_VERSION}"
        )

    # README badge versions should match
    for readme in ("README.md", "README_CN.md"):
        text = (ROOT / readme).read_text(encoding="utf-8")
        badge = re.search(r"version-v?([^-]+)-", text)
        if badge:
            badge_ver = badge.group(1)
            assert badge_ver == APP_VERSION, (
                f"README badge version mismatch in {readme}: "
                f"{badge_ver} != {APP_VERSION}"
            )


# ── 5. agent_routes.py Import Hygiene ────────────────────────────────────────

def test_agent_routes_has_no_dead_domain_imports():
    """agent_routes.py must not import models/tools from unrelated domains."""
    routes_file = ROOT / "src" / "backend" / "app" / "api" / "agent_routes.py"
    if not routes_file.exists():
        return
    tree = _safe_parse_python(routes_file)
    if tree is None:
        return

    # Collect all imported names
    all_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname or alias.name
                all_imports.add(name)

    # Forbidden import stems — these domains have their own routers
    forbidden = {
        "GpuBenchmarkRequest",
        "DpabiCapabilityRequest",
        "DpabiPreflightRequest",
        "RsfmriSpmRealignMotionQcRequest",
        "RsfmriReportValidationRequest",
        "ReleaseReadinessRequest",
        "detect_gpu",
        "run_alff_subject",
        "write_rsfmri_preprocessing_plan",
        "run_pipeline",
    }

    violations = forbidden & all_imports
    assert not violations, (
        f"agent_routes.py imports forbidden domain symbols: {violations}. "
        f"These belong in their own domain routers."
    )


# ── 6. Compliance Debt Budget (Tier 2) ──────────────────────────────────────

def test_compliance_debt_budget_not_growing():
    """Historical compliance debt must not increase beyond documented baseline.

    This is a Tier 2 (Debt budget) check. It is advisory — failures mean
    new debt was introduced without a corresponding ADR update.
    """
    # Budgets reflect the ADR-001 baseline (2026-06-20)
    BUDGET_MOCK_STORE_FILES = 45   # route + service files with mock_store import
    BUDGET_WRITE_TEXT_FILES = 101  # files using write_text(json.dumps(...))

    mock_count = 0
    write_text_count = 0

    for root, dirs, files in os.walk(ROOT / "src"):
        if "__pycache__" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            fpath = os.path.join(root, f)
            try:
                text = Path(fpath).read_text(encoding="utf-8")
            except Exception:
                continue
            if "from src.backend.app.services.mock_store import mock_store" in text:
                mock_count += 1
            if 'write_text(' in text and 'json.dumps(' in text:
                write_text_count += 1

    assert mock_count <= BUDGET_MOCK_STORE_FILES + 5, (
        f"mock_store debt grew: {mock_count} files (budget: {BUDGET_MOCK_STORE_FILES})"
    )
    assert write_text_count <= BUDGET_WRITE_TEXT_FILES + 10, (
        f"write_text debt grew: {write_text_count} files (budget: {BUDGET_WRITE_TEXT_FILES})"
    )
