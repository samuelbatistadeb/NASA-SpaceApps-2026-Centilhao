
"""Spatial coverage checks for astronomical FITS images."""

from __future__ import annotations

import math

from astropy.wcs import WCS


def contains_sky_position(
    wcs: WCS,
    image_shape: tuple[int, int],
    ra_deg: float,
    dec_deg: float,
) -> bool:
    """Check whether a sky position falls inside an image.

    image_shape follows NumPy ordering: (height, width).
    """

    height, width = image_shape

    if height <= 0 or width <= 0:
        return False

    if not wcs.has_celestial:
        return False

    try:
        x, y = wcs.celestial.all_world2pix(
            ra_deg,
            dec_deg,
            0,
        )
    except (ValueError, RuntimeError):
        return False

    if not math.isfinite(x) or not math.isfinite(y):
        return False

    return bool(
        -0.5 <= x < width - 0.5
        and -0.5 <= y < height - 0.5
    )
