"""Wavelength of a SPHEREx pixel from the WCS-WAVE lookup table.

SPHEREx detectors carry a linear variable filter: the wavelength changes
across the detector, so a source observed at different detector positions in
different exposures is measured at different wavelengths. That is how a
spectrum is built from images.

Verified on real DR1 products (2026-11-15):
* the IMAGE header has an alternative WCS ``W`` (``CTYPE*W = 'WAVE-TAB'``)
  pointing to the ``WCS-WAVE`` binary table (1 row; X, Y control points and
  VALUES[2, 9, 14] = wavelength and bandwidth, in micrometres);
* the table is identical for every exposure of a detector processed with the
  same calibration, and an IBE cutout carries the full table (only
  ``CRPIX*W`` in the IMAGE header changes with the cutout);
* the official IRSA tutorials evaluate it with ``WCS(hdr, fobj=hdul, key='W')``
  and ``sip = None``.

The Explanatory Supplement (§4.3.1) calls this WCS approximate, adequate for
visualisation; the UI must say so.

The table sits at the very end of the file, after the 3.9 MB EPSF table, so it
is read with an HTTP Range request of the last bytes of the full product.
"""

from __future__ import annotations

import io
import threading
import warnings

import numpy as np
from astropy import log as astropy_log
from astropy.io import fits
from astropy.wcs import WCS

#: Bytes read from the end of a product to get the WCS-WAVE HDU (5760 B for
#: detector 3; a few blocks of margin).
WCS_WAVE_TAIL_BYTES = 4 * 2880
WAVELENGTH_SOURCE = "WCS-WAVE (aproximada; Explanatory Supplement §4.3.1)"

_BLOCK = 2880
_ASTROPY_LOG_LOCK = threading.Lock()


def parse_wcs_wave_tail(tail: bytes) -> fits.BinTableHDU | None:
    """Find the ``WCS-WAVE`` table in the last bytes of a FITS file.

    ``tail`` must end at the end of the file; HDUs start on 2880-byte blocks
    counted from the end only if the file size is a multiple of 2880, which
    FITS guarantees.
    """
    offset = len(tail) % _BLOCK
    for start in range(offset, len(tail), _BLOCK):
        block = tail[start:start + 80]
        if not block.startswith(b"XTENSION"):
            continue
        header_text = tail[start:start + 3 * _BLOCK].decode("ascii", errors="replace")
        if "EXTNAME = 'WCS-WAVE" not in header_text:
            continue
        primary = fits.PrimaryHDU().header.tostring().encode("ascii")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                hdul = fits.open(io.BytesIO(primary + tail[start:]), lazy_load_hdus=False)
                hdu = fits.BinTableHDU(data=hdul[1].data.copy(), header=hdul[1].header.copy())
                hdul.close()
            return hdu
        except Exception:  # noqa: BLE001 - malformed tail = unknown wavelength
            return None
    return None


def wavelength_at(
    image_header: fits.Header, wcs_wave: fits.BinTableHDU, x: float, y: float
) -> tuple[float, float] | None:
    """Return ``(wavelength_um, bandwidth_um)`` at 0-based pixel (x, y) of the image.

    ``image_header`` is the header of the IMAGE HDU the pixel refers to (an
    IBE cutout header already has ``CRPIX*W`` adjusted to the cutout).
    """
    if "CTYPE1W" not in image_header:
        return None
    hdul = fits.HDUList([fits.PrimaryHDU(), wcs_wave])
    # astropy logs an INFO about SIP for this alternative WCS; sip is disabled below.
    # The log level is global: serialise, or parallel spectra race on it.
    with _ASTROPY_LOG_LOCK:
        return _wavelength_at_locked(image_header, hdul, x, y)


def _wavelength_at_locked(image_header, hdul, x, y) -> tuple[float, float] | None:
    previous_level = astropy_log.level
    astropy_log.setLevel("WARNING")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wcs = WCS(image_header, fobj=hdul, key="W")
            wcs.sip = None
            wavelength, bandwidth = wcs.pixel_to_world_values(x, y)
    except Exception:  # noqa: BLE001 - no usable spectral WCS
        return None
    finally:
        astropy_log.setLevel(previous_level)
    wavelength, bandwidth = float(np.asarray(wavelength)), float(np.asarray(bandwidth))
    if not (np.isfinite(wavelength) and np.isfinite(bandwidth)):
        return None
    return wavelength, bandwidth


def calibration_key(access_url: str, detector: str | None) -> str:
    """Cache key of the WCS-WAVE table: detector + processing directory.

    Products of one processing run (``.../l2b-v27-2026-197/3/...``) share the
    spectral calibration of the detector (verified identical across
    exposures and even across two processing directories).
    """
    parts = access_url.split("/")
    version = next((p for p in parts if p.startswith("l2b-")), "")
    return f"{detector or ''}|{version}"


def aperture_photometry(frame, radius_px: float) -> dict | None:
    """Mean surface brightness in a circular aperture at the frame centre.

    Background = median of an annulus between 2 and 3 aperture radii, so the
    result is the source excess over the local sky (MJy/sr). The error comes
    from the VARIANCE plane (when present): sqrt(sum var) / n. Returns
    ``None`` when the aperture or the annulus has no valid pixel.
    """
    data = np.where(frame.outside, np.nan, frame.data)
    side = data.shape[0]
    centre = (side - 1) / 2.0
    yy, xx = np.mgrid[0:side, 0:side]
    r = np.hypot(xx - centre, yy - centre)
    aperture = r <= radius_px
    annulus = (r >= 2.0 * radius_px) & (r <= 3.0 * radius_px)
    inside = data[aperture]
    ring = data[annulus]
    if not np.isfinite(inside).any() or not np.isfinite(ring).any():
        return None
    background = float(np.nanmedian(ring))
    n = int(np.isfinite(inside).sum())
    flux = float(np.nanmean(inside)) - background
    flux_err = None
    variance = frame.extras.get("variance")
    if variance is not None:
        values = variance[aperture]
        values = values[np.isfinite(values) & np.isfinite(inside)]
        if values.size:
            flux_err = float(np.sqrt(values.sum()) / values.size)
    flags = frame.extras.get("flags")
    flags_value = int(np.bitwise_or.reduce(flags[aperture].ravel())) if flags is not None else 0
    return {
        "flux": round(flux, 6),
        "flux_err": None if flux_err is None else round(flux_err, 6),
        "background": round(background, 6),
        "n_pixels": n,
        "flags_value": flags_value,
    }
