# Long-route runtime investigation — 2026-11-05

## Goal and current experiment

Use 12 ordered forward-facing Street View inputs covering approximately 398.3 m.
Keep a single persistent generation session; apply subsequent anchors as soft
latent corrections, then continue beyond the final anchor. Dates may differ.
No turns, lane changes or head rotation are required for this experiment.

Legacy configuration: 4 continuation segments per gap, 49 requested frames per
segment, 6 inference steps, 832×480 generated output, seed 43, correction strength
0.6 on the final segment of each gap, and 2 uncorrected segments after P12.
One initialization plus 46 continuation jobs is expected. Every decoded frame is
exported (`STREETVIEW_FRAME_STRIDE=1`). Camera distances are input commands, not
calibrated generated travel distance. This is not a coherent reconstructed 3D map.

## Runtime failures and corrections

- The upstream launcher supervises and automatically respawns GPU worker children.
  Terminating a child and starting another manually creates competing workers.
  A first attempt lost its session cache and showed a worker SIGKILL/restart.
  The interrupted result must not be described as a successful continuous route.
- Restart the managed pool as a whole; do not spawn a separate worker beside it.
  `deploy/restart-worker-pool.py` provides an explicit `--execute` path and otherwise
  only inspects the pool. Stop job submissions before using it. The gateway and
  existing authentication remain unchanged.
- The default `temporal_context` policy archives full KV history in CPU memory.
  This grows with route length even though the GPU context window is bounded.
  The long-route run uses `inference.sliding_window.sampling=recent`, keeping the
  existing 18 latent-frame history budget without the full CPU history archive.
  Recent-window mode does not support upstream generation rollback. Offline
  viewer backward scrubbing is unaffected because it reads saved frames.
- The runner now reads the actual per-job metadata and requires
  `continue_kv_cache=true` for every continuation. It fails on lost state instead
  of silently stitching independently initialized segments.

## Data transfer and delivery

- `deploy/route-input-transfer.py` adds a validated ZIP upload page behind the
  existing authenticated proxy. It verifies image hashes and rejects unsafe paths
  and oversized archives. Original input bytes were imported successfully.
- `deploy/watch-route-export.py` maintains a live progress page and a viewer
  checkpoint as frames appear. Completion packages a ZIP under that run's output
  directory, preventing a previous run's archive from being presented as current.
- The offline package includes all generated viewer frames, original anchors,
  input metadata, run report, per-job generation parameters, camera commands,
  cache continuity evidence and checksums. No server, external CDN or API key is
  required to open the extracted `index.html`.
- Playback prefetches a bounded window with four concurrent image loads. It has
  playback speed, frame scrubbing, keyboard controls and anchor jumps.

## Validation status

The legacy soft correction run was stopped after 1,127 exported frames. Cache
continuity was verified, and logs confirmed image correction was executed, but
visual inspection failed: P03 drifted toward the sidewalk and P06 rose above
street level. This is a failed partial baseline, not a successful full route.
Camera embeddings were present; do not treat successful parameter delivery as
proof of stable camera motion. The partial export preserves `status=failed` and
`visual_passed=false`, with an explicit warning in the viewer and README.

The next run retains the same 12 inputs and applies the new `progressive` policy:
all four segments toward each anchor receive guidance with maximum strength 0.85
and a gap-progress exponent of 1.5. Guidance spans the full latent segment,
leaves its first latent frame unchanged, and becomes stronger at lower noise.
Unlike the legacy rule, it is not divided by the denoising-step count. There is
no exact endpoint replacement. The prompt also explicitly keeps the camera at
street level with a level horizon. This combined change is experimental and is
not a controlled ablation isolating only one parameter.

Six anchor-correction tests passed in the model runtime, including retained
legacy behavior, a preserved first frame, stronger soft convergence and no
correction at pure noise. Three offline package tests passed: MP4/metadata/hash
roundtrip, strict failed-run rejection unless partial export is explicit, and
frame path traversal rejection. The source patch was checked for idempotence.

Actual generated frames were used to verify MP4 playback, speed changes, frame
stepping, spacebar control, scrubbing, anchor preview and the comparison page in
the browser. The full progressive run and its visual evaluation remain pending.

## Reproduction after a fresh image or runtime

The Docker build now applies `patch_progressive_anchor.py` through
`patch_upstream.py`. Existing running images require the progressive patch plus
a managed worker-pool restart to load new Python code. Updating files alone does
not replace code already imported by the model process. Keep gateway auth intact.

Before submitting jobs, use `restart-worker-pool.py --execute --history recent
--frame-stride 1` with submissions stopped, then verify readiness. The helper
updates upstream's `worker.pid` and preserves worker logs for subsequent restarts.
The runner's defaults now select progressive correction, 4 segments per gap and
maximum strength 0.85. To reproduce the legacy policy, explicitly pass
`--correction-policy legacy --strength 0.6 --segments-per-gap 4`.

Final packages contain `route.mp4` for smooth playback and `comparison.html` for
per-anchor review in addition to all viewer frames, original input images and
generation metadata. A failed run may be retained with `--allow-partial`; this
does not change its failed status or imply completion.

Do not infer anchor effectiveness from successful jobs or the presence of input
thumbnails. Inspect generated frames around corrections and the continuation
after P12 before recording a visual pass. Keep original imagery and private
runtime records out of the public repository.

## Progressive run visual checkpoint

At 29 of 47 completed jobs, 1,372 frames were exported through P08. Sampled
anchor frames at P04, P05, P06, P07 and P08 remain at street level and show
recognizable changes toward their respective input layouts. In particular, the
legacy rooftop failure at P06 was not present at the new P06 marker. However,
strong blur, ghosting and granular texture are visible. A sampled intermediate
frame between P05 and P06 contains a plausible street but buildings inconsistent
with the real inputs. These observations establish neither calibrated travel
distance nor geometric reconstruction. Endpoint similarity alone is not proof
of continuous camera control between anchors.

The completed continuation metadata checked so far retain KV-cache continuity.
The full route, final uncorrected continuation and final export are still pending.
Do not label this checkpoint as a visual pass or a completed deliverable.
