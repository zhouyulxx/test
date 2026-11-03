"""Produce deterministic, browser-compatible camera-trajectory JSON without model use.

The path's spatial units are requested camera units. Hy-Nomas may renormalize
translation; this is NOT a guarantee of physical meters in generated scenery.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def build_trajectory(*, seconds: float, fps: int = 24, speed: float = 0.0,
                     yaw_degrees: float = 0.0, pitch_degrees: float = 0.0, fov: float = 55.0) -> dict:
    if not (0.2 <= seconds <= 120 and 1 <= fps <= 120):
        raise ValueError("seconds must be 0.2..120 and FPS 1..120")
    count = max(2, int(round(seconds * fps)) + 1)
    # Hy-Nomas 4x temporal compression is first-frame aware: 4k+1 samples.
    count = ((count - 1 + 3) // 4) * 4 + 1
    path = []
    for i in range(count):
        t = i / fps
        yaw = math.radians(yaw_degrees * min(t / seconds, 1.0))
        pitch = math.radians(pitch_degrees * min(t / seconds, 1.0))
        # Three.js Y-up camera, looking in -Z at yaw=0.
        cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
        cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
        q = {"x": cy * sp, "y": sy * cp, "z": -sy * sp, "w": cy * cp}
        path.append({
            "t": round(t * 1000, 4),
            "position": {"x": 0.0, "y": 1.5, "z": round(-speed * t, 6)},
            "quaternion": q,
            "fov": fov,
        })
    return {
        "version": "1.0", "type": "camera-trajectory", "name": "streetview-auto",
        "sampleRate": fps, "durationMs": round((count - 1) / fps * 1000),
        "coordinateSystem": {"handedness": "right", "up": "+Y", "forward": "-Z", "unit": "requested-meter"},
        "frames": path, "keyEvents": [],
    }


def main():
    parser = argparse.ArgumentParser(description="Create a deterministic Hy-Nomas camera trajectory")
    parser.add_argument("--seconds", type=float, default=2)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--speed", type=float, default=0.0, help="Forward camera units per second")
    parser.add_argument("--yaw", type=float, default=180.0, help="Total yaw rotation in degrees")
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--output", default="camera_path.json")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(build_trajectory(seconds=args.seconds, fps=args.fps,
        speed=args.speed, yaw_degrees=args.yaw, pitch_degrees=args.pitch), indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
