#!/usr/bin/env python3
"""Exit 0 only when gateway AND GPU worker report ready."""
import json
import os
import sys
import urllib.request

port = os.environ.get("PORT", "18084")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as response:
        data = json.load(response)
    okay = data.get("worker_online") is True and data.get("available") is True
    print(json.dumps({"status": data.get("status"), "worker_status": data.get("worker_status"), "available": data.get("available")}))
    sys.exit(0 if okay else 1)
except Exception as e:
    print(f"Health check unavailable: {e}", file=sys.stderr)
    sys.exit(1)
