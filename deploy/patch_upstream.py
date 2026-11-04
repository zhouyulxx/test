#!/usr/bin/env python3
"""Minimal idempotent patch against pinned Hy-Nomas upstream source.

Guarded string replacement fails closed on upstream layout changes.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def patch(root: Path) -> None:
    from patch_direct_session import patch_direct_sessions
    patch_direct_sessions(root)
    from patch_anchor_correction import patch as patch_anchor_correction
    patch_anchor_correction(root)
    worker = root / "scripts/inference/run_seg_ar_gpu_worker.sh"
    content = worker.read_text(encoding="utf-8")
    old = "++model.vae.deepgemm_fp8=true"
    new = "++model.vae.deepgemm_fp8=false"
    if old in content:
        assert content.count(old) == 1, "Unexpected upstream worker layout"
        worker.write_text(content.replace(old, new), encoding="utf-8")
        print("[patch] Worker: DeepGEMM disabled; low-memory CUDA SM89 CUTLASS FP8 retained")
    elif new in content:
        print("[patch] Worker: already patched")
    else:
        raise RuntimeError("Worker FP8 override not found; upstream changed, refusing blind patch")

    # PixelUMM _decode_windows returns CPU pixels whenever to_cpu is enabled.
    # Restore pending pixels to that same device on subsequent low-memory pushes.
    streaming = root / "hymm/models/vae/pixelumm_decoder/streaming.py"
    content = streaming.read_text(encoding="utf-8")
    old = 'if name == "pending" and self.to_cpu\n                and self.model._distributed_decode_mode == "window"'
    new = 'if name == "pending" and self.to_cpu'
    if old in content:
        assert content.count(old) == 1, "Unexpected streaming offload layout"
        streaming.write_text(content.replace(old, new), encoding="utf-8")
        print("[patch] Streaming pending pixels follow CPU output placement")
    elif new not in content:
        raise RuntimeError("Streaming pending device logic changed; refusing blind patch")

    server = root / "apps/seg_ar_web_server.py"
    content = server.read_text(encoding="utf-8")
    marker = "        timestamp = datetime.datetime.now().strftime(\"%Y%m%d_%H%M%S\")"
    inject = '''        # StreetView experiment: persist lossless decoded frames BEFORE H.264 encode.\n        # Opt-in only; failures are reported without corrupting the model session.\n        if os.environ.get("STREETVIEW_EXPORT_FRAMES", "0").lower() in ("1", "true", "yes"):\n            try:\n                from streetview.export import export_observations\n                export_path = export_observations(video_np, params, self.output_dir, fps, decoder_metadata=getattr(self.pipeline, "_last_pixelumm_streaming_metadata", None))\n                logger.info(f"StreetView observations: {export_path}")\n            except Exception:\n                logger.exception("StreetView observation export failed")\n\n'''
    if "StreetView observation export failed" in content:
        content = content.replace(
            "export_observations(video_np, params, self.output_dir, fps)",
            'export_observations(video_np, params, self.output_dir, fps, decoder_metadata=getattr(self.pipeline, "_last_pixelumm_streaming_metadata", None))',
        )
        server.write_text(content, encoding="utf-8")
        print("[patch] Output exporter: updated decoder alignment")
    elif marker in content:
        assert content.count(marker) == 1, "Unexpected _save_output timestamp count"
        # Verify insertion point is after the reference/carry trim, not before.
        trim = "if params.get(\"reference_image_id\") is not None:"
        assert trim in content[:content.index(marker)], "Expected reference trimming before export"
        server.write_text(content.replace(marker, inject + marker), encoding="utf-8")
        print("[patch] Output exporter: inserted prior to MP4 encode")
    else:
        raise RuntimeError("Web worker _save_output layout changed; refusing blind patch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="/Hy-Nomas")
    patch(Path(parser.parse_args().root))
