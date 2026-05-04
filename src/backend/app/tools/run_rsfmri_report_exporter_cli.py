from __future__ import annotations
import json, sys; from pathlib import Path
from src.backend.app.runtime.pipeline_executor import run_pipeline
def main() -> int:
    args = sys.argv[1:]
    pc = Path(args[0]) if args else Path("examples/project_config_dataset.yaml")
    pl = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_report_exporter.yaml")
    s = run_pipeline(pc, pl); print(json.dumps(s, ensure_ascii=False, indent=2))
    st = s.get("status"); return 0 if st == "SUCCESS" else (1 if st == "INVALID" else 2)
if __name__ == "__main__": raise SystemExit(main())
