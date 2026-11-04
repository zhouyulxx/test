# A → B → C continuous image correction experiment

Inputs: UVA Computer Vision Lab, StereoWalker, uva_test segment 3, sequence indices 363, 368, 373. Original filenames 005438.jpg, 005513.jpg, 005587.jpg. Source: https://huggingface.co/datasets/uva-cv-lab/StereoWalker . License: CC BY 4.0. Input metadata and download URLs are in anchors.json.

These are three real views along the same outdoor campus pedestrian path, approximately 4.854 m and 4.856 m apart. They are not Google Street View panoramas. People move between captures; image-wide pixel differences confound dynamic objects and geometry.

The model is initialized with image A through its native DCAE-V reference-image mechanism. The baseline then generates two moving segments without additional image conditions. The experiment rolls back both segments to the same A cache/RNG/decoder state, then regenerates with image B guiding the first segment and C guiding the next. Text and camera trajectory interfaces remain available.

The experimental correction acts on the last four latent time positions during each flow-denoising step. It softly pulls them toward the noise-level-matched encoded reference, with a temporal ramp and a configured strength. Corrected latents are included in the subsequent denoising/cache write, so the next segment inherits the corrected state. This is an untrained inference heuristic, not a learned geometric or pose-alignment mechanism. No output frame is replaced by B or C and no pixel crossfade is used.

Controls: same seed, requested path and starting model state. Two 49-frame moving segments per group; each group's middle reference point is B. The input observations span ten seconds, compressed into four seconds of generated movement; model translation is not metrically calibrated.

Acceptance layers must remain separate: (1) A/B/C image inputs reach the model, (2) execution and continuation succeed, (3) actual scene geometry and forward movement remain convincing. Pixel MAE, including an upper-half diagnostic, is not proof of the third layer. The corrected branch should not be declared better solely because its endpoint metric moves closer to an explicitly used reference.

Local main runtime lacks torch; numerical smoke checks are embedded in the remote GPU runner. Pure text/direct-session regression checks and source compilation are performed locally. Full experiment outputs remain on the running Pod until exported.

## Completed result

Session three-anchor-1793757746 succeeded. Five jobs and the two native rollbacks completed; all 196 exported frames exist. Actual queue payloads confirm A initialization and B/C correction IDs, with persistent cache and no reset for continuation. Input SHA256 hashes match the local source photos. The verifier passed. Endpoint RGB MAE changed from 30.847 to 28.792 at B and 36.796 to 32.682 at C. Initial A reconstruction MAE was 2.230. These metrics do not establish geometric quality.

The comparison viewer was installed at /streetview/anchors.html with synchronized playback, a frame slider and W/S controls. Browser visual verification remains blocked by Basic authentication (ERR_INVALID_AUTH_CREDENTIALS). Generated frames remain on the nonpersistent Pod and are NOT in this archive. This archive contains input photos, code and a transcribed result summary.
