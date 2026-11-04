# Product goal and Street View integration handoff — 2026-11-04

This document supersedes earlier narrow three-anchor/short-distance plans where they conflict. Read it before continuing this project.

## Final product — explicit user requirement
Build a Chrome extension that augments Google Maps Street View with controllable, continuous forward travel through generated street scenes. The eventual goal is production-scale generation, storage and reuse of generated scenes for many viewers, not a one-off Colab video demo. Chrome extension is the client; production generation and storage belong in backend infrastructure. Exact extension integration and distribution remain unimplemented.

## Intended visual behavior
- Start from an actual street image A; later images B, C, ... progressively correct the continuing generation state.
- B is not a mandatory exact endpoint. Continue beyond it and beyond the final tested anchor.
- Do not substitute independent clips, simple screenshot playback, forced image replacement or pixel crossfades for continuous generation.
- Geometry may deform substantially. Perfect physical reconstruction is NOT the acceptance criterion.
- Different dates, seasons and lighting are allowed, including a future morning-to-night transition. Date differences must not reject an anchor.
- Desired acceptance: perceived forward travel, gradual response to successive anchors, usable viewer controls and no disruptive jumps. Smooth handling of large differences is a hypothesis to test, not an established model capability.
- Keep text prompting for debugging. Initial scope is straight streets, fixed forward view, no lane changes, turns or pitch changes. Later head yaw can be limited to +/-60 degrees.
- Main test must have at least 10 distinct image anchors. Three anchors over a short route are insufficient to reveal accumulated drift.
- Slow movement requires generating enough intermediate frames. Slower playback alone does not create spatial progression.

## Current verified route
Lynchburg downtown, Virginia; 12 distinct Street View panoramas, approximately 398.3 m total.
Adjacent gaps: 30.1–43.1 m. All 12 API images returned successfully in the user-run Colab test.
Forward-facing contact sheet inspected in conversation. No full generation run on this route has occurred.

Parameters:
- heading: 324 degrees
- pitch: 0
- horizontal FOV: 90 degrees
- image size: 640x360
- 70/90/110 degree previews compared at the same point. 90 chosen as initial composition baseline; 70 remains a generation ablation. No claim that 90 is empirically optimal for generation.
- Mixed dates 2023-11, 2025-07, 2025-09 intentionally retained.

Confirmed initial coordinates:
A: 37.41160054638993, -79.1393862038534
B: 37.41187948911811, -79.13965684087397
C: 37.41216824976726, -79.1399143846171

A–B 39.2 m, B–C 39.3 m; calculated bearings 322.4 and 324.7 degrees.
Later candidates were extrapolated from C at 35 m spacing along 324 degrees, then snapped to API panoramas and visually checked. This is NOT a general road-following or turn-planning algorithm.

## Important sampler bug and fix
Initial source=outdoor selected a Threshold 360 storefront panorama at P05, although it was only 2.9 m from the requested location and passed coordinate checks. Its view faced a shop entrance rather than down the street.
Changed metadata search to source=google (official Google collections). P05 was replaced with a forward street view at about 144.2 m:
37.41265005708104, -79.14034281871449.
All remaining contact-sheet views appeared along the street.
Coordinate proximity and HTTP success alone do NOT validate road-facing imagery. Do not infer provider from panorama-ID string format.

## Tools prepared
- notebooks/Lynchburg_12_anchors.ipynb: CPU Colab route preview, max 12 metadata and 12 image requests per run, no automatic retry. Secret name GOOGLE_MAPS_API_KEY. source=google. Stops on duplicates/geometry failures; date is informational only.
- notebooks/Lynchburg_export_inputs.ipynb: fixed confirmed panorama IDs, up to 12 requests, verifies original 640x360 image data, preserves original image bytes/attribution, exports P01–P12 and anchors.json with hashes. Only use where the intended export/use is authorized.
- Colab secret remains with the user. Never ask for the key in chat or commit it. No key exists in these notebooks.
- The user has supplied the route JSON and contact sheet; the independent original-image ZIP has NOT yet been received by the assistant.
- Local syntax checks passed. Preview was executed by the user; exporter has not been executed/verified end to end.
- No GPU was started during this Google integration work. Old Pod status is unknown; do not claim it is stopped.

## Google access and production rights
Project ID: street-view-try2. Street View Static API enabled, key created, project linked to billing; metadata OK and image HTTP 200 confirmed.
API restriction was Street View Static API only; application restriction was temporarily None. Production credentials must stay server-side and use appropriate restrictions.

API access/payment is NOT evidence of rights to bulk storage, redistribution or AI-derived scenes.
Official policy reviewed 2026-11-04:
https://developers.google.com/maps/documentation/streetview/policies
https://developers.google.com/maps/documentation/streetview/request-streetview

Google's policies restrict content prefetch/storage/caching; panorama IDs have an exception. The exact permissions for this product's generated outputs, retention, display, model inference and redistribution remain unresolved. Do not equate inference with training or claim either is permitted without checking the applicable agreement.
The user explicitly wants industrial/production generation and storage, so licensing is a core product requirement, not something to conceal by calling the project a temporary demo. Evaluate appropriate Google permission/licensing or imagery with rights covering the intended uses. Do not describe an export script as proof of permission. Keep source imagery out of the public repository. Preserve provider attribution and distinguish generated scenes from source imagery.

## Generation limitations and next steps
Existing Hy-Nomas modification is an untrained soft latent correction heuristic concentrated near segment tails. It does not establish geometric calibration or smooth day/night transitions.
The prior ~10 m three-anchor experiment's pixel-score improvement was against its conditioning images and is not proof of long-distance correction.
Camera trajectory units / generated seconds have not been calibrated to real meters.

Next:
1. Resolve/record the imagery use path appropriate for production generation and storage.
2. Obtain original inputs through that path; validate order, hashes and dimensions.
3. Extend the runner from A/B/C to >=10 anchors with persistent state, bounded memory, progress records and failure recovery.
4. Run matched seed/settings for initial-image-only vs successive-anchor correction. Avoid tying huge metric gaps to the former two-second segments.
5. If correction jumps, test earlier/longer gradual target influence; do not promise this works before testing.
6. Deliver a viewer with playback, pause, forward/backward navigation and anchor markers. Permit visual deformation; inspect continuity and anchor response throughout.
7. Build production generation jobs, durable generated-asset storage, versioned route manifests and serving/cache controls, with source/derived rights and attribution tracked separately.
8. Design the Chrome extension integration after validating the generation loop. The extension, backend orchestration and industrial storage are not yet built.

Refer also to docs/HANDOFF-2026-11-04.md for existing model patch details and docs/SHUTDOWN-STATUS.md for unresolved old Pod export/shutdown history.
