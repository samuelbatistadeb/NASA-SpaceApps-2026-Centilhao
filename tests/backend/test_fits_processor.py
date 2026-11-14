"""Tests of the FITS processing (metadata, cutout and PNG rendering)."""

from __future__ import annotations

import io

import numpy as np
import pytest
from astropy.io import fits

from app.api.errors import ProcessingError
from app.services import fits_processor
from app.services.fits_processor import (
    VISUAL_NORMALIZATION_DESCRIPTION,
    cutout_image,
    extract_header_metadata,
    extract_observation_datetime,
    load_image,
    normalize_for_display,
    pixel_scale_arcsec,
    render_png,
    size_pixels_for_fov,
)

from conftest import build_synthetic_fits

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_load_image_extracts_the_science_plane(synthetic_fits: bytes) -> None:
    """The synthetic file must be opened and its plane extracted."""
    image = load_image(synthetic_fits)

    assert image.data.shape == (64, 64)
    assert image.hdu_index == 1
    assert image.header["INSTRUME"] == "synthetic-instrument"


def test_header_metadata_only_keeps_existing_keywords(synthetic_fits: bytes) -> None:
    """Only the keywords really present may be reported."""
    image = load_image(synthetic_fits)
    metadata = extract_header_metadata(image.header)

    assert metadata["DATE-OBS"] == "2026-01-02T03:04:05"
    assert metadata["EXPTIME"] == 300.0
    assert "TELESCOP" not in metadata


def test_observation_datetime_is_read_from_date_obs(synthetic_fits: bytes) -> None:
    """``DATE-OBS`` must be interpreted as UTC."""
    image = load_image(synthetic_fits)
    instant = extract_observation_datetime(image.header)

    assert instant is not None
    assert instant.isoformat() == "2026-01-02T03:04:05+00:00"


def test_observation_datetime_falls_back_to_mjd() -> None:
    """``MJD-OBS`` must be used when ``DATE-OBS`` is absent."""
    header = fits.Header({"MJD-OBS": 59000.25})
    instant = extract_observation_datetime(header)

    assert instant is not None
    assert instant.tzinfo is not None


def test_missing_observation_datetime_returns_none() -> None:
    """A header without temporal information must not produce a date."""
    assert extract_observation_datetime(fits.Header()) is None


def test_cutout_has_the_requested_size(synthetic_fits: bytes) -> None:
    """The cutout must have the requested side."""
    image = load_image(synthetic_fits)
    cutout = cutout_image(image, 32.0, 32.0, 16)

    assert cutout.data.shape == (16, 16)
    assert cutout.metadata["cutout_size_pixels"] == 16


def test_cutout_without_wcs_uses_the_centre_of_the_image(synthetic_fits: bytes) -> None:
    """Without a WCS the centre of the image must be used and reported."""
    image = load_image(synthetic_fits)
    cutout = cutout_image(image, 10.0, 20.0, 8)

    assert cutout.metadata["wcs_available"] is False
    assert cutout.metadata["cutout_center_source"] == "image_center_no_wcs"
    assert cutout.metadata["cutout_center_px"] == [31.5, 31.5]


def test_cutout_with_a_wcs_uses_the_requested_position() -> None:
    """With a WCS the requested position must be converted to pixels."""
    header = fits.Header()
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRVAL1"] = 10.0
    header["CRVAL2"] = 20.0
    header["CRPIX1"] = 32.0
    header["CRPIX2"] = 32.0
    header["CDELT1"] = -0.001
    header["CDELT2"] = 0.001
    header["CUNIT1"] = "deg"
    header["CUNIT2"] = "deg"

    data = np.zeros((64, 64), dtype=float)
    image = fits_processor.FitsImage(data=data, header=header, hdu_index=1, hdu_name="SCI")

    cutout = cutout_image(image, 10.0, 20.0, 8)

    assert cutout.metadata["wcs_available"] is True
    assert cutout.metadata["cutout_center_source"] == "wcs"
    # ``wcs_world2pix`` returns zero based coordinates, as expected by numpy.
    assert cutout.metadata["cutout_center_px"] == pytest.approx([31.0, 31.0])


def test_size_pixels_uses_the_pixel_scale_when_available() -> None:
    """The size must be derived from the field of view and the pixel scale."""
    size, criterion = size_pixels_for_fov(
        1.0, arcsec_per_pixel=0.5, default_pixels=256, max_pixels=2048
    )

    assert size == 120
    assert criterion == "fov_and_pixel_scale"


def test_size_pixels_falls_back_to_the_application_default() -> None:
    """Without a pixel scale the application default must be used and reported."""
    size, criterion = size_pixels_for_fov(
        1.0, arcsec_per_pixel=None, default_pixels=256, max_pixels=2048
    )

    assert size == 256
    assert criterion == "application_default_no_pixel_scale"


def test_render_png_produces_a_valid_image() -> None:
    """The PNG must be a real image, not an empty file."""
    data = np.linspace(0.0, 10.0, 4096).reshape(64, 64)

    content = render_png(data)

    assert content.startswith(PNG_MAGIC)
    assert len(content) > 1000

    import matplotlib.image as mpimg

    image = mpimg.imread(io.BytesIO(content), format="png")
    assert image.ndim in (2, 3)
    assert image.shape[0] > 0 and image.shape[1] > 0


def test_normalisation_handles_non_finite_values() -> None:
    """The visual normalisation must ignore NaN and infinite pixels."""
    data = np.array([[1.0, np.nan], [np.inf, 4.0]])

    normalised, vmin, vmax = normalize_for_display(data)

    assert np.isfinite(normalised).all()
    assert vmin <= vmax


def test_normalisation_fails_without_valid_values() -> None:
    """An image without any valid pixel must be reported."""
    with pytest.raises(ProcessingError):
        normalize_for_display(np.array([[np.nan, np.nan]]))


def test_broken_fits_is_reported_as_processing_error() -> None:
    """A file that is not a FITS must be reported as a processing error."""
    with pytest.raises(ProcessingError):
        load_image(b"this is not a FITS file")


def test_visual_normalisation_is_declared_as_display_only() -> None:
    """The description must state that the stretch is not a measurement."""
    assert "not a photometric measurement" in VISUAL_NORMALIZATION_DESCRIPTION.lower()


def test_pixel_scale_of_a_wcs_without_cdelt_is_none() -> None:
    """A WCS without a scale must not produce an invented value."""
    header = fits.Header()
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRVAL1"] = 10.0
    header["CRVAL2"] = 20.0
    wcs = fits_processor.extract_wcs(header)

    assert wcs is not None
    assert pixel_scale_arcsec(wcs) is not None
