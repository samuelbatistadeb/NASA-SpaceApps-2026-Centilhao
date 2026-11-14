
from pathlib import Path
import json

import numpy as np
from astropy.io import fits
from astropy.visualization import (
    ImageNormalize,
    AsinhStretch,
    PercentileInterval,
)
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FITS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "spherex"
    / "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "spherex"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not FITS_PATH.is_file():
        raise FileNotFoundError(
            f"Arquivo FITS não encontrado: {FITS_PATH}"
        )

    print("=== SPHEREx FITS Renderer ===")

    with fits.open(FITS_PATH, memmap=True) as hdul:
        print("\nExtensões:")
        hdul.info()

        if "IMAGE" not in hdul:
            raise ValueError(
                "Extensão IMAGE não encontrada. "
                "Verifique a estrutura do FITS."
            )

        data = np.asarray(
            hdul["IMAGE"].data,
            dtype=np.float32,
        )

        header = hdul["IMAGE"].header

    print("\nDimensões:", data.shape)

    if data.ndim != 2:
        raise ValueError(
            f"Esperada imagem 2D; recebido: {data.shape}"
        )

    valid = np.isfinite(data)

    if not valid.any():
        raise ValueError(
            "A imagem não contém pixels válidos."
        )

    print("Pixels válidos:", int(valid.sum()))
    print("Mínimo:", float(np.min(data[valid])))
    print("Máximo:", float(np.max(data[valid])))

    # Percentis robustos reduzem a influência de valores extremos.
    low, high = PercentileInterval(99.5).get_limits(
        data[valid]
    )

    if high <= low:
        raise ValueError(
            "Não foi possível determinar um intervalo "
            "de contraste válido."
        )

    # Escala asinh para preservar estruturas tênues.
    normalization = ImageNormalize(
        vmin=low,
        vmax=high,
        stretch=AsinhStretch(),
        clip=True,
    )

    normalized = np.zeros(
        data.shape,
        dtype=np.float32,
    )

    normalized[valid] = normalization(
        data[valid]
    ).filled(0)

    pixels = np.clip(
        normalized * 255,
        0,
        255,
    ).astype(np.uint8)

    output_png = OUTPUT_DIR / "spherex_first_image.png"
    output_json = OUTPUT_DIR / "spherex_first_image.json"

    Image.fromarray(pixels, mode="L").save(output_png)

    metadata = {
        "source_file": FITS_PATH.name,
        "source_extension": "IMAGE",
        "dimensions": list(data.shape),
        "valid_pixels": int(valid.sum()),
        "contrast_method": "percentile_99.5_asinh",
        "contrast_min": float(low),
        "contrast_max": float(high),
        "visualization_only": True,
        "image_header": {
            key: header.get(key)
            for key in (
                "BUNIT",
                "CTYPE1",
                "CTYPE2",
                "CRVAL1",
                "CRVAL2",
            )
        },
    }

    output_json.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\nImagem gerada:", output_png)
    print("Metadados:", output_json)
    print("Processamento concluído!")


if __name__ == "__main__":
    main()
