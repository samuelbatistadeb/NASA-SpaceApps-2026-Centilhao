"""Step 6 - Test the documented IRSA SPHEREx cutout service empirically.

The cutout mechanism is documented at
https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html  (see
data/processed/docs/cutout_tool.txt):

    <file_url>?center=<ra_deg>,<dec_deg>&size=<value>

This script measures, for a real DR1 product that covers WISE 0855:
  * HTTP status and Content-Length of the plain file vs the cutout
  * download wall-clock time
  * the resulting FITS structure (HDU list, shape, WCS) to determine what the
    `size` parameter means geometrically.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\06_cutout_test.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

BASE = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W19_1B/"
        "l2b-v27-2026-197/3/level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits")
RA, DEC = 133.795129, -7.245147

UA = {"User-Agent": "SPHERExExplorer-NASASpaceApps2026/0.1"}


def head(url: str) -> dict:
    t0 = time.perf_counter()
    try:
        r = requests.head(url, timeout=90, headers=UA, allow_redirects=True)
        cl = r.headers.get("Content-Length")
        return {
            "url": url, "status_code": r.status_code,
            "content_length": int(cl) if cl else None,
            "size_mb": round(int(cl) / 1e6, 3) if cl else None,
            "content_type": r.headers.get("Content-Type"),
            "elapsed_s": round(time.perf_counter() - t0, 3),
        }
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "status_code": None, "error": f"{type(exc).__name__}: {exc}"}


def download(url: str, dest: Path) -> dict:
    t0 = time.perf_counter()
    h = hashlib.sha256()
    n = 0
    with requests.get(url, stream=True, timeout=300, headers=UA) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    fh.write(chunk)
                    h.update(chunk)
                    n += len(chunk)
    dt = time.perf_counter() - t0
    return {
        "url": url, "path": str(dest), "bytes": n,
        "size_mb": round(n / 1e6, 3), "sha256": h.hexdigest(),
        "elapsed_s": round(dt, 3), "throughput_MBps": round(n / 1e6 / dt, 3) if dt else None,
    }


def describe_fits(path: Path) -> dict:
    d = {"path": str(path), "hdus": []}
    with fits.open(path, memmap=False) as hdul:
        d["n_hdu"] = len(hdul)
        for i, h in enumerate(hdul):
            info = {
                "index": i, "name": h.name,
                "type": type(h).__name__,
                "shape": list(h.shape) if h.shape else None,
                "size_bytes": int(h.size if hasattr(h, "size") else 0),
                "keys": list(h.header.keys()),
            }
            d["hdus"].append(info)
    return d


def main() -> int:
    rep = {"tested_at_utc": datetime.now(timezone.utc).isoformat(), "base_url": BASE,
           "ra_deg": RA, "dec_deg": DEC, "steps": []}

    print("### 1. HEAD of the plain DR1 product")
    h0 = head(BASE)
    print(json.dumps(h0, indent=2))
    rep["steps"].append({"step": "head_plain", "result": h0})

    print("\n### 2. HEAD of cutouts with different `size` values")
    size_vals = ["0.1", "0.05", "0.02", "0.01"]
    cuts = {}
    for sv in size_vals:
        url = f"{BASE}?center={RA},{DEC}&size={sv}"
        h = head(url)
        cuts[sv] = h
        print(f"  size={sv:6s} -> {h.get('status_code')}  "
              f"{h.get('size_mb')} MB  ({h.get('elapsed_s')}s)")
    rep["steps"].append({"step": "head_cutouts", "result": cuts})

    print("\n### 3. Download the smallest cutout and describe it")
    best = None
    for sv, h in cuts.items():
        if h.get("status_code") == 200 and h.get("content_length"):
            if best is None or h["content_length"] < cuts[best]["content_length"]:
                best = sv
    print("  smallest available cutout size parameter:", best)
    if best is None:
        print("  NO cutout available; will fall back to full download")
        best = None
    else:
        url = f"{BASE}?center={RA},{DEC}&size={best}"
        dest = RAW / f"2026-11-14_spherex_dr1_l2b_2025W19_1B" / f"cutout_wise0855_size{best}.fits"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dl = download(url, dest)
        print(json.dumps(dl, indent=2))
        rep["steps"].append({"step": "download_cutout", "result": dl})
        desc = describe_fits(dest)
        print(json.dumps(desc, indent=2)[:4000])
        rep["steps"].append({"step": "describe_cutout", "result": desc})

    (OUT / "cutout_test.json").write_text(
        json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSaved:", OUT / "cutout_test.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
