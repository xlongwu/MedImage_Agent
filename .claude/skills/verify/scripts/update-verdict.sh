#!/bin/bash
# update-verdict.sh - Update latest-run.json with verification verdict
#
# Usage:
#   update-verdict.sh VERIFIED
#   update-verdict.sh FIXABLE "{run_dir}/verify/gaps.md"
#   update-verdict.sh BLOCKED "{run_dir}/verify/gaps.md"
#   update-verdict.sh RFI

set -euo pipefail

VERDICT="${1:-}"
GAPS_PATH="${2:-}"

META_FILE="docs/darwin/_meta/latest-run.json"

if [[ -z "$VERDICT" ]]; then
  echo "Error: Verdict required (VERIFIED|FIXABLE|BLOCKED|RFI)" >&2
  exit 1
fi

if [[ ! -f "$META_FILE" ]]; then
  echo "Error: No active run found at $META_FILE" >&2
  exit 1
fi

case "$VERDICT" in
  VERIFIED)
    jq '.phase = "COMPLETE" | .verdict = "VERIFIED"' "$META_FILE" > "${META_FILE}.tmp"
    ;;
  FIXABLE)
    if [[ -z "$GAPS_PATH" ]]; then
      echo "Error: FIXABLE requires gaps_path" >&2
      exit 1
    fi
    jq --arg gaps "$GAPS_PATH" '.phase = "COMPLETE" | .verdict = "FIXABLE" | .gaps_path = $gaps' "$META_FILE" > "${META_FILE}.tmp"
    ;;
  BLOCKED)
    if [[ -z "$GAPS_PATH" ]]; then
      echo "Error: BLOCKED requires gaps_path" >&2
      exit 1
    fi
    jq --arg gaps "$GAPS_PATH" '.phase = "COMPLETE" | .verdict = "BLOCKED" | .gaps_path = $gaps' "$META_FILE" > "${META_FILE}.tmp"
    ;;
  RFI)
    jq '.phase = "COMPLETE" | .verdict = "RFI"' "$META_FILE" > "${META_FILE}.tmp"
    ;;
  *)
    echo "Error: Unknown verdict: $VERDICT" >&2
    exit 1
    ;;
esac

mv "${META_FILE}.tmp" "$META_FILE"
echo "Updated $META_FILE with verdict: $VERDICT"
