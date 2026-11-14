"""Step 4 - Fetch IRSA SPHEREx documentation pages and probe cutout services.

Everything fetched is saved under data/processed/docs/ so the evidence is
auditable offline. No URL is invented: cutout candidates are either derived
from links found in the fetched documentation, or are IRSA service roots that
are recorded with their real HTTP status.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\04_docs_and_cutout.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "processed"
DOCS = OUT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "SPHERExExplorer-NASASpaceApps2026/0.1"}

PAGES = {
    "overview_dr1": "https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html",
    "docs_index": "https://irsa.ipac.caltech.edu/data/SPHEREx/docs/",
    "spherex_app": "https://irsa.ipac.caltech.edu/applications/spherex",
    "mission_page": "https://irsa.ipac.caltech.edu/Missions/spherex.html",
}


def get(url: str, timeout: int = 60) -> dict:
    rec = {"url": url}
    t0 = time.perf_counter()
    try:
        r = requests.get(url, timeout=timeout, headers=UA, allow_redirects=True)
        rec["status_code"] = r.status_code
        rec["final_url"] = r.url
        rec["content_type"] = r.headers.get("Content-Type")
        rec["bytes"] = len(r.content)
        rec["elapsed_s"] = round(time.perf_counter() - t0, 3)
        rec["text"] = r.text
    except Exception as exc:  # noqa: BLE001
        rec["status_code"] = None
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def main() -> int:
    report = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(), "pages": {}, "cutout": {}}
    all_links: set[str] = set()

    for name, url in PAGES.items():
        rec = get(url)
        text = rec.pop("text", "") or ""
        (DOCS / f"{name}.html").write_text(text, encoding="utf-8", errors="replace")
        rec["saved_to"] = f"data/processed/docs/{name}.html"
        report["pages"][name] = rec
        print(f"{name:16s} {rec.get('status_code')} {rec.get('bytes')}B  {rec.get('final_url')}")
        for m in re.finditer(r'href=["\']([^"\']+)["\']', text):
            all_links.add(m.group(1))
        for m in re.finditer(r'https?://[^\s"\'<>]+', text):
            all_links.add(m.group(0))

    # --- interesting links found in the docs ---
    interesting = sorted(
        u for u in all_links
        if any(k in u.lower() for k in
               ("cutout", "sia", "sia2", "gator", "tap", "api", "docs", "cube", "level"))
        and not u.endswith((".css", ".js", ".png", ".gif", ".jpg", ".ico"))
    )
    (OUT / "discovered_links.json").write_text(
        json.dumps(sorted(all_links), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDiscovered {len(all_links)} links; {len(interesting)} interesting:")
    for u in interesting:
        print("  ", u)

    # --- cutout service candidates (IRSA roots + links found above) ---
    candidates = [
        "https://irsa.ipac.caltech.edu/cutout",
        "https://irsa.ipac.caltech.edu/cgi-bin/nph-cutout",
        "https://irsa.ipac.caltech.edu/ibe/data/spherex/",
    ]
    for u in interesting:
        if "cutout" in u.lower() and u.lower().startswith("http") and u not in candidates:
            candidates.append(u)

    print("\n--- cutout / data-root candidates ---")
    for url in candidates:
        rec = get(url)
        text = rec.pop("text", "") or ""
        rec["head"] = text[:800]
        report["cutout"][url] = rec
        print(f"  {rec.get('status_code')} {rec.get('bytes')}B {url}")
        if rec.get("status_code") == 200:
            print("      head:", " ".join(text[:300].split()))

    (OUT / "docs_and_cutout_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSaved:", OUT / "docs_and_cutout_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
