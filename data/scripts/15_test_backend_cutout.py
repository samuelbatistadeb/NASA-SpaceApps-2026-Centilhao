
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(PROJECT_ROOT / "src" / "backend"),
)

from app.services import fits_processor


FITS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "spherex"
    / "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
)


def main():
    if not FITS_PATH.is_file():
        raise FileNotFoundError(FITS_PATH)

    print("=== TESTE DO PROCESSADOR BACKEND ===")

    content = FITS_PATH.read_bytes()

    image = fits_processor.load_image(content)

    print("Extensão selecionada:", image.hdu_name)
    print("Dimensões:", image.data.shape)

    wcs = fits_processor.extract_wcs(image.header)

    scale = fits_processor.pixel_scale_arcsec(wcs)

    print("Escala espacial:", scale, "arcsec/pixel")

    size, criterion = fits_processor.size_pixels_for_fov(
        4.24264,
        arcsec_per_pixel=scale,
        default_pixels=64,
        max_pixels=2040,
    )

    print("Tamanho calculado:", size)
    print("Critério:", criterion)

    cutout = fits_processor.cutout_image(
        image=image,
        ra_deg=133.795129,
        dec_deg=-7.245147,
        size_pixels=size,
    )

    print("Dimensões do recorte:", cutout.data.shape)
    print("Metadados:", cutout.metadata)

    png_bytes = fits_processor.render_png(cutout.data)

    output = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "spherex"
        / "wise0855_backend.png"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(png_bytes)

    print("PNG gerado:", output)
    print("Tamanho PNG:", len(png_bytes), "bytes")
    print("TESTE CONCLUÍDO")


if __name__ == "__main__":
    main()
