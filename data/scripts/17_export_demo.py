"""Export a static demonstration package with REAL SPHEREx data.

The package lets the public site work when the IRSA search service (SIA) or
the backend is unavailable: the frontend loads ``src/frontend/demo/`` as
plain files (contract in ``src/frontend/README.md`` / app.js).

Everything exported is real: the list of products comes from the IRSA SIA
(live, or a real SIA answer saved earlier with ``--sia-file``) and the
images/spectra are computed by the backend from real IBE cutouts.

Usage (from the repository root, with the project venv):

    .venv/Scripts/python.exe data/scripts/17_export_demo.py --target wise0855
    .venv/Scripts/python.exe data/scripts/17_export_demo.py --target wise0855 \
        --sia-file data/sia_snapshots/wise0855_sia_2026-11-15.xml   # when the SIA is down

Re-run before a presentation to refresh the package.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "backend"))

from app.api import observations as api  # noqa: E402
from app.api.targets import TARGETS  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.services.astrometry import ProperMotion  # noqa: E402
from app.services.cache import DiskCache  # noqa: E402
from app.services.cutout_service import CutoutService  # noqa: E402
from app.services.irsa_client import HttpResponse, HttpxTransport  # noqa: E402
from app.services.observation_service import COMPLETE_COVERAGE, ObservationService  # noqa: E402

DEMO_DIR = ROOT / "src" / "frontend" / "demo"
TARGET_IDS = {"wise0855": "WISE 0855", "barnard": "Estrela de Barnard", "epsindi": "ε Indi",
              "rwaur": "RW Aurigae", "rdra": "R Draconis"}


class SavedSiaTransport:
    """Answer SIA requests with a real answer saved earlier; IBE goes live."""

    def __init__(self, sia_file: Path) -> None:
        self._sia = sia_file.read_bytes()
        self._real = HttpxTransport()

    def request(self, method, url, **kwargs):
        if url.rstrip("/").endswith("/SIA"):
            return HttpResponse(200, self._sia, {"content-type": "text/xml"}, url)
        return self._real.request(method, url, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", choices=sorted(TARGET_IDS), required=True)
    parser.add_argument("--fov", type=float, default=3.0)
    parser.add_argument("--sia-file", type=Path, help="real SIA VOTable saved earlier")
    parser.add_argument("--max-spectrum", type=int, default=60)
    args = parser.parse_args()

    target = next(t for t in TARGETS if t.name == TARGET_IDS[args.target])
    motion = None
    if target.pm_ra_cosdec_masyr is not None:
        motion = ProperMotion(target.pm_ra_cosdec_masyr, target.pm_dec_masyr, target.ref_epoch_jyear)

    settings = Settings.from_env()
    client = api.get_irsa_client()
    if args.sia_file:
        client._transport = SavedSiaTransport(args.sia_file)
    service = ObservationService(
        client, DiskCache(settings.cache_dir, settings.cache_ttl_seconds),
        CutoutService(client, settings), settings,
    )

    out = DEMO_DIR / args.target
    # Keep what other scripts write here (19_motion_timeline.py: motion/ and motion.json).
    keep = {"motion", "motion.json"}
    if out.exists():
        for item in out.iterdir():
            if item.name in keep:
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    (out / "img").mkdir(parents=True, exist_ok=True)
    rel = f"demo/{args.target}"
    t0 = time.time()

    response = service.search(target.ra, target.dec, args.fov, motion=motion)
    payload = response.model_dump(mode="json")
    exported = []
    for observation in payload["observations"]:
        try:
            image = service.get_image(observation["id"])
        except Exception as exc:  # noqa: BLE001 - keep the others
            print(f"  sem imagem {observation['id']}: {exc}")
            continue
        (out / "img" / f"{observation['id']}.png").write_bytes(image.content)
        observation["image_url"] = f"{rel}/img/{observation['id']}.png"
        exported.append(observation)
    payload["observations"] = exported
    payload["total_observations"] = len(exported)
    payload["data_source"] = "demo_snapshot"
    payload["data_cached_at"] = datetime.now(timezone.utc).isoformat()
    (out / "observations.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), "utf-8")
    print(f"observações: {len(exported)} imagens ({time.time() - t0:.0f}s)")

    quality = {}
    for observation in exported:
        try:
            quality[observation["id"]] = service.quality(observation["id"])
        except Exception:  # noqa: BLE001
            pass
    (out / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=1), "utf-8")

    has_coverage = has_spectrum = False
    try:
        coverage = service.coverage(target.ra, target.dec, motion)
        (out / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=1), "utf-8")
        has_coverage = True
    except Exception as exc:  # noqa: BLE001 - optional part of the package
        print(f"  cobertura indisponível: {exc}")

    try:
        spectrum = service.spectrum(target.ra, target.dec, motion, max_exposures=args.max_spectrum)
        (out / "spectrum.json").write_text(json.dumps(spectrum, ensure_ascii=False, indent=1), "utf-8")
        has_spectrum = True
        clean = sum(1 for p in spectrum["points"] if not p["flagged"])
        print(f"espectro: {len(spectrum['points'])} pontos ({clean} sem contaminação)")
    except Exception as exc:  # noqa: BLE001
        print(f"  espectro indisponível: {exc}")

    composites = []
    by_detector: dict[str, list[dict]] = {}
    for observation in exported:
        if (observation["metadata"].get("coverage_fraction") or 0) >= COMPLETE_COVERAGE:
            by_detector.setdefault(observation["detector"], []).append(observation)
    for detector, group in sorted(by_detector.items()):
        if len(group) < 4:
            continue
        ids = [o["id"] for o in group]
        half = min(len(ids) // 2, 20)
        for op, a, b, text in (
            ("mean", ids[:40], None, f"Média de {min(len(ids), 40)} épocas do {detector} (maior sinal/ruído)"),
            ("diff", ids[-half:], ids[:half],
             f"Diferença {detector}: {half} épocas mais recentes − {half} mais antigas"),
        ):
            try:
                result = service.composite(op, a, b)
            except Exception as exc:  # noqa: BLE001
                print(f"  composite {op} {detector} falhou: {exc}")
                continue
            name = f"composite_{op}_{detector}.png"
            (out / name).write_bytes(result.content)
            composites.append({"op": op, "detector": detector, "file": f"{rel}/{name}",
                               "description": text, "metadata": result.metadata})

    manifest_path = DEMO_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {"targets": []}
    manifest["targets"] = [t for t in manifest["targets"] if t["id"] != args.target]
    manifest["targets"].append({
        "id": args.target,
        "name": target.name,
        "ra": target.ra,
        "dec": target.dec,
        "fov": args.fov,
        "motion": None if motion is None else {
            "pm_ra_cosdec_masyr": motion.pm_ra_cosdec_masyr,
            "pm_dec_masyr": motion.pm_dec_masyr,
            "ref_epoch_jyear": motion.ref_epoch_jyear,
        },
        "observations": f"{rel}/observations.json",
        "coverage": f"{rel}/coverage.json" if has_coverage else None,
        "spectrum": f"{rel}/spectrum.json" if has_spectrum else None,
        "quality": f"{rel}/quality.json",
        "composites": composites,
        "product_list_source": (
            f"resposta real do SIA salva ({args.sia_file.name}); pode ser uma lista parcial"
            if args.sia_file else "SIA do IRSA ao vivo"
        ),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    })
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["note"] = (
        "Dados reais do SPHEREx (IRSA/IPAC) salvos para demonstração quando o arquivo "
        "IRSA ou o servidor não estiverem disponíveis. Gerado por data/scripts/17_export_demo.py."
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"pacote {out} ({size / 1024:.0f} KB), {len(composites)} composites, {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
