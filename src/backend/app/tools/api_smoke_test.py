from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        import requests
    except ImportError:
        print("Missing dependency: requests. Install with: pip install requests")
        return 1

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    checks = []

    def call(method: str, path: str, **kwargs):
        url = base_url.rstrip("/") + path
        response = requests.request(method, url, timeout=30, **kwargs)
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}

        checks.append({
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "ok": 200 <= response.status_code < 300,
            "payload": payload,
        })

    call("GET", "/health")
    call("GET", "/api/rsfmri/preprocessing-plan")
    call("GET", "/api/rsfmri/spm-slice-timing")
    call("GET", "/api/rsfmri/spm-realign-motion-qc")
    call("GET", "/api/rsfmri/st-realign-motion-qc")
    call("GET", "/api/rsfmri/coregistration-qc")
    call("GET", "/api/rsfmri/segmentation-tissue-qc")
    call("GET", "/api/rsfmri/normalization-qc")
    call("GET", "/api/rsfmri/smoothing-qc")
    call("GET", "/api/rsfmri/nuisance-regression")
    call("GET", "/api/rsfmri/temporal-filtering")
    call("GET", "/api/rsfmri/alff-falff")
    call("GET", "/api/rsfmri/reho")
    call("GET", "/api/rsfmri/functional-connectivity")
    call("GET", "/api/rsfmri/group-summary")
    call("GET", "/api/rsfmri/report-export/latest")
    call("GET", "/api/rsfmri/report-export/list")
    call("GET", "/api/rsfmri/report-validator/latest")
    call("GET", "/api/rsfmri/report-validator/list")
    call("GET", "/api/release-readiness")
    call("GET", "/api/pipelines")
    call("POST", "/api/agent/plan", json={
        "agent_run_id": "agent_run_001",
        "project_config_path": "examples/project_config_dataset.yaml",
        "pipeline_path": "examples/pipeline_subject_preprocess.yaml",
    })
    call("GET", "/api/agent-runs/agent_run_001")

    print(json.dumps({
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
    }, ensure_ascii=False, indent=2))

    return 0 if all(item["ok"] for item in checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
