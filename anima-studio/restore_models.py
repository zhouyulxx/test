"""Reassemble Anima Turbo Release parts into ComfyUI model subfolders.

No Hugging Face connection required on the client. Only standard Python.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import sys

BUFFER_BYTES = 8 * 1024 * 1024

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True,
                        help="Directory containing manifest.json and downloaded .partNNN files")
    parser.add_argument("--comfy-root", type=Path, required=True,
                        help="Root directory of your ComfyUI installation")
    args = parser.parse_args()
    release = args.release_dir.resolve()
    root = args.comfy_root.resolve()
    manifest_path = release / "manifest.json"
    if not manifest_path.exists():
        sys.exit("Missing manifest.json: release may be incomplete.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]

    print(f"Verifying and restoring {len(files)} model files to {root}...")
    for rec in files:
        filename = rec["filename"]
        folder = rec["comfy_subfolder"]
        if Path(filename).name != filename or folder not in ("diffusion_models", "text_encoders", "vae"):
            sys.exit("Invalid manifest path; refusing to write files.")
        dest = root / "models" / folder / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            sys.exit(f"Refusing to overwrite existing model: {dest}. Move it aside first.")

        temp = dest.with_name(dest.name + ".partial")
        digest = hashlib.sha256()
        written = 0
        try:
            with temp.open("wb") as out:
                for part in rec["parts"]:
                    p = release / part["name"]
                    if p.parent != release or not p.is_file():
                        raise RuntimeError(f"Missing or invalid release part: {p}")
                    if p.stat().st_size != part["size"]:
                        raise RuntimeError(f"Wrong part size: {p}")
                    with p.open("rb") as inp:
                        while True:
                            block = inp.read(BUFFER_BYTES)
                            if not block:
                                break
                            out.write(block)
                            digest.update(block)
                            written += len(block)
            if written != rec["size"] or digest.hexdigest() != rec["sha256"]:
                raise RuntimeError(f"Checksum mismatch for {filename}; model was NOT installed")
            os.replace(temp, dest)
            print(f"OK: {dest} ({written:,} bytes)")
        except Exception:
            if temp.exists():
                temp.unlink()
            raise
    print("All weights restored and verified. Restart ComfyUI and select Anima Turbo.")

if __name__ == "__main__":
    main()
