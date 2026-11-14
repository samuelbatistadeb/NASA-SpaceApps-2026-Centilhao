"""Step 2 - Discover the IRSA SIA2 service capabilities with pyvo.

Confirmed base URL (from data/scripts/00_probe_services.py, HTTP 200, service
description "Caltech/IPAC-IRSA IVOA Simple Image Access v2 Service"):
    https://irsa.ipac.caltech.edu/SIA

This script:
  1. Fetches the service description / registry via pyvo `describe()`.
  2. Runs SIA2 searches for the WISE 0855 and Barnard positions.
  3. Saves the raw VOTable + a JSON summary so the discovery is reproducible.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\01_sia2_discover.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyvo
from astropy.coordinates import SkyCoord
import astropy.units as u

SIA2_URL = "https://irsa.ipac.caltech.edu/SIA"
OUTDIR = Path(__file__).resolve().parents[1] / "processed"
OUTDIR.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "WISE0855": (133.795129, -7.245147),
    "Barnard": (269.454, 4.693),
}
SIZE_ARCMIN = 5.0

FIELDS = (
    "obs_title", "obs_description", "instrument", "facility",
    "obs_publisher_did", "obs_id", "target_name", "s_ra", "s_dec",
    "s_fov", "t_min", "t_max", "em_min", "em_max",
    "wcs_ulcorner", "wcs_lrcorner", "wcs_ulcorner2", "wcs_lrcorner2",
    "dataproduct_type", "calib_level", "data_rel", "obs_collection",
    "obs_creator_name", "o_ucd", "access_format", "pixel_scale",
)


def main() -> int:
    summary: dict = {
        "sia2_url": SIA2_URL,
        "queried_at_utc": datetime.now(timezone.utc).isoformat(),
        "pyvo_version": pyvo.__version__,
        "size_arcmin": SIZE_ARCMIN,
        "targets": {},
    }

    svc = pyvo.dal.sia2.SIA2Service(SIA2_URL)

    # ---- service description / registry ----
    try:
        desc = svc.describe()
        raw = desc.raw if hasattr(desc, "raw") else bytes(str(desc), "utf-8")
        (OUTDIR / "sia2_service_description.xml").write_bytes(raw)
        print("--- service description saved ({} bytes) ---".format(len(raw)))
        print(str(desc)[:3000])
        summary["service_description_path"] = "data/processed/sia2_service_description.xml"
        # list the capabilities (collections) if the registry parsed
        try:
            caps = getattr(desc, "_capabilities", None)
            summary["capabilities"] = str(caps)[:4000]
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        print("describe() failed:", type(exc).__name__, exc)
        summary["describe_error"] = f"{type(exc).__name__}: {exc}"

    for name, (ra, dec) in TARGETS.items():
        print("=" * 70)
        print(f"TARGET {name}: RA={ra} Dec={dec}  r={SIZE_ARCMIN} arcmin")
        rec = {"ra_deg": ra, "dec_deg": dec, "size_arcmin": SIZE_ARCMIN}
        try:
            results = svc.search(
                pos=(ra * u.deg, dec * u.deg, SIZE_ARCMIN * u.arcmin),
                maxrec=500,
            )
            rows = list(results)
            rec["n_records"] = len(rows)
            rec["records"] = []
            for r in rows:
                d = {}
                try:
                    d["access_url"] = r.access_url
                except Exception:  # noqa: BLE001
                    d["access_url"] = None
                for field in FIELDS:
                    try:
                        v = getattr(r, field)
                        d[field] = None if v is None else str(v)
                    except Exception:  # noqa: BLE001
                        d[field] = None
                rec["records"].append(d)
                print("  ", d.get("access_url"), "|", d.get("obs_collection"))
            # persist raw votable for audit
            try:
                raw = results.raw if hasattr(results, "raw") else None
                if raw:
                    (OUTDIR / f"sia2_{name}.votable.xml").write_bytes(raw)
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
            print("  SEARCH ERROR:", rec["error"])
        summary["targets"][name] = rec

    (OUTDIR / "sia2_discovery.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\nSaved:", OUTDIR / "sia2_discovery.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
