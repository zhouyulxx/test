"""Optional lossless frame and camera-command export for the Hy-Nomas web worker.

This exports observations, not reconstructed geometry. Camera positions are *requested*
poses rather than measured/calibrated poses; generated view consistency is unverified.
"""
from __future__ import annotations

import json
import fcntl
import os
import re
from pathlib import Path

import numpy as np
from PIL import Image


def _safe_id(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value))[:100] or "unnamed"


def _camera_source(value: object) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            obj = json.loads(value)
            return obj if isinstance(obj, dict) else None
        except (ValueError, TypeError):
            return None
    return None


def _pose_at_frame(camera: dict | None, index: int, fps: int, source_frames: int, emitted_frames: int) -> tuple[dict | None, str]:
    if camera is None:
        return None, "unavailable"
    frames = camera.get("frames")
    if not isinstance(frames, list) or not frames:
        return None, "unsupported_camera_format"
    # The web worker can replace a provisional previous tail during stable-prefix
    # decode and hide a reference prelude. In that situation there is no safe
    # single-frame identity mapping. Do not pretend there is one.
    if emitted_frames != source_frames:
        return None, "unverified_decoder_tail_or_hidden_frames"
    if len(frames) == source_frames:
        item = frames[min(index, len(frames) - 1)]
        return (item, "input_pose_exact_index") if isinstance(item, dict) else (None, "invalid_pose")
    # For camera trajectories with a different sampling frequency, use nearest
    # timestamp. This is only an approximate mapping, not recovered geometry.
    t_ms = index * 1000.0 / max(fps, 1)
    valid = [p for p in frames if isinstance(p, dict) and isinstance(p.get("t"), (int, float))]
    if not valid:
        return None, "unverified_camera_timing"
    chosen = min(valid, key=lambda p: abs(float(p["t"]) - t_ms))
    return chosen, "input_pose_nearest_timestamp"


def export_observations(video_np: np.ndarray, params: dict, output_dir: Path, fps: int, decoder_metadata: dict | None = None) -> Path:
    """Persist sampled PNG frames and a provenance-aware manifest.

    Called after the official worker constructs the final visible video_np and
    before its lossy H.264 encode. Outputs are under output_dir/streetview and
    served by the existing authenticated /outputs static mount.
    """
    frames = np.asarray(video_np)
    if frames.ndim != 4 or frames.shape[-1] != 3:
        raise ValueError(f"Expected [T,H,W,3] decoded RGB, got {frames.shape}")
    if frames.dtype != np.uint8:
        raise ValueError("Expected uint8 RGB frames after official preprocessing")
    interval = max(1, int(os.environ.get("STREETVIEW_FRAME_STRIDE", "4")))
    request_id = _safe_id(params.get("request_id", "unknown"))
    destination = Path(output_dir) / "streetview" / request_id
    destination.mkdir(parents=True, exist_ok=True)
    camera = _camera_source(params.get("camera_trajectory"))
    source_count = int(params.get("num_frames") or len(frames))
    # Pinned causal_ar.py asserts output length = requested frames + replaced tail.
    # Only align the new segment when that assertion is independently satisfied.
    carry = 0
    if isinstance(decoder_metadata, dict) and not any(params.get(k) for k in
            ('reference_image_id', 'hide_reference_carry', 'reference_carry_visible_frames')):
        candidate = int(decoder_metadata.get('replace_pixel_frames') or 0)
        if candidate >= 0 and len(frames) == source_count + candidate:
            carry = candidate
    observations = []
    for index in range(0, len(frames), interval):
        filename = f"frame_{index:05d}.png"
        Image.fromarray(frames[index], "RGB").save(destination / filename)
        if carry and index < carry:
            pose, alignment = None, "previous_segment_replacement_tail"
        else:
            pose, alignment = _pose_at_frame(camera, index - carry, fps, source_count, len(frames) - carry)
            if carry and pose is not None:
                alignment = "decoder_verified_new_segment_" + alignment
        observations.append({
            "frame_index": index,
            "time_s": round(index / fps, 6),
            "image": filename,
            "camera_pose_input": pose,
            "pose_alignment": alignment,
        })
    manifest = {
        "schema": "nomas-streetview-observations-v1",
        "request_id": request_id,
        "fps": int(fps),
        "source_frames": source_count,
        "visible_frames": int(len(frames)),
        "frame_stride": interval,
        "decoder_replacement_frames": carry,
        "decoder_metadata": decoder_metadata,
        "session_id": params.get("session_id"),
        "height": int(frames.shape[1]),
        "width": int(frames.shape[2]),
        "camera_coordinate_system": camera.get("coordinateSystem") if camera else None,
        "requested_camera_trajectory_type": camera.get("type") if camera else None,
        "camera_pose_semantics": "Input camera commands, NOT a calibrated or measured camera path",
        "note": "RGB frames are synthesized observations. This is NOT a coherent 3D scene, depth map, or complete 360-degree field. Decoder tail replacement may invalidate frame alignment.",
        "observations": observations,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # Single GPU deployment, with a lock to keep the catalog safe if expanded.
    root = destination.parent
    with (root / ".index.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        index_path = root / "index.json"
        try:
            previous = json.loads(index_path.read_text()).get("runs", [])
        except (OSError, ValueError, AttributeError):
            previous = []
        runs = [{"request_id": request_id, "frames": int(len(frames)),
                 "manifest": f"{request_id}/manifest.json"}]
        runs.extend(r for r in previous if r.get("request_id") != request_id)
        temporary = root / ".index.tmp"
        temporary.write_text(json.dumps({"runs": runs[:200]}, indent=2), encoding="utf-8")
        temporary.replace(index_path)
    return destination / "manifest.json"
