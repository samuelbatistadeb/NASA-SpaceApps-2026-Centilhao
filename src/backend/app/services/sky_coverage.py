
"""Spatial coverage checks for astronomical FITS images."""

from __future__ import annotations

import math

import numpy as np
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


def parse_s_region(text: object) -> list[tuple[float, float]] | None:
    """Parse an ObsCore ``s_region`` polygon into ``(ra_deg, dec_deg)`` vertices.

    Accepts the form published by the IRSA SIA v2 service for SPHEREx
    (``POLYGON ICRS ra1 dec1 ra2 dec2 ...``, verified on the real answer
    saved in ``tests/backend/fixtures``). The frame token is optional. Anything
    else (circles, malformed text, fewer than 3 vertices) gives ``None``,
    meaning "footprint unknown".
    """
    if not isinstance(text, str):
        return None
    tokens = text.split()
    if not tokens or tokens[0].upper() != "POLYGON":
        return None
    values: list[float] = []
    for token in tokens[1:]:
        try:
            values.append(float(token))
        except ValueError:
            if values:
                return None
            # Leading frame tokens (``ICRS``, ``J2000`` ...) are skipped.
    if len(values) % 2 or not all(math.isfinite(value) for value in values):
        return None
    vertices = list(zip(values[0::2], values[1::2]))
    if len(vertices) > 1 and vertices[0] == vertices[-1]:
        vertices.pop()
    return vertices if len(vertices) >= 3 else None


def polygon_contains_position(
    vertices: list[tuple[float, float]],
    ra_deg: float,
    dec_deg: float,
) -> bool:
    """Check whether a sky position lies inside a spherical polygon.

    The vertices are projected on the plane tangent to the sphere at the
    position (gnomonic projection), where great-circle edges are straight
    lines and the position is the origin; an even-odd ray test follows. A
    vertex 90 degrees or more away cannot be projected: the polygon is then
    treated as not containing the position, which is correct for footprints
    of a few degrees such as the SPHEREx detectors (~3.5 degrees).
    """
    ra0 = math.radians(ra_deg)
    dec0 = math.radians(dec_deg)
    projected: list[tuple[float, float]] = []
    for vertex_ra, vertex_dec in vertices:
        ra = math.radians(vertex_ra)
        dec = math.radians(vertex_dec)
        cos_c = math.sin(dec0) * math.sin(dec) + math.cos(dec0) * math.cos(dec) * math.cos(
            ra - ra0
        )
        if cos_c <= 1e-9:
            return False
        x = math.cos(dec) * math.sin(ra - ra0) / cos_c
        y = (
            math.cos(dec0) * math.sin(dec)
            - math.sin(dec0) * math.cos(dec) * math.cos(ra - ra0)
        ) / cos_c
        projected.append((x, y))

    inside = False
    count = len(projected)
    for index in range(count):
        x1, y1 = projected[index]
        x2, y2 = projected[(index + 1) % count]
        if (y1 > 0.0) != (y2 > 0.0):
            crossing_x = x1 + (0.0 - y1) * (x2 - x1) / (y2 - y1)
            if crossing_x > 0.0:
                inside = not inside
    return inside


def _gnomonic_vertices(
    vertices: list[tuple[float, float]], ra_deg: float, dec_deg: float
) -> np.ndarray | None:
    """Project polygon vertices on the plane tangent at (ra, dec), in arcmin.

    x grows to the east, y to the north. Returns ``None`` when a vertex is
    90 degrees or more away (it cannot be projected).
    """
    ra0 = math.radians(ra_deg)
    dec0 = math.radians(dec_deg)
    ra = np.radians([v[0] for v in vertices])
    dec = np.radians([v[1] for v in vertices])
    cos_c = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(ra - ra0)
    if np.any(cos_c <= 1e-9):
        return None
    x = np.cos(dec) * np.sin(ra - ra0) / cos_c
    y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(ra - ra0)) / cos_c
    return np.degrees(np.column_stack([x, y])) * 60.0


def footprint_coverage(
    vertices: list[tuple[float, float]],
    ra_deg: float,
    dec_deg: float,
    fov_arcmin: float,
    samples: int = 21,
) -> float:
    """Fraction of a square field (side ``fov_arcmin``, north up) inside a footprint.

    The square is centred on (ra, dec) in the tangent plane, the same frame
    used by :mod:`app.services.common_frame`. The fraction is estimated on a
    ``samples`` x ``samples`` grid of points (even-odd rule, vectorised).
    """
    polygon = _gnomonic_vertices(vertices, ra_deg, dec_deg)
    if polygon is None:
        return 0.0
    half = fov_arcmin / 2.0
    axis = (np.arange(samples) + 0.5) / samples * fov_arcmin - half
    px, py = np.meshgrid(axis, axis)
    px = px.ravel()
    py = py.ravel()
    inside = np.zeros(px.shape, dtype=bool)
    x1, y1 = polygon[:, 0], polygon[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    for ax, ay, bx, by in zip(x1, y1, x2, y2):
        crosses = (ay > py) != (by > py)
        if not crosses.any():
            continue
        x_at = ax + (py - ay) * (bx - ax) / (by - ay if by != ay else 1e-300)
        inside ^= crosses & (px < x_at)
    return float(inside.mean())
