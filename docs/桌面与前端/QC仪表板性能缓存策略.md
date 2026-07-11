# QC Dashboard Performance and Cache Strategy

**Status:** Single-module prototype implemented for NIfTI QC Snapshot.
**Version:** v1.1
**Date:** 2026-06-18

---

## 1. Purpose

The QC Dashboard Summary Report (`POST /api/projects/{project_id}/qc-dashboard/report`)
composes 8 independent read-only sub-services.  Each sub-service scans rawdata,
reads NIfTI headers, parses sidecars, and generates report artifacts.
Generating a full dashboard report is therefore expensive:

- Third-party service reports (`build_rsfmri_qc_planning_report`,
  `build_motion_metrics_draft`) each internally call their own QC services,
  causing duplicate scans.
- The full backend test file currently takes approximately **154 seconds**
  (19 tests), dominated by repeated project creation, BIDS scanning, NIfTI
  header reads, and nested report artifact generation.

This document defines a **future caching strategy** to reduce latency while
preserving correctness, read-only safety, and explicit user control.

Binding statements:

- **This document does NOT implement caching.**  Current behavior is unchanged.
- **No preprocessing is introduced.**
- **Rawdata remains read-only.**
- This platform is **research-use only**, not for clinical diagnosis.

---

## 2. Current Performance Baseline

`build_qc_dashboard_report(project_id)` runs 8 modules **sequentially**:

| Module | Approx. Cost | Notes |
|---|---|---|
| `data_readiness` | Medium | Discovers image sources, validates metadata |
| `bids_validation` | High | Scans rawdata tree, reads sidecars, validates BIDS structure |
| `conversion_dry_run` | Low-Medium | Classifies import roots |
| `nifti_qc_snapshot` | High | Iterates NIfTI files, reads headers via nibabel, samples intensity stats |
| `bold_reference_readiness` | Medium | Filters BOLD from image sources, reads sidecar JSON |
| `motion_qc_readiness` | Medium | Discovers BOLD + motion files |
| `motion_metrics_draft` | High | Internally calls motion_qc_readiness, parses rp_*.txt, generates markdown |
| `rsfmri_qc_planning` | High | Internally calls bold_reference + motion_qc, generates markdown |

**Duplicate work**: `rsfmri_qc_planning` and `motion_metrics_draft` each
re-call their own sub-services, resulting in multiple scans of the same
rawdata within one dashboard generation.

Exact timing should be measured with instrumentation before cache implementation.

---

## 3. Cacheable vs Non-cacheable Outputs

| Module | Cacheable? | Cache Key Components | Invalidation Triggers | Notes |
|---|---|---|---|---|
| `data_readiness` | ✅ Partial | project_id, rawdata fingerprint, import records hash | rawdata change, import change | Top-level status + metrics cacheable; detailed image list may be too large |
| `bids_validation` | ✅ | project_id, rawdata fingerprint | rawdata change | Validation is pure function of rawdata tree |
| `conversion_dry_run` | ✅ | project_id, import roots, conversion params | import change | Low-cost; may not need caching |
| `nifti_qc_snapshot` | ✅ | project_id, rawdata fingerprint | rawdata change | Intensive; best caching ROI |
| `bold_reference_readiness` | ✅ | project_id, rawdata fingerprint | rawdata change | Depends on BOLD NIfTI discovery |
| `motion_qc_readiness` | ✅ | project_id, rawdata fingerprint | rawdata change | Depends on BOLD + motion file discovery |
| `motion_metrics_draft` | ✅ Conditional | project_id, rawdata fingerprint, motion file set | rawdata change, motion file change | Cache high; invalidate if rp_*.txt changed |
| `rsfmri_qc_planning` | ✅ Conditional | project_id, rawdata fingerprint | rawdata change | Cache high; avoid recomposing if sub-reports unchanged |
| `qc_dashboard_report` | ✅ (aggregate) | project_id, rawdata fingerprint, module versions | rawdata change, module change | The combined report itself is cacheable |

---

## 4. Cache Key Design

### Primary key: `rawdata_fingerprint`

A lightweight fingerprint computed from **filesystem metadata** (not image
content) to detect changes without hashing large files:

```json
{
  "file_count": 142,
  "total_size_bytes": 2147483648,
  "newest_mtime_iso": "2026-06-18T12:00:00Z",
  "relative_paths_hash": "sha256-of-sorted-path-list",
  "top_level_entries_hash": "sha256-of-immediate-dirs"
}
```

### Per-module cache key

```
SHA256(project_id | rawdata_fingerprint | module_name | module_version | params_hash)
```

