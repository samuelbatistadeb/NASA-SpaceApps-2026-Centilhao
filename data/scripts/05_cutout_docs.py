"""Step 4b - Fetch the cutout tool doc, SIA doc, Gator endpoint and tutorials.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\05_cutout_docs.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "processed"
DOCS = OUT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "SPHERExExplorer-NASASpaceApps2026/0.1"}

PAGES = {
    "cutout_tool": "https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html",
    "ibe_sia": "https://irsa.ipac.caltech.edu/ibe/sia.html",
    "gator_spherex": "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-scan?mission=irsa&submit=Select&projshort=SPHEREX",
    "tutorial_cutouts": "https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/",
    "tutorial_hipscube": "https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/",
    "level2_dir": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/",
    "hips5_cube_dir": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026/",
    "voapi": "https://irsa.ipac.caltech.edu/voapi.html",
}


def main() -> int:
    rep = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(), "pages": {}}
    for name, url in PAGES.items():
        try:
            r = requests.get(url, timeout=90, headers=UA, allow_redirects=True)
            text = r.text
            (DOCS / f"{name}.html").write_text(text, encoding="utf-8", errors="replace")
            rec = {
                "url": url, "status_code": r.status_code, "final_url": r.url,
                "content_type": r.headers.get("Content-Type"), "bytes": len(r.content),
                "saved_to": f"data/processed/docs/{name}.html",
            }
        except Exception as exc:  # noqa: BLE001
            rec = {"url": url, "status_code": None, "error": f"{type(exc).__name__}: {exc}"}
        rep["pages"][name] = rec
        print(f"{name:20s} {rec.get('status_code')} {rec.get('bytes')}B  {url}")

    # Extract the interesting text of the cutout tool doc
    ct = DOCS / "cutout_tool.html"
    if ct.exists():
        html = ct.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        (DOCS / "cutout_tool.txt").write_text(text.strip(), encoding="utf-8")
        print("\n" + "=" * 78)
        print("CUTOUT TOOL DOC (text) - first 6000 chars")
        print("=" * 78)
        print(text.strip()[:6000])

    (OUT / "cutout_docs_report.json").write_text(
        json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSaved:", OUT / "cutout_docs_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
