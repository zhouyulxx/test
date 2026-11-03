#!/usr/bin/env bash
set -Eeuo pipefail
CONTROLLER="$(cd "$(dirname "$0")/.." && pwd)"
"$CONTROLLER/deploy/install.sh"
"$CONTROLLER/deploy/start-services.sh"
# The official service launcher daemonizes. Keep Docker PID 1 alive and report
# logs; shutdown is handled by the container runtime when the Pod stops.
exec tail -n 20 -F "${RUNTIME_DIR:-/Hy-Nomas/.runtime/seg_ar_demo}/gateway.log" \
  "${RUNTIME_DIR:-/Hy-Nomas/.runtime/seg_ar_demo}/worker_0.log"
