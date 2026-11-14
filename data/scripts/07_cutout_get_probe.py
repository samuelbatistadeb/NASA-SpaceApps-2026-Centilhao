"""Step 6b - Probe the cutout endpoint with GET (HEAD returned 405).

Tests, for each `size` value:
  * GET with `Range: bytes=0-0` to learn Content-Range (total size) without
    downloading the whole file
  * GET with a small `size` and full download, measuring wall-clock time

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\07_cutout_get_probe.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "processed"
UA = {"User-Agent": "SPHERExExplorer-NASASpaceApps2026/0.1"}

BASE = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W19_1B/"
        "l2b-v27-2026-197/3/level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits")
RA, DEC = 133.795129, -7.245147
SIZE_VALS = ["0.1", "0.05", "0.02", "0.01"]


def range_probe(url: str) -> dict:
    t0 = time.perf_counter()
    try:
        r = requests.get(url, headers={**UA, "Range": "bytes=0-0"}, timeout=120,
                         allow_redirects=True, stream=True)
        cr = r.headers.get("Content-Range")
        cl = r.headers.get("Content-Length")
        total = None
        if cr and "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except ValueError:
                total = None
        rec = {
            "url": url, "status_code": r.status_code,
            "content_range": cr, "content_length": cl,
            "total_bytes": total,
            "total_mb": round(total / 1e6, 3) if total else None,
            "content_type": r.headers.get("Content-Type"),
            "elapsed_s": round(time.perf_counter() - t0, 3),
        }
        r.close()
        return rec
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "status_code": None, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    rep = {"tested_at_utc": datetime.now(timezone.utc).isoformat(), "base_url": BASE,
           "ra_deg": RA, "dec_deg": DEC, "probes": []}
    for sv in SIZE_VALS:
        url = f"{BASE}?center={RA},{DEC}&size={sv}"
        rec = range_probe(url)
        rep["probes"].append(rec)
        print(f"size={sv:6s} status={rec.get('status_code')} "
              f"CR={rec.get('content_range')} total={rec.get('total_mb')}MB "
              f"ct={rec.get('content_type')} ({rec.get('elapsed_s')}s)")
        if rec.get("error"):
            print("   ERROR:", rec["error"])

    # also probe the plain file with range for comparison
    rec = range_probe(BASE)
    print("PLAIN    ", rec.get("status_code"), rec.get("content_range"),
          rec.get("total_mb"), "MB")
    rep["plain_probe"] = rec

    (OUT / "cutout_get_probe.json").write_text(
        json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSaved:", OUT / "cutout_get_probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
