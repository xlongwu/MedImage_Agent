from __future__ import annotations

import json
import sys
from pathlib import Path

from src.backend.app.tools.gpu_alff_runner import run_alff_subject
from src.backend.app.tools.gpu_utils import detect_gpu


def main() -> int:
    subject_id = sys.argv[1] if len(sys.argv) > 1 else "sub-001"
    input_nii = sys.argv[2] if len(sys.argv) > 2 else "./derivatives/spm_smooth/sub-001/func/sub-001_task-rest_bold_smooth.nii"
    derivatives_dir = sys.argv[3] if len(sys.argv) > 3 else "./derivatives"

    gpu_info = detect_gpu()
    print(json.dumps({"gpu_detection": gpu_info}, ensure_ascii=False, indent=2))

    result = run_alff_subject(
        subject_id=subject_id,
        input_nii=input_nii,
        derivatives_dir=derivatives_dir,
        tr=2.0,
        freq_band=[0.01, 0.08],
        prefer_gpu=True,
        require_gpu=False,
        benchmark_compare_cpu_gpu=True,
    )

    print(json.dumps({"alff_result": result}, ensure_ascii=False, indent=2))

    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
