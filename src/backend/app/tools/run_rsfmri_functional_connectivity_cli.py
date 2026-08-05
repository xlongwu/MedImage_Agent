from __future__ import annotations

import json
import sys
from pathlib import Path

from src.backend.app.runtime.pipeline_executor import run_pipeline


def _make_approved(s: Path, t: Path) -> Path:
    import yaml

    d = yaml.safe_load(s.read_text(encoding="utf-8"))
    for n in d.get("nodes", []):
        if n.get("id") in {
            "spm_slice_timing_subject",
            "spm_realign_subject",
            "spm_coregister_subject",
            "spm_segment_subject",
            "spm_normalize_subject",
            "spm_smooth_subject",
        }:
            n.setdefault("params", {})
            n["params"]["approved"] = True
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    return t


def main() -> int:
    args = sys.argv[1:]
    ap = "--approve" in args
    args = [a for a in args if a != "--approve"]
    pc = Path(args[0]) if args else Path("examples/project_config_dataset.yaml")
    pl = (
        Path(args[1])
        if len(args) > 1
        else Path("examples/pipeline_rsfmri_functional_connectivity.yaml")
    )
    if ap:
        pl = _make_approved(pl, Path("outputs/work/rsfmri/approved_pipeline_fc.yaml"))
    s = run_pipeline(pc, pl)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    st = s.get("status")
    return 0 if st == "SUCCESS" else (1 if st == "INVALID" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
