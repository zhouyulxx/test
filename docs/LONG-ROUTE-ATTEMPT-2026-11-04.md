# Long-route attempt — 2026-11-04

## Outcome
No GPU inference ran. Existing Pod t537icpnnkye0w remains stopped.
Start failed because its RTX 4090 hardware is no longer available; automatic migration returned "There are no instances currently available".
New-deployment attempts for L4, PRO 6000 MIG 24GB and A100 PCIe resolved to "Instance not available"/"Deploy when available". Both subscription dialogs were cancelled. No scheduled auto-deploy subscription was created.
Balance observed: USD 25.00. No new running Pod was created by these attempts.
Do not claim a generated long-route viewer exists.

## Inputs
User uploaded lynchburg_12_inputs.zip. Extracted locally outside git to runtime-inputs/lynchburg.
All 12 images verified against anchors.json SHA256; all 640x360; P01-P12; 398.3 m span.
Input images and API keys are not published in this repository.
Mixed dates are accepted. P05 is the corrected street-facing Google panorama, not the earlier storefront.

## Code prepared
- deploy/long-route-probe.py: CPU dry-run default; --execute explicitly starts inference. 12 anchors in one persistent model session, eight 49-frame jobs per gap, two jobs after P12. 90 continuation jobs, around three minutes of output at 24fps.
- Explicit forward camera trajectories, FOV90. Requested translation is not calibrated physical model displacement.
- Existing correction heuristic only on the final job of each anchor interval, strength0.6. This is NOT a learned long-range anchor constraint or demonstrated gradual morph across an entire gap.
- Copies input data into run output, exports dense frames, job records, manifest and anchor markers.
- deploy/package-offline-viewer.py: refuses incomplete/empty runs, checks all required frames and input checksums, builds ZIP with index.html, data.js, all frames, original anchors, metadata, report and checksums.
- viewer/offline.html: file://-compatible relative images and JS data, no fetch/CDN/server; play/pause, keyboard step, speed, slider and anchor jumps. Model weights and credentials excluded.

## Checks completed
Python compilation and real 12-anchor CPU dry-run passed.
Offline packager tested with explicitly synthetic fixture: ZIP checksum round trip and missing-frame rejection passed.
No real-generated viewer, visual quality or GPU compatibility check has passed in this attempt.

## Continue
1. Obtain an available compatible GPU within the user's existing budget. Do not subscribe to unattended auto-start.
2. Image ghcr.io/zhouyulxx/test:streetview-v0.1; HTTP8081 only; no public internal18084. 150GB container disk. STREETVIEW_FRAME_STRIDE=1 (image default is4).
3. Inspect image build status: additions trigger Docker rebuild. The earlier run41761311091 succeeded before these additions. Do not assume current new build is ready.
4. Transfer user's ZIP via supported upload; do not publish Google source images to public GitHub. Extract and revalidate.
5. Run CPU plan first, check model readiness, then execute:
   python /opt/streetview/deploy/long-route-probe.py /path/to/lynchburg --execute
6. Inspect early forward motion and first correction before spending on all90 continuation jobs; monitor runtime and memory. No automatic restart/resume: a timed-out request may still be running.
7. After success:
   python /opt/streetview/deploy/package-offline-viewer.py /Hy-Nomas/outputs/seg_ar_demo/long-route-probes/SESSION /path/to/lynchburg-viewer.zip
8. Download, verify checksums, extract and test offline controls, then persist private complete ZIP for user. Only stop GPU after output is safely retrieved. Never replace missing generated output with source-image slideshow.
