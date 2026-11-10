# Anima Turbo v1.1 — Creator Studio starter (prototype)

A lightweight, **human-reviewed** image-production starter for ComfyUI. This repository stores **scripts, workflow guidance, and manifests**, not copyrighted story drafts or raw model weights.

## Model choice

- Upstream: https://huggingface.co/circlestone-labs/Anima
- Variant: Anima Turbo v1.1
- Generation parameters: **8–12 steps, CFG 1** (developer recommendation)
- Three required files are fetched from the *official upstream*:
  1. split_files/diffusion_models/anima-turbo-v1.1.safetensors
  2. split_files/text_encoders/qwen_3_06b_base.safetensors
  3. split_files/vae/qwen_image_vae.safetensors
- ComfyUI model locations: models/diffusion_models, models/text_encoders, models/vae

The upstream *model* is under CircleStone Labs Non-Commercial License, not an unrestricted open-source license. The upstream model card explicitly permits selling **generated images**, but forbids monetizing a hosted inference/API service or embedding the weights in a monetized product without an additional license. Preserve upstream copyright and license notices. Independently review the underlying NVIDIA license and local law.

## Why no git clone of all model weights?

The upstream repository includes several Anima variants (~39 GB total). The selected version needs roughly 5–6 GB across 3 files. GitHub blocks regular files >100 MiB, and Free/Pro Git LFS has a 2 GB per-file limit. We therefore provide an **optional manually dispatched GitHub Actions mirror** that streams only the chosen 3 upstream files into <2 GiB GitHub Release assets. Running it creates a Release using your account's GitHub storage/bandwidth policies. It is intentionally NOT automatic.

**Privacy:** This experiment is on a public test repository. Don't commit story plots, customer data, secrets, or explicit adult material here. GitHub has rules against pornographic content. Use only legal adult fictional characters and check any publishing service's rules.

## One-time owner steps — if you choose to publish these scripts to the default branch

1. Review and merge the draft pull request for branch prototype/anima-turbo-studio. GitHub manual Actions workflows must exist on the default branch.
2. In your repository, open **Actions → Mirror Anima Turbo to a GitHub Release → Run workflow**. The job takes several GB from the official Hugging Face model repo and creates a Release named `anima-turbo-v1.1-mirror`.
3. Confirm the Release contains manifest.json, LICENSE-CircleStone.md, NOTICE.txt and numbered .partNNN assets. If it has no manifest.json the transfer did **not** finish.
4. On the Windows PC with ComfyUI installed, install GitHub CLI (gh), then:

    gh auth login
    gh release download anima-turbo-v1.1-mirror -R zhouyulxx/test -D model-parts
    python anima-studio/restore_models.py --release-dir model-parts --comfy-root "C:\\ComfyUI"

5. In ComfyUI, use the official Anima example workflow (the sample image in the model card can be dragged into ComfyUI) or the latest official Anima template and select Turbo v1.1. Start with CFG=1, 8–12 steps, one 768×1024 or 1024×1024 image.

The restore tool verifies full-file SHA-256 checksums from manifest.json before finalizing weights. It does not require a Hugging Face connection on your PC. You'll need enough local disk space for both the Release parts and restored model weights (preferably 15 GB free).

## Commercial validation: first experiment

Use one **original, clearly adult** character, one original scene, and three outfits/poses. Generate a small contact sheet of candidates. Manually select the best images, note GPU time and rework, and test whether anyone would pay for the artistic quality and story packaging before investing in a whole series.

Potential next modules: character bible, storyboard JSON, review queue, versioned prompts, scene continuity, export to comic panels. Keep personal story drafts in a private workspace.

## Scope and limitations

This starter prepares transfer and local installation; it does **not** itself perform an image generation or guarantee a working render. No model weights have been copied by merely adding this code. The GitHub Actions mirror requires the owner's deliberate manual run, and is subject to GitHub bandwidth/storage and upstream availability.

Official sources:
- https://huggingface.co/circlestone-labs/Anima
- https://huggingface.co/circlestone-labs/Anima/blob/main/LICENSE.md
- https://docs.comfy.org/tutorials/image/anima/anima
- https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
