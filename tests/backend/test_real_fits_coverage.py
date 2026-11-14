
"""Spatial coverage checks using a genuine SPHEREx product."""

from pathlib import Path

import pytest
from astropy.io import fits
from astropy.wcs import WCS

from app.services.sky_coverage import contains_sky_position


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FITS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "spherex"
    / "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
)


@pytest.mark.skipif(
    not FITS_PATH.is_file(),
    reason="Real SPHEREx FITS unavailable",
)
def test_real_fits_sky_coverage() -> None:
    with fits.open(FITS_PATH, memmap=True) as hdul:
        hdu = hdul["IMAGE"]

        wcs = WCS(hdu.header).celestial
        shape = hdu.data.shape

        center_inside = contains_sky_position(
            wcs,
            shape,
            134.414675682,
            -9.0062724739,
        )

        wise0855_inside = contains_sky_position(
            wcs,
            shape,
            133.795129,
            -7.245147,
        )

        print()
        print("=== COBERTURA ESPACIAL ===")
        print(f"Centro do FITS: {center_inside}")
        print(f"WISE 0855: {wise0855_inside}")

        assert center_inside is True
        assert wise0855_inside is True
