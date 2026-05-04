from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _escape_html(text: str | None) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def write_dataset_evaluation_report(
    dataset_summary_path: str,
    subject_qc_table_path: str,
    exclusion_recommendations_path: str,
    output_dir: str,
) -> dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = _read_json(Path(dataset_summary_path))
    subject_rows = _read_csv_rows(Path(subject_qc_table_path))
    attention_rows = _read_csv_rows(Path(exclusion_recommendations_path))

    md_path = out_dir / "dataset_evaluation_report.md"
    html_path = out_dir / "dataset_evaluation_report.html"

    # Generate Markdown
    lines: list[str] = []
    lines.append("# Dataset Evaluation Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- Run ID: {summary.get('run_id')}")
    lines.append(f"- Total subjects: {summary.get('subjects_total')}")
    lines.append(f"- Complete subjects: {summary.get('subjects_complete')}")
    lines.append(f"- Preprocessing success: {summary.get('subjects_preprocess_success')}")
    lines.append(f"- QC success: {summary.get('subjects_qc_success')}")
    lines.append(f"- Included subjects: {summary.get('subjects_include')}")
    lines.append(f"- Manual review: {summary.get('subjects_manual_review')}")
    lines.append(f"- Excluded subjects: {summary.get('subjects_exclude')}")
    lines.append(f"- Dataset quality score: {summary.get('dataset_quality_score')} / 100")
    lines.append("")
    lines.append("## Dataset Overview")
    lines.append("")
    lines.append(f"- Dataset index: `{summary.get('dataset_index')}`")
    lines.append("")
    lines.append("## Recommendation Summary")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    lines.append(f"| INCLUDE | {summary.get('subjects_include')} |")
    lines.append(f"| MANUAL_REVIEW | {summary.get('subjects_manual_review')} |")
    lines.append(f"| EXCLUDE | {summary.get('subjects_exclude')} |")
    lines.append("")
    lines.append("## Subjects Requiring Attention")
    lines.append("")
    if attention_rows:
        lines.append("| Subject ID | Recommendation | Reasons |")
        lines.append("|---|---|---|")
        for row in attention_rows:
            lines.append(f"| {row.get('subject_id')} | {row.get('recommendation')} | {row.get('reasons')} |")
    else:
        lines.append("No subjects require attention.")
    lines.append("")
    lines.append("## Subject QC Details")
    lines.append("")
    if subject_rows:
        lines.append("| Subject ID | Status | Smooth | QC | Recommendation | Shape | Mean | Std |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for row in subject_rows:
            lines.append(
                f"| {row.get('subject_id')} | {row.get('dataset_status')} | "
                f"{row.get('smooth_status')} | {row.get('qc_status')} | "
                f"{row.get('recommendation')} | {row.get('shape')} | "
                f"{row.get('mean')} | {row.get('std')} |"
            )
    else:
        lines.append("No subject QC data available.")
    lines.append("")
    lines.append("## Disclaimer")
    lines.append("")
    lines.append(
        "This report is for engineering QC and research preprocessing support only. "
        "It is not a clinical diagnosis."
    )

    md_content = "\n".join(lines)
    md_path.write_text(md_content, encoding="utf-8")

    # Generate HTML
    html_lines: list[str] = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append("<html>")
    html_lines.append("<head>")
    html_lines.append("<meta charset=\"UTF-8\">")
    html_lines.append("<title>Dataset Evaluation Report</title>")
    html_lines.append("<style>")
    html_lines.append("body { font-family: Arial, sans-serif; margin: 40px; }")
    html_lines.append("h1 { color: #333; }")
    html_lines.append("h2 { color: #555; border-bottom: 1px solid #ccc; padding-bottom: 5px; }")
    html_lines.append("table { border-collapse: collapse; width: 100%; margin: 20px 0; }")
    html_lines.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
    html_lines.append("th { background-color: #4CAF50; color: white; }")
    html_lines.append("tr:nth-child(even) { background-color: #f2f2f2; }")
    html_lines.append(".score { font-size: 24px; font-weight: bold; color: #4CAF50; }")
    html_lines.append(".disclaimer { background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }")
    html_lines.append("</style>")
    html_lines.append("</head>")
    html_lines.append("<body>")
    html_lines.append("<h1>Dataset Evaluation Report</h1>")
    html_lines.append("<h2>Executive Summary</h2>")
    html_lines.append("<ul>")
    html_lines.append(f"<li>Run ID: {_escape_html(summary.get('run_id'))}</li>")
    html_lines.append(f"<li>Total subjects: {summary.get('subjects_total')}</li>")
    html_lines.append(f"<li>Complete subjects: {summary.get('subjects_complete')}</li>")
    html_lines.append(f"<li>Preprocessing success: {summary.get('subjects_preprocess_success')}</li>")
    html_lines.append(f"<li>QC success: {summary.get('subjects_qc_success')}</li>")
    html_lines.append(f"<li>Included subjects: {summary.get('subjects_include')}</li>")
    html_lines.append(f"<li>Manual review: {summary.get('subjects_manual_review')}</li>")
    html_lines.append(f"<li>Excluded subjects: {summary.get('subjects_exclude')}</li>")
    html_lines.append(f"<li class='score'>Dataset quality score: {summary.get('dataset_quality_score')} / 100</li>")
    html_lines.append("</ul>")
    html_lines.append("<h2>Dataset Overview</h2>")
    html_lines.append(f"<p>Dataset index: <code>{_escape_html(summary.get('dataset_index'))}</code></p>")
    html_lines.append("<h2>Recommendation Summary</h2>")
    html_lines.append("<table>")
    html_lines.append("<tr><th>Category</th><th>Count</th></tr>")
    html_lines.append(f"<tr><td>INCLUDE</td><td>{summary.get('subjects_include')}</td></tr>")
    html_lines.append(f"<tr><td>MANUAL_REVIEW</td><td>{summary.get('subjects_manual_review')}</td></tr>")
    html_lines.append(f"<tr><td>EXCLUDE</td><td>{summary.get('subjects_exclude')}</td></tr>")
    html_lines.append("</table>")
    html_lines.append("<h2>Subjects Requiring Attention</h2>")
    if attention_rows:
        html_lines.append("<table>")
        html_lines.append("<tr><th>Subject ID</th><th>Recommendation</th><th>Reasons</th></tr>")
        for row in attention_rows:
            html_lines.append(
                f"<tr><td>{_escape_html(row.get('subject_id'))}</td>"
                f"<td>{_escape_html(row.get('recommendation'))}</td>"
                f"<td>{_escape_html(row.get('reasons'))}</td></tr>"
            )
        html_lines.append("</table>")
    else:
        html_lines.append("<p>No subjects require attention.</p>")
    html_lines.append("<h2>Subject QC Details</h2>")
    if subject_rows:
        html_lines.append("<table>")
        html_lines.append("<tr><th>Subject ID</th><th>Status</th><th>Smooth</th><th>QC</th><th>Recommendation</th><th>Shape</th><th>Mean</th><th>Std</th></tr>")
        for row in subject_rows:
            html_lines.append(
                f"<tr><td>{_escape_html(row.get('subject_id'))}</td>"
                f"<td>{_escape_html(row.get('dataset_status'))}</td>"
                f"<td>{_escape_html(row.get('smooth_status'))}</td>"
                f"<td>{_escape_html(row.get('qc_status'))}</td>"
                f"<td>{_escape_html(row.get('recommendation'))}</td>"
                f"<td>{_escape_html(row.get('shape'))}</td>"
                f"<td>{_escape_html(row.get('mean'))}</td>"
                f"<td>{_escape_html(row.get('std'))}</td></tr>"
            )
        html_lines.append("</table>")
    else:
        html_lines.append("<p>No subject QC data available.</p>")
    html_lines.append("<div class='disclaimer'>")
    html_lines.append("<strong>Disclaimer:</strong> This report is for engineering QC and research preprocessing support only. It is not a clinical diagnosis.")
    html_lines.append("</div>")
    html_lines.append("</body>")
    html_lines.append("</html>")

    html_content = "\n".join(html_lines)
    html_path.write_text(html_content, encoding="utf-8")

    return {
        "ok": True,
        "outputs": [str(md_path), str(html_path)],
        "md_path": str(md_path),
        "html_path": str(html_path),
    }
