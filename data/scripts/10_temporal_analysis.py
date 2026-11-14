"""Step 10 - R-01: is there a genuine temporal sequence for the queried position?

Uses the real SIA2 records saved in data/processed/sia2_spherex_only.json.

For every target it answers, with evidence:
  1. how many products the search cone returns;
  2. the distinct observation epochs (MJD / ISO);
  3. whether the epochs are re-observations of the SAME region+detector
     (a genuine temporal sequence) or just different bands/pointings;
  4. which products share detector AND sky overlap in >=2 epochs, and the
     temporal separation between them;
  5. the fields that allow ordering and compatibility checking.

Angular overlap is evaluated with the record's own s_ra/s_dec (centre of the
footprint) and s_fov (diameter), exactly as published by the SIA2 service.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\10_temporal_analysis.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.time import Time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "processed"
DATA = json.loads((OUT / "sia2_spherex_only.json").read_text(encoding="utf-8"))

FN_RE = re.compile(
    r"(?P<prefix>level2|level3|level1)_(?P<visit>\d{4}W\d{2}_[0-9A-Z]{2})_"
    r"(?P<seq>\d{4})_(?P<det>[0-9]+D[0-9]+)_spx_(?P<pipe>[A-Za-z0-9_\-]+)\.fits$"
)
ARCMIN = np.pi / 180.0


def sep_deg(ra1, dec1, ra2, dec2) -> float:
    """Great-circle separation in degrees (vectorised, numpy)."""
    ra1 = np.radians(np.asarray(ra1, dtype=float))
    dec1 = np.radians(np.asarray(dec1, dtype=float))
    ra2 = np.radians(np.asarray(ra2, dtype=float))
    dec2 = np.radians(np.asarray(dec2, dtype=float))
    d = (np.sin(dec1) * np.sin(dec2)
         + np.cos(dec1) * np.cos(dec2) * np.cos(ra1 - ra2))
    return np.degrees(np.arccos(np.clip(d, -1.0, 1.0)))


def parse_float(s):
    if s is None:
        return None
    try:
        return float(str(s).split()[0])
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sia2_url": DATA["sia2_url"],
        "query_size_arcmin": DATA["size_arcmin"],
        "targets": {},
    }

    for tname, t in DATA["targets"].items():
        ra_t, dec_t = t["ra_deg"], t["dec_deg"]
        recs = t["records"]
        print("=" * 100)
        print(f"TARGET {tname}: RA={ra_t} Dec={dec_t}   search radius={DATA['size_arcmin']}'")
        print("=" * 100)
        tgt = {"ra_deg": ra_t, "dec_deg": dec_t, "n_products": len(recs)}

        rows = []
        for r in recs:
            url = r.get("access_url") or ""
            m = FN_RE.search(url)
            d = dict(r)
            d["visit"] = m.group("visit") if m else None
            d["seq"] = m.group("seq") if m else None
            d["det_tag"] = m.group("det") if m else None
            d["module"] = m.group("det")[0] if m else None
            d["pipeline"] = m.group("pipe") if m else None
            d["s_ra_deg"] = parse_float(r.get("s_ra"))
            d["s_dec_deg"] = parse_float(r.get("s_dec"))
            d["s_fov_deg"] = parse_float(r.get("s_fov"))
            d["t_min"] = parse_float(r.get("t_min"))
            d["t_max"] = parse_float(r.get("t_max"))
            d["em_min_m"] = parse_float(r.get("em_min"))
            d["em_max_m"] = parse_float(r.get("em_max"))
            d["sep_deg"] = (float(sep_deg(ra_t, dec_t, d["s_ra_deg"], d["s_dec_deg"]))
                            if d["s_ra_deg"] is not None else None)
            rows.append(d)

        # ---------- 1. counts ----------
        print(f"\n[1] TOTAL products returned: {len(rows)}")
        by_coll = defaultdict(int)
        for d in rows:
            by_coll[d.get("obs_collection")] += 1
        print(f"    by collection: {dict(by_coll)}")
        print(f"    distinct visits in filenames: {len({d['visit'] for d in rows})}")
        print(f"    distinct detector tags      : {len({d['det_tag'] for d in rows})}")
        print(f"    distinct (visit,det) pairs  : {len({(d['visit'], d['det_tag']) for d in rows})}")
        # records whose filename does not follow the level2 pattern (e.g. the
        # single 'spherex_dr1_cube' product) are listed explicitly
        odd = [d for d in rows if not d["visit"]]
        for d in odd:
            print(f"    NON level2 filename record: collection={d.get('obs_collection')!r} "
                  f"dataproduct_type={d.get('dataproduct_type')!r} "
                  f"obs_id={d.get('obs_id')!r} t_min={d.get('t_min')} "
                  f"em=[{d.get('em_min_m')},{d.get('em_max_m')}]")
            print(f"        access_url = {d.get('access_url')}")
        tgt["non_level2_records"] = [
            {"access_url": d.get("access_url"), "collection": d.get("obs_collection"),
             "dataproduct_type": d.get("dataproduct_type"), "obs_id": d.get("obs_id"),
             "t_min": d.get("t_min"), "em_min_m": d.get("em_min_m"),
             "em_max_m": d.get("em_max_m"), "s_ra_deg": d.get("s_ra_deg"),
             "s_dec_deg": d.get("s_dec_deg"), "s_fov_deg": d.get("s_fov_deg"),
             "sep_deg": d.get("sep_deg")} for d in odd]

        # ---------- 2. epochs ----------
        mjds = sorted({d["t_min"] for d in rows if d["t_min"] is not None})
        print(f"\n[2] distinct t_min values (MJD): {len(mjds)}")
        # cluster MJDs into "nights" (within 0.5 day)
        clusters = []
        for m in mjds:
            if clusters and m - clusters[-1][-1] < 0.5:
                clusters[-1].append(m)
            else:
                clusters.append([m])
        print(f"    clustered into {len(clusters)} observing NIGHTS (<0.5 d apart):")
        epochs = []
        for c in clusters:
            lo, hi = min(c), max(c)
            t_lo = Time(lo, format="mjd").isot
            t_hi = Time(hi, format="mjd").isot
            visits = sorted({d["visit"] for d in rows
                             if d["t_min"] is not None and lo - 1e-9 <= d["t_min"] <= hi + 1e-9})
            dets = sorted({d["det_tag"] for d in rows
                           if d["t_min"] is not None and lo - 1e-9 <= d["t_min"] <= hi + 1e-9})
            n = sum(1 for d in rows if d["t_min"] is not None
                    and lo - 1e-9 <= d["t_min"] <= hi + 1e-9)
            epochs.append({"mjd_min": lo, "mjd_max": hi, "iso_min": t_lo, "iso_max": t_hi,
                           "n_products": n, "visits": visits, "detectors": dets})
            print(f"      MJD {lo:.6f} .. {hi:.6f}  |  {t_lo} .. {t_hi}  |  "
                  f"{n:>3d} products | visits={visits} | {len(dets)} detectors")
        tgt["observing_nights"] = epochs
        tgt["n_observing_nights"] = len(epochs)

        # ---------- 3. re-observation of same detector + overlapping region ----------
        print("\n[3] SAME-DETECTOR GROUPS (same band), and their spatial overlap with the target")
        by_det = defaultdict(list)
        for d in rows:
            if d["det_tag"]:
                by_det[d["det_tag"]].append(d)
        det_summary = []
        for det in sorted(by_det):
            g = by_det[det]
            sep = np.array([x["sep_deg"] for x in g if x["sep_deg"] is not None])
            # a record "covers" the target if the target lies within its footprint
            # radius: half of the footprint diagonal
            inside = []
            for x in g:
                if x["sep_deg"] is None or x["s_fov_deg"] is None:
                    continue
                radius = x["s_fov_deg"] / 2.0
                if x["sep_deg"] <= radius:
                    inside.append(x)
            visits_in = sorted({x["visit"] for x in inside})
            mjds_in = sorted({x["t_min"] for x in inside if x["t_min"] is not None})
            bands = sorted({(x["em_min_m"], x["em_max_m"]) for x in g})
            det_summary.append({
                "detector_tag": det, "n_products": len(g),
                "n_covering_target": len(inside),
                "sep_min_deg": float(sep.min()) if sep.size else None,
                "sep_max_deg": float(sep.max()) if sep.size else None,
                "visits_covering": visits_in,
                "n_epochs_covering": len(mjds_in),
                "band_range_m": bands,
            })
            print(f"    {det}: {len(g):>3d} products | covering target: {len(inside):>3d} | "
                  f"epochs(covering): {len(mjds_in)} | visits: {visits_in}")
        tgt["by_detector"] = det_summary

        # ---------- 4. genuine re-observation pairs ----------
        print("\n[4] DETECTOR GROUPS WITH >=2 DISTINCT EPOCHS COVERING THE TARGET")
        multi = [s for s in det_summary if s["n_epochs_covering"] >= 2]
        tgt["n_detectors_multi_epoch"] = len(multi)
        for s in multi:
            print(f"    detector {s['detector_tag']}: {s['n_epochs_covering']} epochs "
                  f"covering the target, visits {s['visits_covering']}")
            # per-epoch detail + separation
            g = [x for x in by_det[s["detector_tag"]]
                 if x["sep_deg"] is not None and x["s_fov_deg"] is not None
                 and x["sep_deg"] <= x["s_fov_deg"] / 2.0]
            seen = {}
            for x in g:
                seen.setdefault(x["t_min"], []).append(x)
            times = sorted(seen)
            for i in range(len(times) - 1):
                dt_days = times[i + 1] - times[i]
                print(f"        {Time(times[i], format='mjd').isot} -> "
                      f"{Time(times[i+1], format='mjd').isot}  "
                      f"dt = {dt_days:.4f} d")
            # record the epochs for this detector
            s["epoch_mjds"] = times
            s["epoch_isos"] = [Time(t, format="mjd").isot for t in times]
            s["min_dt_days"] = min((times[i + 1] - times[i]
                                    for i in range(len(times) - 1)), default=None)
            s["max_dt_days"] = max((times[i + 1] - times[i]
                                    for i in range(len(times) - 1)), default=None)

        # ---------- 5. ordering / compatibility fields ----------
        print("\n[5] FIELDS AVAILABLE FOR ORDERING AND COMPATIBILITY CHECKING")
        for f in ("t_min", "t_max", "em_min", "em_max", "obs_publisher_did", "obs_id",
                  "obs_collection", "dataproduct_type", "calib_level", "s_ra", "s_dec",
                  "s_fov", "obs_creator_name", "access_format"):
            vals = {str(r.get(f)) for r in rows}
            print(f"    {f:22s} present in {len(rows)} records, {len(vals)} distinct values")
        tgt["ordering_fields"] = ["t_min", "t_max", "em_min", "em_max",
                                  "obs_publisher_did", "obs_id", "obs_collection",
                                  "calib_level", "s_ra", "s_dec", "s_fov"]

        report["targets"][tname] = tgt

    (OUT / "temporal_analysis.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nSaved: {OUT / 'temporal_analysis.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
