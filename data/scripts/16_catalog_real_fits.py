
"""Inspect genuine SPHEREx FITS metadata for local cataloging."""

from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FITS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "spherex"
    / "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
)

KEYWORDS = (
    "DATE-OBS",
    "MJD-OBS",
    "DATE-END",
    "MJD-END",
    "TELESCOP",
    "INSTRUME",
    "DETECTOR",
    "CHANNEL",
    "FILTER",
    "EXPTIME",
    "BUNIT",
    "CRVAL1",
    "CRVAL2",
    "CRPIX1",
    "CRPIX2",
    "CTYPE1",
    "CTYPE2",
    "WCSAXES",
    "WAVEMIN",
    "WAVEMAX",
)


def main() -> None:
    if not FITS_PATH.is_file():
        raise FileNotFoundError(FITS_PATH)

    print("=== PRODUTO SPHEREx ===")
    print(f"Arquivo: {FITS_PATH.name}")
    print(f"Tamanho: {FITS_PATH.stat().st_size} bytes")

    with fits.open(FITS_PATH, memmap=True) as hdul:
        print("\n=== EXTENSOES ===")

        for index, hdu in enumerate(hdul):
            shape = (
                hdu.data.shape
                if hdu.data is not None
                else None
            )

            print(
                f"{index}: {hdu.name} | "
                f"shape={shape}"
            )

        for index in (0, 1):
            if index >= len(hdul):
                continue

            header = hdul[index].header

            print(f"\n=== CABECALHO HDU {index} ===")

            for key in KEYWORDS:
                if key in header:
                    print(f"{key}: {header[key]}")

        image_hdu = hdul["IMAGE"]

        print("\n=== WCS CELESTIAL ===")

        wcs = WCS(image_hdu.header)

        if wcs.has_celestial:
            celestial = wcs.celestial

            print(f"CTYPE: {celestial.wcs.ctype}")
            print(f"CRVAL: {celestial.wcs.crval}")
            print(f"CRPIX: {celestial.wcs.crpix}")
        else:
            print("WCS celestial indisponivel")

        if "WCS-WAVE" in hdul:
            wave = hdul["WCS-WAVE"]

            print("\n=== CALIBRACAO ESPECTRAL ===")
            print(f"Shape: {wave.data.shape}")

            print("\nCabecalho WCS-WAVE:")
            for card in wave.header.cards:
                print(card)


if __name__ == "__main__":
    main()
