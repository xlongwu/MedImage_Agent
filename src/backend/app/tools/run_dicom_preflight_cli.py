from __future__ import annotations

import argparse
import json

from src.backend.app.services.dicom_preflight import build_dicom_preflight


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run read-only DICOM metadata preflight.")
    parser.add_argument("--project-id", default="brain-tumor-study", help="Project ID to include in the report.")
    parser.add_argument("--path", default="data/DemoData", help="DICOM root to inspect without modifying raw files.")
    parser.add_argument("--max-files", type=int, default=2000, help="Maximum DICOM files to sample for metadata.")
    return parser


def run(project_id: str, path: str, max_files: int) -> dict:
    response = build_dicom_preflight(project_id=project_id, roots=[path], max_files=max_files)
    return response.model_dump()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(project_id=args.project_id, path=args.path, max_files=args.max_files)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
