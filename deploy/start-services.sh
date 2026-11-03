#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${NOMAS_ROOT:-/Hy-Nomas}"
cd "$ROOT"
export CUTLASS_PATH="${CUTLASS_PATH:-/opt/cutlass}"
export NOMAS_HTTP_PROXY_PORT="${NOMAS_HTTP_PROXY_PORT:-8081}"
export NOMAS_GATEWAY_HOST="127.0.0.1"
export PORT="${PORT:-18084}"
export NOMAS_SKIP_FRONTEND_BUILD=true
if [[ -z "${HF_HOME:-}" && -d "$ROOT/.hf_cache" ]]; then
  export HF_HOME="$ROOT/.hf_cache"
else
  export HF_HOME="${HF_HOME:-/workspace/hf_cache}"
fi
export STREETVIEW_EXPORT_FRAMES="${STREETVIEW_EXPORT_FRAMES:-1}"
export STREETVIEW_FRAME_STRIDE="${STREETVIEW_FRAME_STRIDE:-4}"
export RUNTIME_DIR="${RUNTIME_DIR:-$ROOT/.runtime/seg_ar_demo}"
export JOB_DB="${JOB_DB:-$RUNTIME_DIR/jobs.json}"
mkdir -p "$HF_HOME" "$RUNTIME_DIR"

MODEL_DIR="${NOMAS_MODELS_DIR:-/workspace/models}"
if [[ -z "${NOMAS_MODELS_DIR:-}" && -f "$ROOT/models/DiT/distilled_int8/diffusion_pytorch_model_ema_0_995_int8.safetensors" ]]; then
  MODEL_DIR="$ROOT/models"
fi
mkdir -p "$MODEL_DIR"
DIT="$MODEL_DIR/DiT/distilled_int8/diffusion_pytorch_model_ema_0_995_int8.safetensors"
PIXEL="$MODEL_DIR/VAE/PixelUMM_FT_FP8/diffusion_pytorch_model_fp8.safetensors"
ENCODER="$MODEL_DIR/VAE/DCAE-V/dc-ae-v-1.0-f32t4c32-bf16.pt"
if [[ ! -s "$DIT" || ! -s "$PIXEL" || ! -s "$ENCODER" ]]; then
  echo "[models] Downloading missing checkpoint(s) from Tencent Hugging Face; MODEL_DIR=$MODEL_DIR"
  hf download tencent/Hy-Nomas \
    --include "DiT/distilled_int8/diffusion_pytorch_model_ema_0_995_int8.safetensors" \
              "VAE/PixelUMM_FT_FP8/diffusion_pytorch_model_fp8.safetensors" \
              "VAE/DCAE-V/dc-ae-v-1.0-f32t4c32-bf16.pt" \
    --local-dir "$MODEL_DIR"
fi
for path in "$DIT" "$PIXEL" "$ENCODER"; do
  [[ -s "$path" ]] || { echo "[models] Missing $path" >&2; exit 2; }
done

# The official launcher starts three processes in the background and returns.
# It generates and reuses a private HTTP password file if not supplied.
bash scripts/inference/start_seg_ar_demo.sh \
  --single-gpu-low-mem-mode \
  --dit-weight "$DIT" \
  --save-path "$ROOT/outputs/seg_ar_demo" \
  "model.vae.checkpoint=$PIXEL" \
  "model.vae.encoder_checkpoint=$ENCODER" \
  "inference.video_size=[480,832]" \
  inference.infer_steps_video=6

echo "[health] Waiting for worker readiness on internal port $PORT"
READY=0
for i in $(seq 1 "${NOMAS_READY_POLLS:-150}"); do
  if PORT="$PORT" python "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check-health.py" 2>/dev/null; then
    READY=1
    break
  fi
  sleep 2
done
if [[ "$READY" -ne 1 ]]; then
  echo "[health] Worker not ready. Recent logs:" >&2
  tail -n 60 "$RUNTIME_DIR/worker_0.log" 2>/dev/null || true
  exit 1
fi
if [[ -f "$RUNTIME_DIR/http_server_8081.env" ]]; then
  echo "[auth] Credentials file (do not post its contents): $RUNTIME_DIR/http_server_8081.env"
fi
echo "[ready] Browse RunPod port ${NOMAS_HTTP_PROXY_PORT}/ and /streetview/index.html"
echo "[ready] Observations saved under $ROOT/outputs/seg_ar_demo/streetview/"
