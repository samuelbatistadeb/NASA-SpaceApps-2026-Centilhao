"""Step 7 - Download real SPHEREx DR1 cutouts and measure size/time.

Downloads the documented IRSA cutout for the WISE 0855 position at two sizes,
records provenance (URL, timestamp, bytes, sha256), and saves the files under
data/raw/<date>_<product>/ .

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\08_download_cutouts.py
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
RUN_TAG = "2026-11-14_spherex_dr1_l2b_2025W19_1B_0116_1D3"

JOBS = [
    ("size0.02", f"{BASE}?center={RA},{DEC}&size=0.02"),
    ("size0.05", f"{BASE}?center={RA},{DEC}&size=0.05"),
]


def download(url: str, dest: Path, attempts: int = 3) -> dict:
    last = {}
    for k in range(attempts):
        t0 = time.perf_counter()
        h = hashlib.sha256()
        n = 0
        try:
            with requests.get(url, stream=True, timeout=600, headers=UA) as r:
                last = {"status_code": r.status_code,
                        "content_type": r.headers.get("Content-Type")}
                if r.status_code != 200:
                    r.close()
                    last["error"] = f"HTTP {r.status_code}"
                    time.sleep(3)
                    continue
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
                "elapsed_s": round(dt, 3),
                "throughput_MBps": round(n / 1e6 / dt, 3) if dt else None,
                "status_code": 200, "attempts": k + 1,
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:  # noqa: BLE001
            last = {"error": f"{type(exc).__name__}: {exc}"}
            time.sleep(3)
    return {"url": url, "failed": True, **last}


def main() -> int:
    rep = {"run_tag": RUN_TAG, "base_url": BASE, "ra_deg": RA, "dec_deg": DEC,
           "downloads": []}
    for tag, url in JOBS:
        dest = RAW / RUN_TAG / f"cutout_wise0855_{tag}.fits"
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {tag} ...")
        rec = download(url, dest)
        print(json.dumps(rec, indent=2))
        rep["downloads"].append(rec)
    (OUT / "cutout_downloads.json").write_text(
        json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSaved:", OUT / "cutout_downloads.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
