"""Proper-motion propagation of a sky position to the epoch of each exposure.

SPHEREx publishes ``target_moving = 0`` for every product, so following a fast
moving star (WISE 0855 ~8"/yr, Barnard ~10"/yr) is the responsibility of the
application (DECISÃO 007, item 8).

Model: linear motion on the plane tangent to the sky at the reference
position, converted back with the inverse gnomonic projection. Parallax and
radial velocity are ignored: the parallactic oscillation of the nearest test
targets is <= 0.55" (Barnard), below 0.1 of a 6.15" SPHEREx pixel.
The time scale (UTC vs TT, ~69 s) is irrelevant at this precision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

#: Milliarcseconds in one radian.
_MAS_PER_RAD = math.degrees(1.0) * 3_600_000.0
#: Julian date of J2000.0 and length of the Julian year.
_JD_J2000 = 2451545.0
_DAYS_PER_JULIAN_YEAR = 365.25
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_JD_UNIX_EPOCH = 2440587.5


@dataclass(frozen=True)
class ProperMotion:
    """Proper motion of a target and the epoch of its reference position.

    ``pm_ra_cosdec_masyr`` already includes the ``cos(dec)`` factor (Gaia
    convention ``pmra``); positive = towards larger RA (east).
    """

    pm_ra_cosdec_masyr: float
    pm_dec_masyr: float
    ref_epoch_jyear: float

    @property
    def total_masyr(self) -> float:
        return math.hypot(self.pm_ra_cosdec_masyr, self.pm_dec_masyr)


def jyear_from_datetime(instant: datetime) -> float:
    """Return the Julian year (e.g. 2025.34) of a UTC instant."""
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    days = (instant - _UNIX_EPOCH).total_seconds() / 86400.0
    jd = _JD_UNIX_EPOCH + days
    return 2000.0 + (jd - _JD_J2000) / _DAYS_PER_JULIAN_YEAR


def propagate_position(
    ra_deg: float, dec_deg: float, motion: ProperMotion, epoch_jyear: float
) -> tuple[float, float]:
    """Return ``(ra_deg, dec_deg)`` of the target at ``epoch_jyear``."""
    years = epoch_jyear - motion.ref_epoch_jyear
    xi = motion.pm_ra_cosdec_masyr * years / _MAS_PER_RAD  # east offset, radians
    eta = motion.pm_dec_masyr * years / _MAS_PER_RAD  # north offset, radians

    ra0 = math.radians(ra_deg)
    dec0 = math.radians(dec_deg)
    denominator = math.cos(dec0) - eta * math.sin(dec0)
    ra = ra0 + math.atan2(xi, denominator)
    dec = math.atan2(
        math.sin(dec0) + eta * math.cos(dec0), math.hypot(xi, denominator)
    )
    return math.degrees(ra) % 360.0, math.degrees(dec)
