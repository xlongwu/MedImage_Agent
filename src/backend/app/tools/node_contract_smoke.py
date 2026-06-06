"""Minimal deterministic executor node for contract smoke testing.

Exercises every field of the executor node contract without any
external dependencies — no BIDS, MATLAB, SPM, DPABI, GPU, or
neuroimaging tools.

Registered as ``contract_smoke`` in the node registry so it can be
used in reviewed-plan execute tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_CONTEXT_FIELDS: tuple[str, ...] = (
    "run_id",
    "work_dir",
    "log_dir",
)


def run_contract_smoke_node(
    context: Any,
    node: Any,
) -> dict[str, Any]:
    """Return a structured result that exercises every contract field.

    **Happy path** (``fail`` param absent / falsy):
        * validates context fields
        * writes a JSON report artifact
        * writes a plain-text log artifact
        * returns ``ok=True`` with outputs, metrics, warnings, and an
          ``stdout_log`` reference

    **Failure path** (``node.params.fail`` truthy):
        * returns ``ok=False`` with a structured error message
        * does NOT raise an exception — failures must stay inside the
          result dict so the pipeline executor can capture them
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── 2. validate input context ──────────────────────────────────────
    for field in REQUIRED_CONTEXT_FIELDS:
        if not getattr(context, field, None):
            errors.append(f"MISSING_CONTEXT_FIELD: {field}")

    if errors:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": errors,
        }

    # ── 8. intentional failure path ────────────────────────────────────
    if node.params.get("fail"):
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "outputs": [],
            "metrics": {"contract_smoke_attempted": True},
            "warnings": warnings
            + [
                (
                    "CONTRACT_SMOKE_INTENTIONAL_FAILURE: "
                    "fail=true was set in node params."
                )
            ],
            "errors": ["CONTRACT_SMOKE_INTENTIONAL_FAILURE"],
        }

    # ── 3-5. happy path: produce artifacts ─────────────────────────────
    work_path = Path(context.work_dir)
    work_path.mkdir(parents=True, exist_ok=True)

    report_path = work_path / "contract_smoke_report.json"
    report_path.write_text(
        json.dumps(
            {
                "node_id": node.id,
                "run_id": context.run_id,
                "status": "ok",
                "message": "contract smoke node completed successfully",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    log_path = work_path / "contract_smoke.log"
    log_path.write_text(
        (
            f"[{context.run_id}] contract_smoke node started\n"
            f"[{context.run_id}] work_dir: {context.work_dir}\n"
            f"[{context.run_id}] log_dir:  {context.log_dir}\n"
            f"[{context.run_id}] contract_smoke node completed\n"
        ),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "node_id": node.id,
        "backend": "python",
        "outputs": [str(report_path), str(log_path)],
        "stdout_log": str(log_path),
        "metrics": {
            "artifacts_written": 2,
            "contract_version": "1.0.0",
            "ctx_run_id": context.run_id,
        },
        "warnings": warnings,
        "errors": [],
    }
