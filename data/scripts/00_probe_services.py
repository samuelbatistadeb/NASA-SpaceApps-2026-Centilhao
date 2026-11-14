"""Step 1 - Empirical discovery of IRSA access paths for SPHEREx.

Probe candidate service endpoints and record HTTP status, headers and body
signature. Nothing is assumed: every URL probed here is either taken from a
link discovered on an IRSA page, or is a well-known IRSA service root that is
verified by the HTTP response recorded in the log.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\00_probe_services.py
"""

from __future__ import annotations

import json
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "processed" / "service_probe.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

USER_AGENT = "SPHERExExplorer-NASASpaceApps2026/0.1 (research; contact: team)"

CANDIDATES = [
    # --- IRSA mission / dataset landing pages (discovery entry points) ---
    ("mission_page", "https://irsa.ipac.caltech.edu/Missions/spherex.html"),
    ("spherex_mission_page", "https://irsa.ipac.caltech.edu/Missions/spherex"),
    ("spitzer_page", "https://irsa.ipac.caltech.edu/Missions/spitzer.html"),
    # --- IRSA TAP ---
    ("tap_root", "https://irsa.ipac.caltech.edu/TAP/"),
    ("tap_async", "https://irsa.ipac.caltech.edu/TAP/async"),
    ("tap_sync", "https://irsa.ipac.caltech.edu/TAP/sync"),
    # --- IRSA SIA / SIA2 style services ---
    ("sia1", "https://irsa.ipac.caltech.edu/SIA?"),
    ("sia2", "https://irsa.ipac.caltech.edu/SIA2?"),
    ("siap", "https://irsa.ipac.caltech.edu/Siap?"),
    # --- IRSA cutout ---
    ("cutout_legacy", "https://irsa.ipac.caltech.edu/cgi-bin/nph-cutout?"),
    ("cutout_new", "https://irsa.ipac.caltech.edu/cutout?"),
    # --- IRSA dataset / file browser roots ---
    ("irsa_root", "https://irsa.ipac.caltech.edu/"),
]


def probe(name: str, url: str, timeout: int = 45) -> dict:
    rec = {
        "name": name,
        "url": url,
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    t0 = time.perf_counter()
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        rec["status_code"] = resp.status_code
        rec["final_url"] = resp.url
        rec["content_type"] = resp.headers.get("Content-Type")
        rec["content_length"] = resp.headers.get("Content-Length")
        rec["bytes"] = len(resp.content)
        rec["elapsed_s"] = round(time.perf_counter() - t0, 3)
        body = resp.content[:4000].decode("utf-8", "replace")
        rec["body_head"] = body
    except Exception as exc:  # noqa: BLE001 - we want the raw failure recorded
        rec["status_code"] = None
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["elapsed_s"] = round(time.perf_counter() - t0, 3)
    return rec


def main() -> int:
    ssl_ctx = ssl.create_default_context()
    print(f"openssl default context ok: {ssl_ctx is not None}")
    results = []
    for name, url in CANDIDATES:
        rec = probe(name, url)
        results.append(rec)
        print(
            f"{name:24s} {str(rec.get('status_code')):>5s} "
            f"{rec.get('bytes', 0):>9d}B  {rec.get('elapsed_s')}s  {rec.get('final_url') or rec.get('url')}"
        )
        if rec.get("error"):
            print(f"    ERROR {rec['error']}")
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
