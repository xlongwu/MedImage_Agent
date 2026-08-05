"""Real data protocol advisor — recommend pipeline from data inventory."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def recommend_protocol_from_inventory(
    inventory: dict | None = None,
    inventory_path: str = "./reports/real_data_sandbox/data_inventory.json",
    output_dir: str = "./reports/real_data_sandbox",
) -> dict[str, Any]:
    """Generate protocol recommendation from data inventory (read-only, no execution)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if inventory is None:
        inv_path = Path(inventory_path)
        if not inv_path.exists():
            return {"ok": False, "errors": [f"Inventory not found: {inventory_path}"]}
        try:
            inventory = json.loads(inv_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return {"ok": False, "errors": [f"Failed to load inventory: {e}"]}

    subjects = inventory.get("subjects", [])
    completeness = inventory.get("completeness", {})

    has_t1w = completeness.get("has_t1w", 0) > 0
    has_bold = completeness.get("has_bold", 0) > 0
    has_fieldmap = completeness.get("has_fieldmap", 0) > 0

    # Determine pipeline
    if has_t1w and has_bold:
        pipeline = "rsfmri_spm_standard_v1"
    elif has_bold:
        pipeline = "rsfmri_python_quickstart"
    else:
        return {"ok": False, "errors": ["No usable data found (needs T1w or BOLD)"]}

    # Get TR from first subject with TR
    tr_values = [s.get("tr") for s in subjects if s.get("tr")]
    typical_tr = tr_values[0] if tr_values else 2.0

    # Get typical slice count
    slice_counts = [s.get("slice_count") for s in subjects if s.get("slice_count")]
    typical_slices = max(set(slice_counts), key=slice_counts.count) if slice_counts else 32

    # Parameters
    params = {
        "slice_timing_reference": "middle_slice",
        "realign_quality": 0.9,
        "normalize_voxel_size": [3, 3, 3],
        "smooth_fwhm": [6, 6, 6],
        "filter_band": [0.01, 0.08],
        "nuisance_model": "friston24",
        "tr": typical_tr,
        "slice_count": typical_slices,
    }

    risks = []
    if not has_fieldmap:
        risks.append("No fieldmap available; distortion correction skipped")
    if len(set(tr_values)) > 1:
        risks.append(f"TR varies across subjects ({min(tr_values)}-{max(tr_values)}s); check temporal filtering band")

    recommendation = {
        "ok": True,
        "node_id": "real_data_protocol_advisor",
        "backend": "python",
        "mode": "readonly_sandbox",
        "recommended_pipeline": pipeline,
        "suggested_params": params,
        "risks": risks,
        "requires_manual_review": True,
        "approval_required": True,
    }

    (out / "protocol_recommendation.json").write_text(
        json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return recommendation
