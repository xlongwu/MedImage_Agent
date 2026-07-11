# Desktop Smoke Report v0.5.0

**Date:** 2026-06-20  
**Validator:** ZCode automated validation pass  
**Baseline interpreter:** `D:\Anaconda3\envs\mamba\python.exe`  
**Frontend:** Node.js via `npm --prefix src/frontend`  

## Scope

This smoke report covers the v0.5.0 scientific credibility convergence pass. It validates that the refactored frontend shell, DICOM conversion public execute endpoint gating, preprocessing pipeline panel mounting, FunRaw/T1Raw detector integration, and Phase 2 feature regression matrix all remain intact after route splitting and store isolation fixes.

- Backend route splitting and `dependencies.py` lazy `mock_store` import are in scope.
- Frontend `App.tsx` → `AppShellView` + feature workspace refactor is in scope.
- QC/SPM route store propagation fixes are in scope.
- MATLAB/SPM/DPABI/GPU external execution, rawdata writes, and clinical workflows remain out of scope for automated smoke.

## Backend Automated Checks

```powershell
D:\Anaconda3\envs\mamba\python.exe -m pytest tests/unit/ --tb=short --basetemp=.pytest_tmp -q
```

**Result:** 3662 passed, 4 skipped, 2 warnings in 197.72s (0:03:17)

Skipped tests are frontend typecheck/build placeholders in
`tests/unit/test_dicom_conversion_frontend_execute_ui_absence.py`; they are
deferred to the separate npm validation commands below.

### Focused Re-validation Matrix

| Focus Area | File | Result |
|---|---|---|
| Frontend source regression | `tests/unit/test_advanced_preprocessing_frontend_source.py` | 64 passed |
| Dashboard UI refactor source | `tests/unit/test_frontend_dashboard_ui_refactor_source.py` | 64 passed |
| Public execute endpoint gating | `tests/unit/test_dicom_conversion_public_execute_endpoint.py` | 55 passed |
| FunRaw/T1Raw detector + API | `tests/unit/test_funraw_t1raw_detector.py` | included in 55 passed |
| Phase 2 feature regression | `tests/unit/test_phase2_feature_regression_matrix.py` | included in 55 passed |

## Frontend Automated Checks

```powershell
npm --prefix src/frontend run typecheck
npm --prefix src/frontend run test
npm --prefix src/frontend run build
```

**Result:**

- `typecheck`: `tsc --noEmit` completed without errors.
- `test`: 4 test files, 47 tests passed.
- `build`: `vite build` completed in 449ms.

Build warning: `INEFFECTIVE_DYNAMIC_IMPORT` for `src/lib/api/legacy.ts`. This is a pre-existing bundler optimization note, not a build failure.

## Key Fixes Validated by This Pass

1. **Lazy `mock_store` import in `src/backend/app/api/dependencies.py`**  
   `get_project_store()` now imports `mock_store` inside the function body, so `Depends(...)` resolves the test-patched store after `monkeypatch.setattr(...)` runs.

2. **Store isolation patch list updated across 18 test files**  
   Tests now import `src.backend.app.services.mock_store as mock_store_module` and patch `mock_store_module.mock_store` in addition to route modules.

3. **Frontend source assertions aligned to refactored file locations**  
   - `AdvancedPreprocessingPipelinePanel` mount count is asserted against `PreprocessingWorkspace.tsx` instead of the shell.
   - Recent activity collapse is asserted against `CompactTaskLog.tsx`.
   - Empty-project recommended action is asserted against `DataConversionWorkspace.tsx`.
   - "Show technical details" toggle is asserted against the panel/review/workspace set instead of `AppShellView.tsx`.

4. **`test_dicom_conversion_public_execute_endpoint.py` patch list simplified**  
   Removed `dependencies` from the `monkeypatch.setattr(..., "mock_store", ...)` loop; the `mock_store_module` patch is sufficient because `dependencies.py` now performs a lazy import.

5. **`qc_routes.py` store propagation**  
   Confirmed earlier in the session that QC routes now receive the project store through the corrected dependency path rather than falling back to a global store.

## Environment Notes

- Full pytest uses `--basetemp=.pytest_tmp` to avoid Windows temp permission errors.
- The `.pytest_cache` directory is owned by a different user context in this workspace and remains inaccessible; pytest warns but continues.
- No SQLite runtime databases, build outputs, or user data were modified during this smoke pass.

## Remaining Risks

- The `INEFFECTIVE_DYNAMIC_IMPORT` warning suggests `legacy.ts` is both statically and dynamically imported. This does not block the build, but should be reviewed for chunking optimization in a follow-up.
- Frontend source tests are string-based and may need future updates when component copy or file paths change again.
- `test_dicom_conversion_frontend_execute_ui_absence.py` remains skipped in automated pytest because frontend typecheck/build are run via npm directly; the skipped assertions are intentionally covered by the npm commands above.

## Recommended Next Work

1. Address the `INEFFECTIVE_DYNAMIC_IMPORT` warning in `src/lib/api/legacy.ts`.
2. Convert frontend string-based source tests to component-prop assertions where feasible to reduce refactor fragility.
3. Lock the v0.5.0 test baseline counts in `PROJECT_STATE.md` once this smoke report is approved.