Where:
- `project_id`: stable project identifier
- `rawdata_fingerprint`: the lightweight fingerprint above
- `module_name`: e.g. `"nifti_qc_snapshot"`
- `module_version`: incremented when the module code changes
- `params_hash`: for modules that accept parameters (conversion, metrics)

Do NOT require hashing entire medical images. The filesystem fingerprint
is sufficient to detect structural rawdata changes.

---

## 5. Invalidation Rules

Cache MUST invalidate when any of these change:

| Trigger | Detection |
|---|---|
| Rawdata directory path changes | `project_config.yaml` hash |
| `dataset_index_path` changes | Config hash |
| Import records change | Import records `modified_at` max |
| File count changes | Fingerprint `file_count` mismatch |
| Total byte size changes | Fingerprint `total_size_bytes` mismatch |
| Newest modified timestamp changes | Fingerprint `newest_mtime_iso` mismatch |
| Module version changes | `module_version` mismatch |
| Request params change | `params_hash` mismatch |
| User explicitly requests refresh | `cache=refresh` flag |
| Previous cache marked with errors | `cache_has_errors: true` flag |

Additionally, the user MUST be able to force refresh via explicit UI action.

---

## 6. Cache Storage Options

### Option A: In-memory process cache
- **Persistence**: Lost on restart.
- **Test isolation**: Automatic (per-test-process).
- **Concurrency**: Simple.
- **Verdict**: Good for development; insufficient for desktop UX.

### Option B: Project-local JSON cache under safe output directory
- **Persistence**: Survives restart.
- **Path**: `outputs/cache/qc_dashboard/<project_id>/module_cache.json`
- **Test isolation**: Needs monkeypatch of cache root.
- **Verdict**: Simple and transparent; good for MVP.

### Option C: SQLite dashboard store table
- **Persistence**: Survives restart.
- **Concurrency**: Built-in with WAL mode.
- **Test isolation**: Needs separate database path per test.
- **Verdict**: More robust; better for multi-module metadata indexing.

### Recommended approach for MVP

**Option B (project-local JSON cache)** as the primary artifact store, with
a thin metadata index in the existing SQLite desktop store for fast lookup:

- SQLite stores: `project_id`, `module_name`, `fingerprint`, `cache_path`,
  `generated_at`, `cache_hit_count`
- JSON files store full module payloads under `outputs/cache/qc_dashboard/`

This avoids SQLite BLOB management for large module responses while keeping
lookup fast.

---

## 7. API Contract Proposal

### Report generation with cache control

```text
POST /api/projects/{project_id}/qc-dashboard/report?cache=prefer
POST /api/projects/{project_id}/qc-dashboard/report?cache=refresh
POST /api/projects/{project_id}/qc-dashboard/report?cache=off
```

| Mode | Behavior |
|---|---|
| `prefer` (default) | Use cache if valid; regenerate expired/missing modules only |
| `refresh` | Regenerate all modules; update cache |
| `off` | Bypass cache entirely; do not write to cache |

### Metadata cache option (request body alternative)

```json
{
  "cache_policy": {
    "mode": "prefer",
    "ttl_seconds": 3600
  }
}
```

### Response extension (backward-compatible)

```json
{
  "cache": {
    "mode": "prefer",
    "hit": false,
    "module_hits": {
      "nifti_qc_snapshot": true,
      "bids_validation": false
    },
    "fingerprint": "abc123...",
    "generated_at": "...",
    "cache_warnings": ["Module 'motion_metrics_draft' had errors; not cached."]
  }
}
```

Current behavior (cache not implemented): the `cache` field is absent,
and existing clients ignore unknown fields.

---

## 8. Frontend UX Contract

Future UI additions to `QcDashboardSummaryPanel`:

| Control | Behavior |
|---|---|
| **Generate Report** | Default `cache=prefer` |
| **Load Latest** | Reads saved artifacts (no recomputation) |
| **Refresh / Regenerate** | Force `cache=refresh` |
| **Cache status indicator** | Shows "cached" vs "fresh" per module |
| **Cache timestamp** | Shows when each module was last cached |
| **Rawdata fingerprint summary** | Tooltip explaining what triggered cache invalidation |

UX rules:
- Cache indicators are informational only — never block user actions.
- "Cached" does NOT mean preprocessing was executed.
- "Stale" does NOT mean unsafe — it means changes were detected and the
  cache was invalidated.
- User can always force refresh.

---

## 9. Test Strategy

Before implementation, design tests for:

