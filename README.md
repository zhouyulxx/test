# Hy-Nomas StreetView · RTX 4090 experimental overlay

Experimental, non-official extension of [Tencent-Hunyuan/Hy-Nomas](https://github.com/Tencent-Hunyuan/Hy-Nomas). No model weights in this repository. Upstream base model, CUDA kernel and weights remain unchanged. Version: **v0.2 (private deployment patch)**.

**Scope:** Export decoded RGB frames + camera-command metadata into a route-view-atlas prototype. It does **not** provide calibrated 3D geometry, complete 360° generation, multiple real-image anchor conditioning, or guaranteed cross-trajectory consistency. These are future research tasks. The viewer uses nearest-view selection, not geometric novel-view synthesis. Test with mock world before model generation.

## A. Easiest: upgrade the already-running RunPod Pod (no Docker rebuild)

The Docker deployment uses **Hy-Nomas source in `/Hy-Nomas`, controller source in `/opt/streetview`, and model weights in `/workspace/models`**. This single SSH command installs the extension, fixes the RTX 4090 FP8 conflict, rebuilds frontend only if missing, restarts Gateway/Worker, waits for `worker_online`, and enables authenticated port 8081:

```bash
# Public repo branch URL will be set after GitHub publish.
git clone --depth 1 --branch hy-nomas-streetview-v1 https://github.com/zhouyulxx/test.git /opt/streetview-controller
bash /opt/streetview-controller/deploy/upgrade-existing-pod.sh
```

Once ready, use RunPod's existing port **8081** Connect link. Browser routes:

- `/` — Official Hy-Nomas interactive world, official interface. The StreetView controller submits structured JSON prompts without Nomas-PE.
- `/streetview/index.html` — Route View Atlas viewer; click **Try mock world** before generating actual observations.

Authenticated username/password are in `/Hy-Nomas/.runtime/seg_ar_demo/http_server_8081.env`, mode 0600. Do **not** paste your password into a chat or commit.

**To find an observation manifest after generating a segment:**

```bash
find /Hy-Nomas/outputs/seg_ar_demo/streetview -name manifest.json
```

The gateway mounts `/Hy-Nomas/outputs/seg_ar_demo/` at `/outputs/`. Use:

`/outputs/streetview/<request-id>/manifest.json`

In viewer, enter that URL or navigate to `/streetview/index.html?manifest=/outputs/streetview/<request-id>/manifest.json`.

## B. Docker: build a single-image, single-GPU RTX 4090 deployment

The included Dockerfile starts with Tencent's CUDA 13.0 image `hynomasoss/hynomasoss:cu130`, pins the Hy-Nomas upstream revision, uses the base image CUTLASS checkout, applies a **guarded** RTX 4090 patch (`deepgemm_fp8=false`, CUTLASS stays enabled), builds the frontend, and installs the observation exporter/viewer. **No large weights are baked into the image**; the startup script downloads the three required weight files to `/workspace/models` (or uses `NOMAS_MODELS_DIR`). The Qwen text encoder is fetched through Hugging Face on first model use.

```bash
docker build -t hy-nomas-streetview:v0.1 .
docker run --gpus all --rm -p 8081:8081 -v ./streetdata:/workspace \
  --shm-size=8g hy-nomas-streetview:v0.1
```

In **RunPod**, set Container Image to the published Docker image (if built in a registry), **HTTP Port `8081`**, container disk at least **150 GB**, one RTX 4090; do **not** override `Container start command` with `sleep infinity`, because this image's CMD starts the application and keeps PID 1 alive. Enable a persistent volume mounted at `/workspace` if you want model downloads to survive a Pod replacement. For a private GitHub Container Registry image, RunPod needs registry authentication; the existing-Pod upgrade path avoids that dependency.

The v0.1 image `ghcr.io/zhouyulxx/test:streetview-v0.1` was successfully built and deployed on an RTX 4090. This v0.2 patch has not been published to GitHub or rebuilt into that image. A replacement Pod using v0.1 alone will not contain the later fixes.

## Operational checks

```bash
PORT=18084 python /opt/streetview/deploy/check-health.py
curl -s http://127.0.0.1:18084/health
# Expected: worker_online=true, available=true

tail -n 50 /Hy-Nomas/.runtime/seg_ar_demo/worker_0.log
```

The launcher authenticates **port 8081** while keeping Gateway on `127.0.0.1:18084`. **Never expose 18084 to the Internet.** Do not expose model output folders outside the authenticated interface.

## Files

- `deploy/patch_upstream.py` — guarded idempotent worker/exporter/streaming-device source patch
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

**Important known constraints:** Hy-Nomas camera positions are often normalized before injection. Pose metadata is **the requested input trajectory**, not measured world coordinates. For stable-prefix streamed segments, earlier tail frames can be replaced; the exporter uses decoder metadata only when the decoded length exactly matches the requested frames plus the replacement tail. It leaves replacement frames without poses and declines other ambiguous mappings. Reference-image upload through the official web UI requires Nomas-PE image captioning, which is not provisioned by this package. These conditions are disclosed instead of silently faking correctness.

## Four-step generation check

Run `python /opt/streetview/deploy/smoke-test.py` inside the Pod after the worker is ready. It submits initial, left-turn, return, and forward segments in one preserved session, and writes a report, observation atlas, and contact sheet under `outputs/seg_ar_demo/streetview-tests/`. The web viewer offers the same sequence plus a frame inspection slider. These are generation and export checks; success does not establish geometric consistency.

The v0.2 private patch also keeps streaming pending pixels on CPU when `to_cpu` is enabled, matching PixelUMM `_decode_windows`. The four-step RTX 4090 smoke test passed after this fix. Visual scene consistency did not pass: returning to the same requested pose changes details.

## Dense route experiment

`viewer/route.html` separates route progress from horizontal heading, removes pitch, and clamps heading to ±60°. Run `deploy/route-probe.py` with a worker started using `STREETVIEW_FRAME_STRIDE=1`. It produces two forward segments plus an endpoint yaw sweep, replaces provisional decoder tails, and exports all frames. Only the endpoint has side views; fixed-position visual consistency still fails. This is a research probe, not full per-node panoramic coverage.

### Independent per-node turn branches

`deploy/branch-probe.py` samples three discrete stopping nodes. Left and right views each start from the same retained model history, using the native session rollback after each side branch. Dense forward transitions remain separate from the side branches. Open `viewer/branches.html` through the existing authenticated deployment after the run completes. This does not supply side views at every intermediate transition frame.

The guarded `deploy/patch_direct_session.py` patch adds direct structured-prompt history to the worker job store so native rollback works without the prompt-enhancement conversation path. `deploy/patch_upstream.py` applies it during installation. Authentication is unchanged.

Validation:

```bash
NOMAS_TEST_ROOT=/path/to/patched/Hy-Nomas python tests/test_direct_session.py
node tests/test_node_controls.cjs
python deploy/check-branch-probe.py
```

The first two checks validate queue history and controller behavior. The final check validates generated coverage, files and six successful restores; it intentionally does not mark visual geometry as passing. Returning to a cached center image is deterministic playback, not evidence of multiview consistency.

### Three real image anchors: continuous soft correction (experimental)

`deploy/three-anchor-probe.py` initializes the persistent model from real image A, generates a two-segment baseline, restores the same A state, then generates with B and C as successive soft latent references. It requires three input records in `/opt/streetview/anchor-inputs/anchors.json`; the first test uses the public StereoWalker campus-path sequence. See `anchor-experiment/EXPERIMENT.md` in the result bundle for attribution, input selection and limitations.

`deploy/patch_anchor_correction.py` adds optional `correction_image_id` and `correction_strength` request fields. Correction is applied inside flow denoising and before cache snapshots. Strength zero and absent correction images retain the original path. Native image initialization is still separate from continuation; there is no forced final-frame replacement. Manual image upload (`/v1/reference-images?caption_mode=manual`) accepts validated images without requiring an external captioning service; generation requires a structured manual prompt. Existing text generation and automatic captioning paths are retained. Authentication is unchanged.

`viewer/anchors.html` compares the two generated sequences synchronously and shows A, B and C separately as inputs. Success of execution does not establish scene geometry, and endpoint pixel metrics are not independent quality measures when the endpoint image is a condition. This inference heuristic has not been trained for multi-anchor consistency.

## Latest experiment and continuation
Read [the 2026-11-04 handoff](docs/HANDOFF-2026-11-04.md) before continuing. The current experiment uses three real image anchors with experimental soft latent correction and persistent continuation; it does not retrain weights. Results and exact input provenance are in `experiments/three-anchor/`. The paired viewer is `/streetview/anchors.html`. Geometry quality remains unverified; the user supplied preliminary positive visual feedback.
