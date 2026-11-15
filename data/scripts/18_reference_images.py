"""Download reference images (DSS, 2MASS, WISE) of the 5 test targets.

Static fallback for the public site: when the IRSA search (SIA) or the backend
is down, the frontend shows these saved images instead of an error.

Source: IRSA Finder Chart API (NASA/IPAC). For each survey band the API reports
the real observation date (``obsdate``) of the plate/tile. Because some targets
move up to ~10"/yr, each image is centred on the target position PROPAGATED to
that date with the project's own proper-motion code (``app.services.astrometry``).
The date is re-checked at the propagated position (a target can cross a plate
boundary); if it changes, the position is propagated again once.

Usage (repository root, project venv):

    .venv/Scripts/python.exe data/scripts/18_reference_images.py            # all targets
    .venv/Scripts/python.exe data/scripts/18_reference_images.py --target barnard

Writes ``src/frontend/demo/<id>/ref/*.png`` and ``src/frontend/demo/reference.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "backend"))

from app.api.targets import TARGETS  # noqa: E402
from app.services.astrometry import ProperMotion, jyear_from_datetime, propagate_position  # noqa: E402

DEMO_DIR = ROOT / "src" / "frontend" / "demo"
API = "https://irsa.ipac.caltech.edu/applications/finderchart/servlet/api"
TARGET_IDS = {"wise0855": "WISE 0855", "barnard": "Estrela de Barnard", "epsindi": "ε Indi",
              "rwaur": "RW Aurigae", "rdra": "R Draconis"}

# (file stem, Finder Chart <band> label, survey query, band parameter, wavelength label)
BANDS = [
    ("dss1_red", "DSS1 Red", "DSS", "dss_bands=poss1_red", "luz visível (vermelho)"),
    ("dss2_red", "DSS2 Red", "DSS", "dss_bands=poss2ukstu_red", "luz visível (vermelho)"),
    ("2mass_j", "J", "2MASS", "twomass_bands=j", "1,23 µm"),
    ("2mass_h", "H", "2MASS", "twomass_bands=h", "1,66 µm"),
    ("2mass_k", "K", "2MASS", "twomass_bands=k", "2,16 µm"),
    ("wise_w1", "w1", "WISE", "wise_bands=1", "3,4 µm"),
    ("wise_w2", "w2", "WISE", "wise_bands=2", "4,6 µm"),
    ("wise_w3", "w3", "WISE", "wise_bands=3", "12 µm"),
    ("wise_w4", "w4", "WISE", "wise_bands=4", "22 µm"),
]
CREDITS = {
    "DSS": "Digitized Sky Survey (STScI), placas dos telescópios Schmidt de Palomar e UK Schmidt; via IRSA Finder Chart.",
    "2MASS": "2MASS: Universidade de Massachusetts e IPAC/Caltech (NASA/NSF); via IRSA Finder Chart.",
    "WISE": ("WISE/AllWISE: NASA/JPL-Caltech/UCLA; via IRSA Finder Chart. O AllWISE soma exposições "
             "de 2010–2011; a data é a informada pelo serviço para o ladrilho."),
}
UA = {"User-Agent": "spherex-explorer-demo/1.0"}


def get(url: str, timeout: float = 120, tries: int = 3) -> bytes:
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001 - network: retry, then re-raise
            last = exc
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"{url}: {last}")


def obsdates(ra: float, dec: float, fov: float) -> dict[tuple[str, str], str]:
    """Return {(survey, band label): 'YYYY-MM-DD'} reported by the Finder Chart."""
    q = urllib.parse.urlencode({"locstr": f"{ra:.6f} {dec:.6f}", "subsetsize": f"{fov}",
                                "survey": "DSS,2MASS,WISE"})
    root = ET.fromstring(get(f"{API}?{q}"))
    if root.get("status") != "ok":
        raise RuntimeError(f"Finder Chart status={root.get('status')}")
    out = {}
    for img in root.iter("image"):
        survey, band = img.findtext("surveyname"), img.findtext("band")
        if not survey or not band:
            continue
        # "WISE (AllWISE)" -> "WISE"
        out[(survey.split()[0].upper(), band)] = (img.findtext("obsdate") or "").strip()
    return out


def jyear(date: str) -> float:
    return jyear_from_datetime(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc))


def export(tid: str, fov: float) -> dict:
    t = next(x for x in TARGETS if x.name == TARGET_IDS[tid])
    motion = (ProperMotion(t.pm_ra_cosdec_masyr, t.pm_dec_masyr, t.ref_epoch_jyear)
              if t.pm_ra_cosdec_masyr is not None else None)
    out_dir = DEMO_DIR / tid / "ref"
    out_dir.mkdir(parents=True, exist_ok=True)
    base_dates = obsdates(t.ra, t.dec, fov)
    images = []
    for stem, band, survey, param, wl in BANDS:
        date = base_dates.get((survey, band))
        if not date:
            print(f"  {tid} {stem}: sem imagem no Finder Chart, pulando")
            continue
        ra, dec = t.ra, t.dec
        if motion:
            ra, dec = propagate_position(t.ra, t.dec, motion, jyear(date))
            # A posição propagada pode cair noutra placa/ladrilho: confere a data ali.
            date2 = obsdates(ra, dec, fov).get((survey, band))
            if date2 and date2 != date:
                date = date2
                ra, dec = propagate_position(t.ra, t.dec, motion, jyear(date))
        url = (f"{API}?mode=getImage&RA={ra:.6f}&DEC={dec:.6f}&subsetsize={fov}"
               f"&thumbnail_size=large&survey={survey.lower()}&{param}&type=jpgurl")
        data = get(url)
        if not data.startswith(b"\x89PNG"):
            print(f"  {tid} {stem}: resposta não é PNG, pulando")
            continue
        (out_dir / f"{stem}.png").write_bytes(data)
        images.append({
            "id": stem, "survey": survey, "band": band, "wavelength": wl, "obsdate": date,
            "file": f"demo/{tid}/ref/{stem}.png", "center_ra_deg": round(ra, 6),
            "center_dec_deg": round(dec, 6), "fov_arcmin": fov,
            "centered_on": "posição propagada para a data da imagem" if motion else "posição do catálogo",
            "source_url": url, "credit": CREDITS[survey],
        })
        print(f"  {tid} {stem}: {date}  RA {ra:.5f} Dec {dec:.5f}  {len(data)} B")
    return {"id": tid, "name": t.name, "ra": t.ra, "dec": t.dec,
            "ref_epoch_jyear": t.ref_epoch_jyear, "images": images}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--target", choices=sorted(TARGET_IDS))
    p.add_argument("--fov", type=float, default=3.0, help="arcmin")
    args = p.parse_args()
    ids = [args.target] if args.target else list(TARGET_IDS)

    manifest_path = DEMO_DIR / "reference.json"
    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {"targets": []}
    by_id = {x["id"]: x for x in manifest["targets"]}
    failed = []
    for tid in ids:
        print(f"== {tid}")
        try:
            by_id[tid] = export(tid, args.fov)
        except Exception as exc:  # noqa: BLE001
            print(f"  FALHOU: {exc}")
            failed.append(tid)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "service": API,
        "note": ("Imagens de referência de outros levantamentos (não são SPHEREx). Cada imagem é "
                 "centrada no alvo na data da própria imagem (obsdate informado pelo IRSA Finder Chart)."),
        "targets": [by_id[k] for k in TARGET_IDS if k in by_id],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print("falhas:", failed or "nenhuma")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
