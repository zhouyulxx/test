#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${NOMAS_ROOT:-/Hy-Nomas}"
CONTROLLER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_COMMIT="${UPSTREAM_COMMIT:-a31c0fe0bcc493be188fd37ddba4ce2f674becb4}"

if [[ ! -f "$ROOT/scripts/inference/start_seg_ar_demo.sh" ]]; then
  echo "[install] Fetching pinned Hy-Nomas ${UPSTREAM_COMMIT} into ${ROOT}"
  mkdir -p "$ROOT"
  git -C "$ROOT" init -q
  git -C "$ROOT" remote add origin https://github.com/Tencent-Hunyuan/Hy-Nomas.git 2>/dev/null || true
  git -C "$ROOT" fetch --depth 1 origin "$UPSTREAM_COMMIT"
  git -C "$ROOT" checkout --force FETCH_HEAD
else
  echo "[install] Using existing Hy-Nomas source at $ROOT"
fi

mkdir -p "$ROOT/streetview" "$ROOT/apps/frontend/dist/streetview"
cp "$CONTROLLER/streetview/"*.py "$ROOT/streetview/"
python "$CONTROLLER/deploy/patch_upstream.py" "$ROOT"

if [[ ! -f "$ROOT/apps/frontend/dist/index.html" ]]; then
  echo "[install] Building official Hy-Nomas frontend"
  npm --prefix "$ROOT/apps/frontend" ci
  npm --prefix "$ROOT/apps/frontend" run build
fi
mkdir -p "$ROOT/apps/frontend/dist/streetview"
cp "$CONTROLLER/viewer/index.html" "$ROOT/apps/frontend/dist/streetview/index.html"

CUTLASS_PATH="${CUTLASS_PATH:-/opt/cutlass}"
if [[ ! -d "$CUTLASS_PATH/include/cutlass" ]]; then
  echo "[install] Downloading CUTLASS headers into $CUTLASS_PATH"
  mkdir -p "$(dirname "$CUTLASS_PATH")"
  git clone --depth 1 https://github.com/NVIDIA/cutlass.git "$CUTLASS_PATH"
fi

echo "[install] Done: $ROOT | CUTLASS_PATH=$CUTLASS_PATH"
