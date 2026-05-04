from __future__ import annotations

from typing import Any

from src.backend.app.preprocessing.rsfmri_plan_builder import (
    build_rsfmri_preprocessing_plan,
)


def write_rsfmri_preprocessing_plan(
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict[str, Any]:
    return build_rsfmri_preprocessing_plan(
        work_dir=work_dir,
        report_dir=report_dir,
    )
