"""Step 2b - Summarize the SIA2 discovery JSON (compact, reproducible).

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\02_sia2_summary.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUTDIR = Path(__file__).resolve().parents[1] / "processed"
DATA = json.loads((OUTDIR / "sia2_discovery.json").read_text(encoding="utf-8"))

FIELDS_TO_SHOW = [
    "access_url", "obs_collection", "obs_title", "obs_id", "obs_publisher_did",
    "instrument", "facility", "dataproduct_type", "calib_level", "data_rel",
    "t_min", "t_max", "em_min", "em_max", "s_ra", "s_dec", "s_fov",
    "obs_creator_name", "target_name", "access_format", "pixel_scale",
    "wcs_ulcorner", "wcs_lrcorner", "wcs_ulcorner2", "wcs_lrcorner2",
    "o_ucd",
]

FN_RE = re.compile(
    r"level2_(?P<visit>\d{4}W\d{2}_[0-9A-Z]{2})_(?P<seq>\d{4})_(?P<det>[0-9]+D[0-9]+)"
    r"_spx_(?P<pipe>[A-Za-z0-9_\-]+)\.fits$"
)


def main() -> int:
    print("SIA2 URL:", DATA["sia2_url"])
    print("queried_at_utc:", DATA["queried_at_utc"])
    for tname, t in DATA["targets"].items():
        print("=" * 78)
        print(f"TARGET {tname}  RA={t['ra_deg']} Dec={t['dec_deg']} size={t.get('size_arcmin')} arcmin")
        if "error" in t:
            print("  ERROR:", t["error"])
            continue
        recs = t["records"]
        print(f"  n_records = {t['n_records']}")
        if not recs:
            continue
        # show the union of field values for a sample record
        print("  -- sample record fields (first record) --")
        for f in FIELDS_TO_SHOW:
            vals = {r.get(f) for r in recs}
            if vals == {None}:
                continue
            if len(vals) == 1:
                print(f"    {f:20s} = {vals.pop()}")
            else:
                print(f"    {f:20s} = {len(vals)} distinct values (sample: {sorted(str(v) for v in vals)[:3]})")
        # distinct counts
        print("  -- distinct counts --")
        for f in ("obs_collection", "dataproduct_type", "calib_level", "instrument",
                  "facility", "data_rel", "access_format", "obs_title", "obs_id",
                  "obs_creator_name", "target_name"):
            c = Counter(str(r.get(f)) for r in recs)
            if len(c) > 1 or list(c)[0] != "None":
                print(f"    {f:20s} : {dict(list(c.items())[:8])}")
        # parse filenames
        visits = Counter()
        pipes = Counter()
        dets = Counter()
        seqs = Counter()
        for r in recs:
            url = r.get("access_url") or ""
            m = FN_RE.search(url)
            if m:
                visits[m.group("visit")] += 1
                pipes[m.group("pipe")] += 1
                dets[m.group("det")] += 1
                seqs[m.group("seq")] += 1
        print("  -- parsed from filename --")
        print("    visits (epoch-like) :", dict(sorted(visits.items())))
        print("    pipeline tags       :", dict(sorted(pipes.items())))
        print("    detector tags       :", dict(sorted(dets.items())))
        print("    n distinct seq      :", len(seqs))
        # t_min/t_max
        tvals = sorted({(str(r.get('t_min')), str(r.get('t_max'))) for r in recs})
        print(f"  -- (t_min,t_max) distinct: {len(tvals)} --")
        for a, b in tvals[:20]:
            print(f"    t_min={a}  t_max={b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
