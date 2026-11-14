"""Step 3 - SPHEREx-only SIA2 query + HTTP HEAD size probe on real products.

Adds the `collection` constraint so that Spitzer/NeoWISE records are excluded,
and measures the real download size of the returned FITS products via HEAD.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\03_sia2_spherex_only.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyvo
import requests
import astropy.units as u

SIA2_URL = "https://irsa.ipac.caltech.edu/SIA"
OUTDIR = Path(__file__).resolve().parents[1] / "processed"
OUTDIR.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "WISE0855": (133.795129, -7.245147),
    "Barnard": (269.454, 4.693),
}
SIZE_ARCMIN = 5.0
COLLECTIONS = ["spherex_dr1", "spherex_dr1_cube", "spherex_qr3"]

FIELDS = (
    "obs_title", "obs_description", "instrument", "facility", "obs_publisher_did",
    "obs_id", "target_name", "s_ra", "s_dec", "s_fov", "t_min", "t_max",
    "em_min", "em_max", "wcs_ulcorner", "wcs_lrcorner", "wcs_ulcorner2",
    "wcs_lrcorner2", "dataproduct_type", "calib_level", "data_rel",
    "obs_collection", "obs_creator_name", "access_format", "pixel_scale",
)

FN_RE = re.compile(
    r"(?P<prefix>level2|level3|level1)_(?P<visit>\d{4}W\d{2}_[0-9A-Z]{2})_"
    r"(?P<seq>\d{4})_(?P<det>[0-9]+D[0-9]+)_spx_(?P<pipe>[A-Za-z0-9_\-]+)\.fits$"
)


def head(url: str, timeout: int = 60) -> dict:
    rec = {"url": url}
    t0 = time.perf_counter()
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True,
                          headers={"User-Agent": "SPHERExExplorer/0.1"})
        rec["status_code"] = r.status_code
        rec["content_length"] = r.headers.get("Content-Length")
        rec["content_type"] = r.headers.get("Content-Type")
        rec["elapsed_s"] = round(time.perf_counter() - t0, 3)
        if r.headers.get("Content-Length"):
            rec["size_mb"] = round(int(r.headers["Content-Length"]) / 1e6, 2)
    except Exception as exc:  # noqa: BLE001
        rec["status_code"] = None
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["elapsed_s"] = round(time.perf_counter() - t0, 3)
    return rec


def main() -> int:
    svc = pyvo.dal.sia2.SIA2Service(SIA2_URL)
    out = {
        "sia2_url": SIA2_URL,
        "queried_at_utc": datetime.now(timezone.utc).isoformat(),
        "size_arcmin": SIZE_ARCMIN,
        "collections": COLLECTIONS,
        "targets": {},
    }

    for tname, (ra, dec) in TARGETS.items():
        print("=" * 78)
        print(f"TARGET {tname}: RA={ra} Dec={dec} r={SIZE_ARCMIN}'")
        rec: dict = {"ra_deg": ra, "dec_deg": dec}
        rows = []
        for coll in COLLECTIONS:
            try:
                res = svc.search(
                    pos=(ra * u.deg, dec * u.deg, SIZE_ARCMIN * u.arcmin),
                    collection=coll,
                    maxrec=2000,
                )
                got = list(res)
                print(f"  collection={coll:20s} -> {len(got)} records")
                for r in got:
                    d = {f: (None if getattr(r, f, None) is None else str(getattr(r, f)))
                         for f in FIELDS}
                    try:
                        d["access_url"] = r.access_url
                    except Exception:  # noqa: BLE001
                        d["access_url"] = None
                    rows.append(d)
            except Exception as exc:  # noqa: BLE001
                print(f"  collection={coll} ERROR {type(exc).__name__}: {exc}")
                rec.setdefault("errors", []).append(f"{coll}: {type(exc).__name__}: {exc}")

        # dedupe by access_url
        seen = set()
        uniq = []
        for d in rows:
            if d["access_url"] in seen:
                continue
            seen.add(d["access_url"])
            uniq.append(d)
        rec["n_records"] = len(uniq)
        rec["records"] = uniq

        visits, pipes, dets, collections = {}, {}, {}, {}
        for d in uniq:
            m = FN_RE.search(d["access_url"] or "")
            if not m:
                continue
            visits[m.group("visit")] = visits.get(m.group("visit"), 0) + 1
            pipes[m.group("pipe")] = pipes.get(m.group("pipe"), 0) + 1
            dets[m.group("det")] = dets.get(m.group("det"), 0) + 1
            c = d.get("obs_collection")
            collections[c] = collections.get(c, 0) + 1
        rec["parsed"] = {
            "visits": dict(sorted(visits.items())),
            "pipelines": dict(sorted(pipes.items())),
            "detectors": dict(sorted(dets.items())),
            "collections": collections,
        }
        print(f"  TOTAL unique = {rec['n_records']}")
        print(f"  visits ({len(visits)}): {sorted(visits)}")
        print(f"  collections: {collections}")

        # MJD distinct values
        mjds = sorted({d.get("t_min") for d in uniq if d.get("t_min")})
        rec["t_min_distinct"] = mjds
        print(f"  distinct t_min (MJD): {len(mjds)}")
        if mjds:
            print(f"    min={mjds[0]}  max={mjds[-1]}")
        # spectral ranges
        ems = sorted({(d.get("em_min"), d.get("em_max")) for d in uniq if d.get("em_min")})
        rec["em_distinct"] = ems
        print(f"  distinct (em_min,em_max): {len(ems)}")
        for a, b in ems:
            print(f"    {a} .. {b}")

        # HEAD probe on first 5 products to measure real sizes
        probes = []
        for d in uniq[:5]:
            h = head(d["access_url"])
            probes.append(h)
            print(f"  HEAD {h.get('status_code')} {h.get('size_mb')}MB  {d['access_url'].rsplit('/',1)[-1]}")
        rec["head_probes"] = probes

        out["targets"][tname] = rec

    (OUTDIR / "sia2_spherex_only.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSaved:", OUTDIR / "sia2_spherex_only.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
