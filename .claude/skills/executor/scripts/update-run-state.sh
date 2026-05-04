#!/bin/bash
# Update DARWIN run state
# Usage: update-run-state.sh <phase>
# Example: update-run-state.sh EXECUTE_COMPLETE

set -e

PHASE="$1"
RUN_FILE="docs/darwin/_meta/latest-run.json"

if [[ -z "$PHASE" ]]; then
    echo "Error: Phase required"
    echo "Usage: update-run-state.sh <phase>"
    exit 1
fi

if [[ ! -f "$RUN_FILE" ]]; then
    echo "Error: Run file not found: $RUN_FILE"
    exit 1
fi

# Update phase using jq
if command -v jq &> /dev/null; then
    jq --arg phase "$PHASE" '.phase = $phase' "$RUN_FILE" > "${RUN_FILE}.tmp" && mv "${RUN_FILE}.tmp" "$RUN_FILE"
    echo "Updated phase to: $PHASE"
else
    echo "Error: jq not installed"
    exit 1
fi