| Test | Assertion |
|---|---|
| Cache miss on first run | No cache hit; full generation |
| Cache hit on second run | All modules hit; response == first response |
| Rawdata mtime change invalidates | Adding/deleting a file → cache miss |
| Import record change invalidates | New import → data_readiness cache miss |
| Module version change invalidates | Increment version constant → cache miss |
| `cache=refresh` bypasses | Force flag → all modules regenerated |
| `cache=off` no reads/writes | No cache file created or read |
| Cache artifacts stay outside rawdata | All paths under `outputs/cache/` |
| Corrupt cache file falls back | Malformed JSON → regeneration, log warning |
| Test isolation via tmp cache root | Monkeypatch cache dir; tests order-independent |

---

## 10. Safety Rules

All caching must guarantee:

- **Never modify rawdata.**
- **Never store raw image data** in cache (references and metadata only).
- **Never accept arbitrary cache paths** from user input.
- **Project-scoped cache only** — no cross-project leakage.
- **Cache cannot enable execution** — no preprocessing path unlocks via cache.
- **Cache cannot suppress critical errors** silently — errors must still
  appear in the dashboard report.
- **Stale cache must be visibly marked** if used (frontend badge).
- **User can force refresh** at any time.

---

## 11. Recommended Implementation Order

1. **Fingerprint helper** — pure function: file count, total size, newest
   mtime, sorted relative path list.  No cache writes.
2. **Cache metadata schemas** — Pydantic models for cache entries.
3. **In-memory cache prototype** — for one module (NIfTI QC snapshot first).
4. **Module-level cache adapter** — wrapper around sub-service calls.
5. **Dashboard cache summary fields** — add `cache` key to response.
6. **Frontend cache indicators** — per-module "cached" / "fresh" badges.
7. **Invalidation tests** — rawdata change, module version bump.
8. **Extend to BIDS / Data Readiness** — apply same pattern.
9. **Optimize nested report calls** — avoid re-calling sub-services when
   their inputs haven't changed (e.g., `rsfmri_qc_planning` reuses
   `bold_reference_readiness` cache).

---

## 12. Current Implementation Status

The following items from this strategy have been implemented:

- [x] **Rawdata fingerprint helper** (`build_rawdata_fingerprint`)
- [x] **Fingerprint debug endpoint** (`GET /api/projects/{id}/qc-dashboard/fingerprint`)
- [x] **Cache metadata schemas** (`QcDashboardCacheSummary`, `QcDashboardModuleCacheRecord`, etc.)
- [x] **Cache response contract** (`QcDashboardReportResponse.cache` field, default `mode="off"`)
- [x] **Cache query parameter contract** (`POST .../qc-dashboard/report?cache=off|prefer|refresh`)
- [x] **NIfTI QC Snapshot module cache prototype** — cache writes on `refresh`, cache hits on `prefer` when fingerprint matches
- [x] **Frontend module hit/miss display** — per-module status badges in `QcDashboardSummaryPanel`

Not yet implemented:

- [ ] Cache for other 7 dashboard modules (`data_readiness`, `bids_validation`, etc.)
- [ ] SQLite cache metadata index (currently JSON-only)
- [ ] Cache cleanup / eviction policy
- [ ] Thumbnail cache
- [ ] `cache=prefer` auto-write policy
- [ ] Cross-project cache isolation enforcement beyond path-based naming

## 13. Open Questions

| # | Question | Status |
|---|---|---|
| 1 | How deep should the rawdata fingerprint go? Sub-file vs directory-level? | Proposed: directory-level (file count, size, mtime, path list hash) |
| 2 | SQLite vs JSON cache split boundary? | Proposed: SQLite for metadata index, JSON for payloads |
| 3 | Cache TTL vs fingerprint-only invalidation? | Proposed: fingerprint-only; TTL as optional override |
| 4 | How to cache module failures? | Never cache modules with hard errors; cache warnings as normal |
| 5 | Should thumbnails be cached? | Out of scope for dashboard cache; thumbnails are lazy-loaded per image |
| 6 | Does latest report count as cache? | No; latest report is a persisted artifact, not a cache |
| 7 | Cleanup policy for stale caches? | LRU eviction by project; manual "clear cache" button |
| 8 | Windows path normalization in fingerprint? | Use resolved absolute paths, forward-slashes |
| 9 | Multi-project concurrent access? | File-level locks via `portalocker` or similar if needed |

---

## 13. Immediate Next Safe Task

**Recommended: QC Dashboard Fingerprint Helper**

- Pure function: `build_rawdata_fingerprint(rawdata_dir: Path) -> RawdataFingerprint`
- Computes: file count, total byte size, newest mtime, sorted relative path list SHA-256
- No cache writes, no subprocess, no external tools
- Read-only access to rawdata filesystem metadata
- Tests: deterministic output, change detection, empty directory, symlink handling

This can be implemented and tested immediately without any caching changes.

---

*End of cache strategy document.  No caching has been implemented.
Current dashboard behavior is unchanged.*
