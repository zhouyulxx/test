# Hy-Nomas StreetView · RTX 4090 experimental overlay

Experimental, non-official extension of [Tencent-Hunyuan/Hy-Nomas](https://github.com/Tencent-Hunyuan/Hy-Nomas). No model weights in this repository. Upstream base model, CUDA kernel and weights remain unchanged. Version: **v0.1**.

**Scope:** Export decoded RGB frames + camera-command metadata into a route-view-atlas prototype. It does **not** provide calibrated 3D geometry, complete 360° generation, multiple real-image anchor conditioning, or guaranteed cross-trajectory consistency. These are future research tasks. The viewer uses nearest-view selection, not geometric novel-view synthesis. Test with mock world before model generation.

## A. Easiest: upgrade the already-running RunPod Pod (no Docker rebuild)

The existing pod is an RTX 4090, with **Hy-Nomas source in `/Hy-Nomas` and model weights in `/Hy-Nomas/models`**. This single SSH command installs the extension, fixes the RTX 4090 FP8 conflict, rebuilds frontend only if missing, restarts Gateway/Worker, waits for `worker_online`, and enables authenticated port 8081:

```bash
# Public repo branch URL will be set after GitHub publish.
git clone --depth 1 --branch hy-nomas-streetview-v1 https://github.com/zhouyulxx/test.git /opt/streetview-controller
bash /opt/streetview-controller/deploy/upgrade-existing-pod.sh
```

Once ready, use RunPod's existing port **8081** Connect link. Browser routes:

- `/` — Official Hy-Nomas interactive world, text fallback works without Nomas-PE.
- `/streetview/index.html` — Route View Atlas viewer; click **Try mock world** before generating actual observations.

Authenticated username/password are in `/Hy-Nomas/.runtime/seg_ar_demo/http_server_8081.env`, mode 0600. Do **not** paste your password into a chat or commit.

**To find an observation manifest after generating a segment:**

```bash
find /Hy-Nomas/outputs/seg_ar_demo/streetview -name manifest.json
```

Copy its path after `/Hy-Nomas/outputs/seg_ar_demo/` into URL:

`/outputs/seg_ar_demo/streetview/<request-id>/manifest.json`

In viewer, enter that URL or navigate to `/streetview/index.html?manifest=/outputs/seg_ar_demo/streetview/<request-id>/manifest.json`.

## B. Docker: build a single-image, single-GPU RTX 4090 deployment

The included Dockerfile starts with Tencent's CUDA 13.0 image `hynomasoss/hynomasoss:cu130`, pins the Hy-Nomas upstream revision, clones CUTLASS, applies a **guarded** RTX 4090 patch (`deepgemm_fp8=false`, CUTLASS stays enabled), builds the frontend, and installs the observation exporter/viewer. **No large weights are baked into the image**; the startup script downloads the three required weight files to `/workspace/models` (or uses `NOMAS_MODELS_DIR`). The Qwen text encoder is fetched through Hugging Face on first model use.

```bash
docker build -t hy-nomas-streetview:v0.1 .
docker run --gpus all --rm -p 8081:8081 -v ./streetdata:/workspace \
  --shm-size=8g hy-nomas-streetview:v0.1
```

In **RunPod**, set Container Image to the published Docker image (if built in a registry), **HTTP Port `8081`**, container disk at least **150 GB**, one RTX 4090; do **not** override `Container start command` with `sleep infinity`, because this image's CMD starts the application and keeps PID 1 alive. Enable a persistent volume mounted at `/workspace` if you want model downloads to survive a Pod replacement. For a private GitHub Container Registry image, RunPod needs registry authentication; the existing-Pod upgrade path avoids that dependency.

The GitHub Actions workflow is a build recipe, not a claim that a hosted image exists. Building requires enough GitHub Actions disk space and compatible registry permissions. The supported immediate test is path A.

## Operational checks

```bash
python /opt/streetview-controller/deploy/check-health.py
curl -s http://127.0.0.1:18084/health
# Expected: worker_online=true, available=true

tail -n 50 /Hy-Nomas/.runtime/seg_ar_demo/worker_0.log
```

The launcher authenticates **port 8081** while keeping Gateway on `127.0.0.1:18084`. **Never expose 18084 to the Internet.** Do not expose model output folders outside the authenticated interface.

## Files

- `deploy/patch_upstream.py` — guarded idempotent two-location source patch
- `deploy/install.sh`, `deploy/upgrade-existing-pod.sh` — setup/restart on current Pod
- `deploy/start-services.sh`, `deploy/entrypoint.sh` — model provisioning, worker readiness and persistent Docker PID1
- `streetview/export.py` — decoded RGB to sampled PNGs and provenance-aware manifests
- `streetview/trajectories.py` — deterministic camera-trajectory JSON generator
- `viewer/index.html` — browser route observation explorer, with a mock world for tests
- `tests/test_export.py` — offline unit tests; no CUDA needed

## Local tests

```bash
python -m unittest discover -s tests -v
python streetview/trajectories.py --seconds 2 --yaw 180 --speed 0 --output /tmp/yaw.json
```

**Important known constraints:** Hy-Nomas camera positions are often normalized before injection. Pose metadata is **the requested input trajectory**, not measured world coordinates. For stable-prefix streamed segments, earlier tail frames can be replaced; when visible decoded frame count differs from requested frame count, this exporter intentionally declines to attach a potentially wrong pose. Reference-image upload through the official web UI requires Nomas-PE image captioning, which is not provisioned by this package. These conditions are disclosed instead of silently faking correctness.
