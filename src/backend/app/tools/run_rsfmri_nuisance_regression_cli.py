from __future__ import annotations
import json, sys
from pathlib import Path
from src.backend.app.runtime.pipeline_executor import run_pipeline

def _make_approved_pipeline_copy(source: Path, target: Path) -> Path:
    try: import yaml
    except ImportError as exc: raise RuntimeError("Missing dependency: PyYAML.") from exc
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    for node in data.get("nodes", []):
        if node.get("id") in {"spm_slice_timing_subject","spm_realign_subject","spm_coregister_subject","spm_segment_subject","spm_normalize_subject","spm_smooth_subject"}:
            node.setdefault("params",{}); node["params"]["approved"] = True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target

def main() -> int:
    args = sys.argv[1:]; approved = "--approve" in args
    args = [a for a in args if a != "--approve"]
    pc = Path(args[0]) if args else Path("examples/project_config_dataset.yaml")
    pl = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_nuisance_regression.yaml")
    if approved: pl = _make_approved_pipeline_copy(pl, Path("outputs/work/rsfmri/approved_pipeline_nuisance_regression.yaml"))
    summary = run_pipeline(pc, pl)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    s = summary.get("status")
    return 0 if s == "SUCCESS" else (1 if s == "INVALID" else 2)

if __name__ == "__main__": raise SystemExit(main())
