"""Build a FIXED-SKY timeline of each test target: decades of surveys + SPHEREx.

Goal: let anyone SEE a star move over time. Every frame of a target shows the
same patch of sky (same centre, same field of view, north up, east left), so a
high-proper-motion star crosses the frame while background stars stay put:

* DSS1/DSS2 plates, 2MASS and WISE images from the IRSA Finder Chart API, each
  with the real observation date (``obsdate``) reported by the service;
* SPHEREx exposures (D1-D6) re-cut by IBE at the same fixed centre and FOV and
  resampled with the backend's own common-frame code. The exposures come from
  the saved demo package (``demo/<id>/observations.json``: real IRSA products),
  so the SIA search service is NOT needed - only IBE cutouts.

For each frame the target's PREDICTED position (proper motion propagated to the
frame date with ``app.services.astrometry``) is stored as a fraction of the
image, so the site can draw the expected track. Nothing is fitted or measured.

Usage (repository root, project venv):

    .venv/Scripts/python.exe data/scripts/19_motion_timeline.py                 # all targets
    .venv/Scripts/python.exe data/scripts/19_motion_timeline.py --target barnard

Writes ``src/frontend/demo/<id>/motion/*.png``, ``demo/<id>/motion.json`` and the
index ``src/frontend/demo/motion.json``.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "backend"))

from app.api import observations as api  # noqa: E402
from app.api.targets import TARGETS  # noqa: E402
from app.services import fits_processor  # noqa: E402
from app.services.astrometry import ProperMotion, jyear_from_datetime, propagate_position  # noqa: E402
from app.services.common_frame import SPHEREX_PIXEL_SCALE_ARCSEC, project_to_frame  # noqa: E402
from app.services.cutout_service import IBE_SIZE_FACTOR  # noqa: E402

DEMO = ROOT / "src" / "frontend" / "demo"
API = "https://irsa.ipac.caltech.edu/applications/finderchart/servlet/api"
TARGET_IDS = {"barnard": "Estrela de Barnard", "epsindi": "ε Indi", "wise0855": "WISE 0855",
              "rwaur": "RW Aurigae", "rdra": "R Draconis"}
UA = {"User-Agent": "spherex-explorer-demo/1.0"}

# (id, Finder Chart survey name, band label, query param, label shown, wavelength)
SURVEY_BANDS = [
    ("dss1_red", "DSS", "DSS1 Red", "survey=dss&dss_bands=poss1_red", "DSS1 vermelho", "luz visível"),
    ("dss2_red", "DSS", "DSS2 Red", "survey=dss&dss_bands=poss2ukstu_red", "DSS2 vermelho", "luz visível"),
    ("dss2_ir", "DSS", "DSS2 IR", "survey=dss&dss_bands=poss2ukstu_ir", "DSS2 infravermelho", "~0,85 µm"),
    ("2mass_k", "2MASS", "K", "survey=2mass&twomass_bands=k", "2MASS K", "2,16 µm"),
    ("wise_w1", "WISE", "w1", "survey=wise&wise_bands=1", "WISE W1", "3,4 µm"),
    ("wise_w2", "WISE", "w2", "survey=wise&wise_bands=2", "WISE W2", "4,6 µm"),
]
CREDITS = {
    "DSS": "Digitized Sky Survey (STScI; placas Palomar e UK Schmidt), via IRSA Finder Chart",
    "2MASS": "2MASS (UMass e IPAC/Caltech; NASA/NSF), via IRSA Finder Chart",
    "WISE": "WISE/AllWISE (NASA/JPL-Caltech/UCLA), via IRSA Finder Chart; soma de exposições de 2010–2011",
    "SPHEREx": "SPHEREx (NASA/JPL-Caltech), dados IRSA/IPAC; recorte IBE reamostrado norte para cima",
}
TWOMASS_MAX_ARCMIN = 12.0   # o Finder Chart devolve 2MASS todo preto acima disso (testado 15–30′)
FOV_MAX_ARCMIN = 20.0
SPHEREX_PER_DETECTOR = 3     # mais antiga, do meio e mais recente de cada detector
NOW_JYEAR = round(jyear_from_datetime(datetime.now(timezone.utc)), 2)  # fim do trajeto: hoje


def get(url: str, timeout: float = 150, tries: int = 3) -> bytes:
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"{url}: {last}")


def finder_dates(ra: float, dec: float, fov: float) -> dict[tuple[str, str], str]:
    q = urllib.parse.urlencode({"locstr": f"{ra:.6f} {dec:.6f}", "subsetsize": f"{fov:.2f}",
                                "survey": "DSS,2MASS,WISE"})
    root = ET.fromstring(get(f"{API}?{q}"))
    out = {}
    for img in root.iter("image"):
        s, b = img.findtext("surveyname"), img.findtext("band")
        if s and b:
            out[(s.split()[0].upper(), b)] = (img.findtext("obsdate") or "").strip()
    return out


def jy(date: str) -> float:
    return jyear_from_datetime(datetime.strptime(date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc))


def sep_arcmin(a: tuple[float, float], b: tuple[float, float]) -> float:
    d1, d2 = math.radians(a[1]), math.radians(b[1])
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(math.radians(a[0] - b[0]))
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 60


def frac_xy(pos: tuple[float, float], center: tuple[float, float], fov: float) -> list[float]:
    """Position as a fraction of a north-up, east-left image (gnomonic)."""
    ra, dec = map(math.radians, pos)
    ra0, dec0 = map(math.radians, center)
    cosc = math.sin(dec0) * math.sin(dec) + math.cos(dec0) * math.cos(dec) * math.cos(ra - ra0)
    xi = math.cos(dec) * math.sin(ra - ra0) / cosc          # east, rad
    eta = (math.cos(dec0) * math.sin(dec) - math.sin(dec0) * math.cos(dec) * math.cos(ra - ra0)) / cosc
    side = math.radians(fov / 60)
    return [round(0.5 - xi / side, 4), round(0.5 - eta / side, 4)]


def looks_empty(png: bytes) -> bool:
    a = np.asarray(Image.open(io.BytesIO(png)).convert("L"), dtype=float)
    return a.std() < 2.0 or a.mean() < 2.0


def build(tid: str, max_spherex: int) -> dict:
    t = next(x for x in TARGETS if x.name == TARGET_IDS[tid])
    motion = (ProperMotion(t.pm_ra_cosdec_masyr, t.pm_dec_masyr, t.ref_epoch_jyear)
              if t.pm_ra_cosdec_masyr is not None else None)
    pos_at = (lambda y: propagate_position(t.ra, t.dec, motion, y)) if motion else (lambda y: (t.ra, t.dec))

    dates = finder_dates(t.ra, t.dec, 3)
    epochs = {sid: dates.get((s, b)) for sid, s, b, *_ in SURVEY_BANDS}
    epochs = {k: v for k, v in epochs.items() if v}
    # FOV: o trajeto inteiro (da imagem mais antiga até hoje) + margem de 3′.
    oldest = min(jy(d) for d in epochs.values()) if epochs else NOW_JYEAR
    extent = sep_arcmin(pos_at(oldest), pos_at(NOW_JYEAR))
    fov = round(min(FOV_MAX_ARCMIN, max(3.0, math.ceil(extent + 3))), 1)
    if extent + 2 > FOV_MAX_ARCMIN:  # trajeto não cabe: descarta as épocas mais antigas
        keep = {k: v for k, v in epochs.items() if sep_arcmin(pos_at(jy(v)), pos_at(NOW_JYEAR)) + 2 <= FOV_MAX_ARCMIN}
        print(f"  trajeto de {extent:.1f}′ não cabe em {FOV_MAX_ARCMIN}′; épocas descartadas: {sorted(set(epochs) - set(keep))}")
        epochs = keep
        oldest = min(jy(d) for d in epochs.values())
        extent = sep_arcmin(pos_at(oldest), pos_at(NOW_JYEAR))
    p0, p1 = pos_at(oldest), pos_at(NOW_JYEAR)
    center = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)  # trajetos curtos: média basta
    print(f"  trajeto {extent:.2f}′ ({oldest:.1f}–{NOW_JYEAR}) · FOV {fov}′ · centro {center[0]:.5f} {center[1]:.5f}")

    out_dir = DEMO / tid / "motion"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()
    frames, skipped = [], []

    # Datas reconferidas no centro fixo (uma placa pode mudar de um ponto para outro).
    dates_c = finder_dates(*center, fov)
    for sid, survey, band, param, label, wl in SURVEY_BANDS:
        date = dates_c.get((survey, band)) or epochs.get(sid)
        if sid not in epochs or not date:
            continue
        if survey == "2MASS" and fov > TWOMASS_MAX_ARCMIN:
            skipped.append(f"{label}: FOV {fov}′ acima do limite do serviço ({TWOMASS_MAX_ARCMIN}′)")
            continue
        url = (f"{API}?mode=getImage&RA={center[0]:.6f}&DEC={center[1]:.6f}&subsetsize={fov}"
               f"&thumbnail_size=large&{param}&type=jpgurl")
        try:
            png = get(url)
        except RuntimeError as exc:
            skipped.append(f"{label}: {exc}")
            continue
        if not png.startswith(b"\x89PNG") or looks_empty(png):
            skipped.append(f"{label}: imagem vazia ou inválida")
            continue
        (out_dir / f"{sid}.png").write_bytes(png)
        y = jy(date)
        frames.append({"id": sid, "kind": "survey", "survey": survey, "label": label, "wavelength": wl,
                       "date": date, "jyear": round(y, 3), "file": f"demo/{tid}/motion/{sid}.png",
                       "target_xy": frac_xy(pos_at(y), center, fov), "credit": CREDITS[survey],
                       "source_url": url})
        print(f"  {label:20s} {date}  ok")

    # SPHEREx: exposições do pacote salvo, recortadas de novo no centro FIXO.
    obs_path = DEMO / tid / "observations.json"
    if obs_path.exists():
        obs = json.loads(obs_path.read_text("utf-8"))["observations"]
        client = api.get_irsa_client()
        by_det: dict[str, list] = {}
        for o in obs:
            if o.get("detector") and o.get("metadata", {}).get("original_file_url"):
                by_det.setdefault(o["detector"], []).append(o)
        for det in sorted(by_det):
            lst = sorted(by_det[det], key=lambda o: o["observed_at"])
            n = min(max_spherex, len(lst))
            idx = sorted({round(i * (len(lst) - 1) / max(1, n - 1)) for i in range(n)})
            for o in (lst[i] for i in idx):
                md = o["metadata"]
                try:
                    content = client.fetch_ibe_cutout(md["original_file_url"], center[0], center[1],
                                                      fov * 60 * IBE_SIZE_FACTOR / 3600.0)
                    img = fits_processor.load_image(content)
                    wcs = fits_processor.extract_wcs(img.header)
                    frame = project_to_frame(img.data, wcs, center[0], center[1], fov,
                                             scale_arcsec=SPHEREX_PIXEL_SCALE_ARCSEC)
                    if frame.coverage_fraction < 0.5:
                        skipped.append(f"SPHEREx {det} {o['observed_at'][:10]}: só {frame.coverage_fraction:.0%} do campo no detector")
                        continue
                    png = fits_processor.render_frame_png(frame.data, frame.outside)
                except Exception as exc:  # noqa: BLE001 - IBE indisponível ou produto sem o ponto
                    skipped.append(f"SPHEREx {det} {o['observed_at'][:10]}: {exc}")
                    continue
                name = f"spherex_{det}_{o['id']}.png"
                (out_dir / name).write_bytes(png)
                when = datetime.fromisoformat(o["observed_at"].replace("Z", "+00:00"))
                y = jyear_from_datetime(when)
                wmin, wmax = md.get("wavelength_min_nm"), md.get("wavelength_max_nm")
                frames.append({
                    "id": f"spherex_{det}_{o['id']}", "kind": "spherex", "survey": "SPHEREx", "detector": det,
                    "label": f"SPHEREx {det}",
                    "wavelength": (f"{wmin / 1000:.2f}–{wmax / 1000:.2f} µm".replace(".", ",") if wmin and wmax else ""),
                    "date": o["observed_at"][:10], "jyear": round(y, 3), "file": f"demo/{tid}/motion/{name}",
                    "target_xy": frac_xy(pos_at(y), center, fov), "credit": CREDITS["SPHEREx"],
                    "product_id": md.get("product_id"),
                    "coverage_fraction": round(frame.coverage_fraction, 3),
                })
                print(f"  SPHEREx {det} {o['observed_at'][:10]}  ok ({frame.coverage_fraction:.0%})")

    frames.sort(key=lambda f: f["jyear"])
    pm_total = motion.total_masyr / 1000 if motion else 0.0
    data = {
        "id": tid, "name": t.name, "center_ra_deg": round(center[0], 6), "center_dec_deg": round(center[1], 6),
        "fov_arcmin": fov, "pm_total_arcsec_per_year": round(pm_total, 3),
        "track_extent_arcmin": round(extent, 2), "span_years": [round(oldest, 2), NOW_JYEAR],
        "track": [frac_xy(pos_at(y), center, fov) for y in np.linspace(oldest, NOW_JYEAR, 24)],
        "frames": frames, "skipped": skipped,
        "note": ("Mesmo campo do céu em todas as imagens (norte para cima, leste à esquerda). A marca é a posição "
                 "PREVISTA pelo movimento próprio do catálogo, não uma medida. Brilho e nitidez variam entre "
                 "telescópios e comprimentos de onda; um alvo fraco numa banda pode não aparecer nela."),
    }
    (DEMO / tid / "motion.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    return {"id": tid, "name": t.name, "file": f"demo/{tid}/motion.json", "frames": len(frames),
            "thumb": frames[0]["file"] if frames else None,
            "years": [frames[0]["date"][:4], frames[-1]["date"][:4]] if frames else None,
            "pm_total_arcsec_per_year": round(pm_total, 3), "track_extent_arcmin": round(extent, 2),
            "ra": t.ra, "dec": t.dec}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--target", choices=sorted(TARGET_IDS))
    p.add_argument("--spherex-per-detector", type=int, default=SPHEREX_PER_DETECTOR)
    args = p.parse_args()
    index_path = DEMO / "motion.json"
    index = json.loads(index_path.read_text("utf-8")) if index_path.exists() else {"targets": []}
    by_id = {x["id"]: x for x in index["targets"]}
    failed = []
    for tid in [args.target] if args.target else list(TARGET_IDS):
        print(f"== {tid}")
        try:
            by_id[tid] = build(tid, args.spherex_per_detector)
        except Exception as exc:  # noqa: BLE001
            print(f"  FALHOU: {exc}")
            failed.append(tid)
    index = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "targets": [by_id[k] for k in TARGET_IDS if k in by_id]}
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), "utf-8")
    print("falhas:", failed or "nenhuma")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
