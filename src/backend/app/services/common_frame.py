"""Common display frame: every cutout resampled onto the same sky grid.

Each SPHEREx exposure has its own orientation (the detector rotates on the
sky) and an IBE cutout near a detector edge is clipped. To compare epochs, sum
or subtract them, every image is resampled onto one grid:

* gnomonic (TAN) projection centred on the requested (or propagated) position;
* north up, east left; pixel scale = native SPHEREx scale (no up-sampling);
* side = field of view requested by the user.

Pixels of the grid that fall outside the source data (outside the detector)
are ``NaN`` and flagged in ``outside``; they must be shown as "no data",
never as dark sky.

Resampling is bilinear where the four neighbours are valid and nearest-pixel
otherwise, so isolated invalid pixels (e.g. a saturated core) stay invalid.
Implemented with numpy + astropy.wcs only (scipy/reproject are not
dependencies of the project).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
from astropy.wcs import WCS

#: Native SPHEREx pixel scale (arcsec), verified on the real FITS (6.1547").
SPHEREX_PIXEL_SCALE_ARCSEC = 6.15


@dataclass
class FrameImage:
    """An image resampled onto the common frame."""

    data: np.ndarray  # float, NaN where there is no valid value
    outside: np.ndarray  # bool, True where the grid is outside the source data
    wcs: WCS
    pixel_scale_arcsec: float
    #: Auxiliary planes resampled by nearest pixel (e.g. "flags", "variance").
    extras: dict[str, np.ndarray] = field(default_factory=dict)
    #: 0-based (x, y) of the frame centre in the source image (where the
    #: target falls on the detector: it sets the wavelength). None if unknown.
    center_source_xy: tuple[float, float] | None = None

    @property
    def coverage_fraction(self) -> float:
        """Fraction of the frame that lies inside the source data."""
        return float(1.0 - self.outside.mean()) if self.outside.size else 0.0


def frame_side_pixels(fov_arcmin: float, scale_arcsec: float, max_pixels: int = 2048) -> int:
    """Side of the square frame, in pixels (odd, so the target has a centre pixel)."""
    side = int(math.ceil(fov_arcmin * 60.0 / scale_arcsec))
    side += 1 - side % 2
    return max(3, min(side, max_pixels - (1 - max_pixels % 2)))


def frame_wcs(ra_deg: float, dec_deg: float, side: int, scale_arcsec: float) -> WCS:
    """TAN WCS of the common frame (north up, east left, centred on the target)."""
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [ra_deg, dec_deg]
    wcs.wcs.crpix = [(side + 1) / 2.0, (side + 1) / 2.0]
    wcs.wcs.cdelt = [-scale_arcsec / 3600.0, scale_arcsec / 3600.0]
    wcs.wcs.cunit = ["deg", "deg"]
    wcs.wcs.radesys = "ICRS"
    return wcs


def project_to_frame(
    data: np.ndarray,
    source_wcs: WCS,
    ra_deg: float,
    dec_deg: float,
    fov_arcmin: float,
    *,
    scale_arcsec: float = SPHEREX_PIXEL_SCALE_ARCSEC,
    max_pixels: int = 2048,
    extras: Mapping[str, np.ndarray] | None = None,
) -> FrameImage:
    """Resample ``data`` (with ``source_wcs``) onto the common frame.

    ``extras`` are planes aligned with ``data`` (FLAGS, VARIANCE) resampled by
    nearest pixel; outside the source, integer planes get 0 and float planes NaN.
    """
    source = np.asarray(data, dtype=float)
    if source.ndim != 2:
        raise ValueError("project_to_frame expects a 2D image")
    side = frame_side_pixels(fov_arcmin, scale_arcsec, max_pixels)
    target = frame_wcs(ra_deg, dec_deg, side, scale_arcsec)

    yy, xx = np.mgrid[0:side, 0:side].astype(float)
    ra, dec = target.wcs_pix2world(xx, yy, 0)
    sx, sy = source_wcs.celestial.all_world2pix(ra, dec, 0, quiet=True)
    sx = np.asarray(sx, dtype=float)
    sy = np.asarray(sy, dtype=float)

    height, width = source.shape
    inside = (
        np.isfinite(sx) & np.isfinite(sy)
        & (sx >= -0.5) & (sx <= width - 0.5)
        & (sy >= -0.5) & (sy <= height - 0.5)
    )

    out = np.full((side, side), np.nan)
    # Nearest pixel (always defined inside).
    nx = np.clip(np.rint(sx), 0, width - 1).astype(int)
    ny = np.clip(np.rint(sy), 0, height - 1).astype(int)
    out[inside] = source[ny[inside], nx[inside]]

    # Bilinear where the 4 neighbours exist and are finite.
    x0 = np.floor(sx)
    y0 = np.floor(sy)
    fx = sx - x0
    fy = sy - y0
    x0i = np.clip(x0, 0, width - 2).astype(int)
    y0i = np.clip(y0, 0, height - 2).astype(int)
    full = inside & (x0 >= 0) & (y0 >= 0) & (x0 <= width - 2) & (y0 <= height - 2)
    if full.any() and width > 1 and height > 1:
        v00 = source[y0i, x0i]
        v10 = source[y0i, x0i + 1]
        v01 = source[y0i + 1, x0i]
        v11 = source[y0i + 1, x0i + 1]
        ok = full & np.isfinite(v00) & np.isfinite(v10) & np.isfinite(v01) & np.isfinite(v11)
        bilinear = (
            v00 * (1 - fx) * (1 - fy) + v10 * fx * (1 - fy)
            + v01 * (1 - fx) * fy + v11 * fx * fy
        )
        out[ok] = bilinear[ok]

    projected: dict[str, np.ndarray] = {}
    for name, plane in (extras or {}).items():
        plane = np.asarray(plane)
        if plane.shape != source.shape:
            continue
        if np.issubdtype(plane.dtype, np.integer):
            result = np.zeros((side, side), dtype=np.int64)
        else:
            result = np.full((side, side), np.nan)
        result[inside] = plane[ny[inside], nx[inside]]
        projected[name] = result

    centre = (side - 1) // 2
    center_xy = None
    if np.isfinite(sx[centre, centre]) and np.isfinite(sy[centre, centre]):
        center_xy = (float(sx[centre, centre]), float(sy[centre, centre]))

    return FrameImage(
        data=out, outside=~inside, wcs=target, pixel_scale_arcsec=scale_arcsec,
        extras=projected, center_source_xy=center_xy,
    )
