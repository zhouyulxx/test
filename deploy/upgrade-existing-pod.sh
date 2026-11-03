#!/usr/bin/env bash
# One command upgrade for the CURRENT running official Pod; reuses its models.
set -Eeuo pipefail
CONTROLLER="$(cd "$(dirname "$0")/.." && pwd)"
export NOMAS_ROOT="${NOMAS_ROOT:-/Hy-Nomas}"
export CUTLASS_PATH="${CUTLASS_PATH:-$NOMAS_ROOT/cutlass}"
"$CONTROLLER/deploy/install.sh"
if [[ -f "$NOMAS_ROOT/.runtime/seg_ar_demo/gateway.pid" ]]; then
  echo "[upgrade] Restarting existing demo to pick up patched worker/exporter"
  (cd "$NOMAS_ROOT" && bash scripts/inference/stop_seg_ar_demo.sh) || true
fi
"$CONTROLLER/deploy/start-services.sh"
