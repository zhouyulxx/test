# Long-route runtime investigation — 2026-11-05

## Goal and current experiment

Use 12 ordered forward-facing Street View inputs covering approximately 398.3 m.
Keep a single persistent generation session; apply subsequent anchors as soft
latent corrections, then continue beyond the final anchor. Dates may differ.
No turns, lane changes or head rotation are required for this experiment.

Current configuration: 4 continuation segments per gap, 49 requested frames per
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

Input ZIP verification and single-worker startup with dense export and recent
history were observed. The initialization job completed. The full long-route
render and visual quality evaluation are still pending at this checkpoint.
Archive roundtrip checks verified preservation of per-job metadata and all
checksum entries. JavaScript syntax and modified Python scripts were checked.

Do not infer anchor effectiveness from successful jobs or the presence of input
thumbnails. Inspect generated frames around corrections and the continuation
after P12 before recording a visual pass. Keep original imagery and private
runtime records out of the public repository.
