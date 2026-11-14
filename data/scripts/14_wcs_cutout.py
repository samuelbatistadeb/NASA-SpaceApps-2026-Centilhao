
from pathlib import Path
import json

import numpy as np
from PIL import Image

from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy.nddata import Cutout2D
from astropy import units as u
from astropy.visualization import (
    ImageNormalize,
    AsinhStretch,
    PercentileInterval,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FITS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "spherex"
    / "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "spherex"

RA_DEG = 133.795129
DEC_DEG = -7.245147
FOV_ARCMIN = 4.24264


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not FITS_PATH.is_file():
        raise FileNotFoundError(FITS_PATH)

    position = SkyCoord(
        ra=RA_DEG * u.deg,
        dec=DEC_DEG * u.deg,
        frame="icrs",
    )

    with fits.open(FITS_PATH, memmap=True) as hdul:
        image_hdu = hdul["IMAGE"]

        data = np.asarray(
            image_hdu.data,
            dtype=np.float32,
        )

        wcs = WCS(image_hdu.header).celestial

        x, y = wcs.world_to_pixel(position)

        print("=== SPHEREx WCS Cutout ===")
        print("Coordenadas:", RA_DEG, DEC_DEG)
        print("Posição em pixels:", x, y)
        print("Dimensões originais:", data.shape)

        height, width = data.shape

        if not (
            np.isfinite(x)
            and np.isfinite(y)
            and 0 <= x < width
            and 0 <= y < height
        ):
            raise ValueError(
                "O alvo está fora dos limites da imagem."
            )

        cutout = Cutout2D(
            data,
            position=position,
            size=FOV_ARCMIN * u.arcmin,
            wcs=wcs,
            mode="partial",
            fill_value=np.nan,
            copy=True,
        )

    pixels = cutout.data

    valid = np.isfinite(pixels)

    if not valid.any():
        raise ValueError(
            "O recorte não contém pixels válidos."
        )

    low, high = PercentileInterval(99.5).get_limits(
        pixels[valid]
    )

    if high <= low:
        raise ValueError(
            "Intervalo de contraste inválido."
        )

    normalization = ImageNormalize(
        vmin=low,
        vmax=high,
        stretch=AsinhStretch(),
        clip=True,
    )

    normalized = np.zeros(
        pixels.shape,
        dtype=np.float32,
    )

    normalized[valid] = normalization(
        pixels[valid]
    ).filled(0)

    png_pixels = np.clip(
        normalized * 255,
        0,
        255,
    ).astype(np.uint8)

    output_png = OUTPUT_DIR / "wise0855_cutout.png"
    output_json = OUTPUT_DIR / "wise0855_cutout.json"

    Image.fromarray(png_pixels).save(output_png)

    metadata = {
        "target": "WISE 0855",
        "ra_deg": RA_DEG,
        "dec_deg": DEC_DEG,
        "fov_arcmin": FOV_ARCMIN,
        "source_file": FITS_PATH.name,
        "source_extension": "IMAGE",
        "pixel_position": {
            "x": float(x),
            "y": float(y),
        },
        "cutout_dimensions": list(pixels.shape),
        "valid_pixels": int(valid.sum()),
        "normalization": "percentile_99.5_asinh",
        "contrast_min": float(low),
        "contrast_max": float(high),
        "visualization_only": True,
    }

    output_json.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nRecorte gerado:", output_png)
    print("Dimensões:", pixels.shape)
    print("Pixels válidos:", int(valid.sum()))
    print("Metadados:", output_json)


if __name__ == "__main__":
    main()
