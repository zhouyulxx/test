"""Stream only official Anima Turbo weights into <=1.5 GB GitHub Release parts.

Run in GitHub Actions with GH_TOKEN and GITHUB_REPOSITORY. This utility
does not run inference. Manifest is uploaded LAST and denotes completion.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import requests

MODEL_REPO = "circlestone-labs/Anima"
BASE_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main"
TAG = os.environ.get("RELEASE_TAG", "anima-turbo-v1.1-mirror")
GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]
PART_BYTES = 1_500_000_000  # below GitHub Release's 2 GiB asset limit
CHUNK_BYTES = 8 * 1024 * 1024

MODEL_FILES = [
    ("split_files/diffusion_models/anima-turbo-v1.1.safetensors", "diffusion_models"),
    ("split_files/text_encoders/qwen_3_06b_base.safetensors", "text_encoders"),
    ("split_files/vae/qwen_image_vae.safetensors", "vae"),
]

NOTICE = """The CircleStone Model is licensed by CircleStone Labs LLC under the CircleStone Non-Commercial License. Copyright CircleStone Labs LLC. IN NO EVENT SHALL CIRCLESTONE LABS LLC BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT OR TORT, ARISING FROM, OUT OF OR IN CONNECTION WITH USE OF THIS MODEL.

Source: https://huggingface.co/circlestone-labs/Anima
No changes to the model weights are made: the original files are split byte-for-byte for transport.
All downstream recipients are bound by the official upstream license; consult LICENSE-CircleStone.md.
Anima derives from NVIDIA Cosmos-Predict2 and is also subject to the applicable NVIDIA Open Model License Agreement.
Do not embed the model in a paid app or run paid inference services without a separate commercial license.
"""

def gh(*args):
    subprocess.run(["gh", *args, "--repo", GITHUB_REPO], check=True)

def upload_file(path):
    gh("release", "upload", TAG, str(path), "--clobber")

def download_text(session, path, name):
    resp = session.get(f"{BASE_URL}/{path}", timeout=(30, 180))
    resp.raise_for_status()
    target = Path(name)
    target.write_bytes(resp.content)
    upload_file(target)
    target.unlink()

def download_parts(session, source_path, target_folder):
    basename = source_path.rsplit("/", 1)[-1]
    url = f"{BASE_URL}/{source_path}"
    full_sha256 = hashlib.sha256()
    total = 0
    parts = []
    part_number = 0
    part_size = 0
    outfile = None
    part_path = None

    def close_and_upload():
        nonlocal outfile, part_path, part_size
        if outfile is None:
            return
        outfile.close()
        parts.append({"name": part_path.name, "size": part_size})
        upload_file(part_path)
        part_path.unlink()
        outfile = None
        part_path = None
        part_size = 0

    def open_part():
        nonlocal outfile, part_path, part_number
        part_number += 1
        part_path = Path(f"{basename}.part{part_number:03d}")
        outfile = part_path.open("wb")

    print(f"Downloading {source_path}", flush=True)
    with session.get(url, stream=True, timeout=(30, 300)) as resp:
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "text/html" in ctype:
            raise RuntimeError(f"Unexpected HTML instead of weights: {source_path}")
        for buf in resp.iter_content(chunk_size=CHUNK_BYTES):
            if not buf:
                continue
            full_sha256.update(buf)
            total += len(buf)
            view = memoryview(buf)
            cursor = 0
            while cursor < len(view):
                if outfile is None:
                    open_part()
                to_write = min(len(view) - cursor, PART_BYTES - part_size)
                outfile.write(view[cursor:cursor + to_write])
                cursor += to_write
                part_size += to_write
                if part_size == PART_BYTES:
                    close_and_upload()
    close_and_upload()
    if total < 100_000_000:
        raise RuntimeError(f"Suspiciously small model file: {source_path}, bytes={total}")
    print(f"Completed {basename}: {total} bytes, SHA-256 {full_sha256.hexdigest()}", flush=True)
    return {
        "source_path": source_path,
        "filename": basename,
        "comfy_subfolder": target_folder,
        "size": total,
        "sha256": full_sha256.hexdigest(),
        "parts": parts,
    }

def main():
    if not os.environ.get("GH_TOKEN"):
        sys.exit("Missing GH_TOKEN with contents:write permission")
    note = Path("NOTICE.txt")
    note.write_text(NOTICE, encoding="utf-8")
    check = subprocess.run(
        ["gh", "release", "view", TAG, "--repo", GITHUB_REPO],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    if check.returncode:
        gh("release", "create", TAG, "--title", TAG,
           "--notes", "Byte-for-byte split of official Anima Turbo v1.1 weights. "
                      "Observe CircleStone and NVIDIA license terms. No commercial inference service.")
    session = requests.Session()
    session.headers.update({"User-Agent": "AnimaStudioGitHubMirror/1.0"})
    upload_file(note)
    download_text(session, "LICENSE.md", "LICENSE-CircleStone.md")
    records = [download_parts(session, path, folder) for path, folder in MODEL_FILES]
    manifest = {
        "source": f"https://huggingface.co/{MODEL_REPO}",
        "release_tag": TAG,
        "files": records,
        "license": "CircleStone Labs Non-Commercial License (see LICENSE-CircleStone.md)",
    }
    manifest_path = Path("manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    upload_file(manifest_path)  # must be last: proof of successful complete transfer
    print("Release complete:", TAG)

if __name__ == "__main__":
    main()
