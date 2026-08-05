"""Real data risk reporter — generate risk assessment from data inventory."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_risk_report(
    inventory: dict | None = None,
    inventory_path: str = "./reports/real_data_sandbox/data_inventory.json",
    output_dir: str = "./reports/real_data_sandbox",
) -> dict[str, Any]:
    """Generate a risk report from a data inventory (read-only)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if inventory is None:
        inv_path = Path(inventory_path)
        if not inv_path.exists():
            return {"ok": False, "errors": [f"Inventory not found: {inventory_path}. Run data inspection first."]}
        try:
            inventory = json.loads(inv_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return {"ok": False, "errors": [f"Failed to load inventory: {e}"]}

    subjects = inventory.get("subjects", [])
    completeness = inventory.get("completeness", {})
    risks = []
    warnings = []

    # Risk 1: Missing critical data
    missing_t1w = completeness.get("subjects_total", 0) - completeness.get("has_t1w", 0)
    missing_bold = completeness.get("subjects_total", 0) - completeness.get("has_bold", 0)
    if missing_t1w > 0:
        risks.append({"severity": "critical", "check": "missing_t1w",
                       "count": missing_t1w, "message": f"{missing_t1w} subjects missing T1w"})
    if missing_bold > 0:
        risks.append({"severity": "critical", "check": "missing_bold",
                       "count": missing_bold, "message": f"{missing_bold} subjects missing BOLD"})

    # Risk 2: TR variation
    trs = [s.get("tr") for s in subjects if s.get("tr")]
    if len(set(trs)) > 1:
        risks.append({"severity": "high", "check": "tr_inconsistency",
                       "values": list(set(trs)), "message": f"TR varies across subjects: {set(trs)}"})

    # Risk 3: Slice count variation
    slice_counts = [s.get("slice_count") for s in subjects if s.get("slice_count")]
    if len(set(slice_counts)) > 1:
        risks.append({"severity": "medium", "check": "slice_count_inconsistency",
                       "values": list(set(slice_counts)), "message": f"Slice count varies: {set(slice_counts)}"})

    # Risk 4: Missing fieldmap
    if completeness.get("has_fieldmap", 0) == 0:
        risks.append({"severity": "medium", "check": "no_fieldmap",
                       "message": "No fieldmap data found; distortion correction unavailable"})

    # Risk 5: File size anomalies
    size_risks = _check_file_sizes(subjects)
    risks.extend(size_risks)

    # Risk 6: Naming issues
    naming_count = completeness.get("naming_issues", 0)
    if naming_count > 0:
        risks.append({"severity": "low", "check": "naming_issues",
                       "count": naming_count, "message": f"{naming_count} BIDS naming issues found"})

    # Risk 7: Missing participants.tsv
    if not completeness.get("has_participants_tsv"):
        warnings.append("No participants.tsv found; limited demographic information available")

    summary = {
        "ok": True,
        "node_id": "real_data_risk_reporter",
        "backend": "python",
        "mode": "readonly_sandbox",
        "subjects_total": completeness.get("subjects_total", 0),
        "risks_total": len(risks),
        "critical_risks": sum(1 for r in risks if r["severity"] == "critical"),
        "high_risks": sum(1 for r in risks if r["severity"] == "high"),
        "risks": risks,
        "warnings": warnings,
        "overall_risk": "HIGH" if any(r["severity"] == "critical" for r in risks) else (
            "MEDIUM" if any(r["severity"] == "high" for r in risks) else "LOW"
        ),
    }

    (out / "risk_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown report
    lines = [
        "# Real Data Risk Report",
        "",
        f"Subjects: {summary['subjects_total']}",
        f"Overall Risk: **{summary['overall_risk']}**",
        f"Risks: {len(risks)} total ({summary['critical_risks']} critical, {summary['high_risks']} high)",
        "",
        "## Risk Details",
        "",
        "| Severity | Check | Detail |",
        "|----------|-------|--------|",
    ]
    for r in risks:
        lines.append(f"| {r['severity']} | {r['check']} | {r['message']} |")

    lines += [
        "",
        "## Safety Note",
        "",
        "This report is generated from read-only metadata inspection.",
        "No rawdata was modified. No preprocessing was executed.",
        "No clinical conclusions are drawn.",
    ]
    (out / "risk_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return summary


def _check_file_sizes(subjects: list[dict]) -> list[dict]:
    risks = []
    sizes = []
    for s in subjects:
        for key in ("t1w", "bold"):
            path_str = s.get(key)
            if path_str:
                p = Path(path_str)
                if p.exists():
                    sizes.append((s["subject_id"], key, p.stat().st_size))

    if not sizes:
        return risks

    t1w_sizes = [sz for _, key, sz in sizes if key == "t1w"]
    bold_sizes = [sz for _, key, sz in sizes if key == "bold"]

    for key, sz_list in [("t1w", t1w_sizes), ("bold", bold_sizes)]:
        if len(sz_list) < 2:
            continue
        avg = sum(sz_list) / len(sz_list)
        for subj_id, k, sz in sizes:
            if k == key and sz < avg * 0.3:
                risks.append({"severity": "medium", "check": f"small_{key}",
                               "subject": subj_id, "message": f"{subj_id}: {key} is significantly smaller than average"})

    return risks[:10]
