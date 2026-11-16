"""Wavelength (WCS-WAVE), FLAGS, aperture photometry, quality and spectrum.

Real-data fixtures (saved unchanged on 2026-11-15 from an IBE cutout of
level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits, 29x29 px at
133.737467, -7.240406): the last 11520 bytes of the cutout (WCS-WAVE table),
and the IMAGE and FLAGS headers. Reference wavelength at the cutout centre,
computed with the method of the official IRSA tutorial
(``WCS(hdr, fobj=hdul, key='W')``, ``sip=None``) on the full cutout:
2.36218 um, bandwidth 0.05848 um.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from app.api.errors import ImageNotFoundError
from app.services.common_frame import FrameImage, frame_wcs
from app.services.spectral import (
    aperture_photometry,
    calibration_key,
    parse_wcs_wave_tail,
    wavelength_at,
)
from app.services.spherex_flags import (
    DEFAULT_BITS,
    bits_from_header,
    contamination_mask,
    decode,
    fraction_by_flag,
)

FIXTURES = Path(__file__).parent / "fixtures"


def real_image_header() -> fits.Header:
    return fits.Header.fromstring((FIXTURES / "spherex_d3_0116_image_header.txt").read_text(), sep="\n")


def real_flags_header() -> fits.Header:
    return fits.Header.fromstring((FIXTURES / "spherex_d3_0116_flags_header.txt").read_text(), sep="\n")


# --- wavelength ----------------------------------------------------------------
def test_wcs_wave_table_is_found_in_the_tail_of_the_file() -> None:
    table = parse_wcs_wave_tail((FIXTURES / "spherex_d3_0116_wcswave_tail.bin").read_bytes())
    assert table is not None
    assert table.header["EXTNAME"] == "WCS-WAVE"
    assert table.data["VALUES"][0].shape == (14, 9, 2)


def test_wavelength_at_the_cutout_centre_matches_the_official_method() -> None:
    table = parse_wcs_wave_tail((FIXTURES / "spherex_d3_0116_wcswave_tail.bin").read_bytes())
    wavelength, bandwidth = wavelength_at(real_image_header(), table, 14.0, 14.0)
    assert wavelength == pytest.approx(2.36218, abs=1e-4)
    assert bandwidth == pytest.approx(0.05848, abs=1e-4)
    # Inside the D3 range published by the SIA (em_min/em_max 1.6301-2.4346 um).
    assert 1.6301 <= wavelength <= 2.4346


def test_wavelength_changes_across_the_detector() -> None:
    """Linear variable filter: another pixel, another wavelength."""
    table = parse_wcs_wave_tail((FIXTURES / "spherex_d3_0116_wcswave_tail.bin").read_bytes())
    left = wavelength_at(real_image_header(), table, 0.0, 14.0)[0]
    right = wavelength_at(real_image_header(), table, 28.0, 14.0)[0]
    bottom = wavelength_at(real_image_header(), table, 14.0, 0.0)[0]
    assert len({round(left, 5), round(right, 5), round(bottom, 5)}) > 1


def test_garbage_tail_gives_no_table() -> None:
    assert parse_wcs_wave_tail(b"\0" * 8640) is None


def test_calibration_key_uses_detector_and_processing_run() -> None:
    url = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W19_1B/"
           "l2b-v27-2026-197/3/level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits")
    assert calibration_key(url, "D3") == "D3|l2b-v27-2026-197"


# --- flags ---------------------------------------------------------------------
def test_bits_read_from_the_real_flags_header_match_the_documentation() -> None:
    bits = bits_from_header(real_flags_header())
    for bit in (0, 1, 6, 17, 19, 21, 22, 25):
        assert bits[bit].name == DEFAULT_BITS[bit].name


def test_source_is_informational_not_contamination() -> None:
    source = 1 << 21
    cosmic_ray = 1 << 0
    flags = np.array([[0, source], [cosmic_ray, cosmic_ray | source]])
    assert contamination_mask(flags).tolist() == [[False, False], [True, True]]
    assert [b.name for b in decode(cosmic_ray | source)] == ["TRANSIENT", "SOURCE"]
    fractions = fraction_by_flag(flags, np.ones((2, 2), bool))
    assert fractions == {"TRANSIENT": 0.5, "SOURCE": 0.5}


# --- aperture photometry -----------------------------------------------------------
def synthetic_frame(side=13, peak=10.0, sky=2.0, flags_at_centre=0) -> FrameImage:
    yy, xx = np.mgrid[0:side, 0:side]
    c = (side - 1) / 2
    data = sky + peak * np.exp(-((xx - c) ** 2 + (yy - c) ** 2) / 2.0)
    flags = np.zeros((side, side), dtype=np.int64)
    flags[int(c), int(c)] = flags_at_centre
    return FrameImage(
        data=data, outside=np.zeros((side, side), bool), wcs=frame_wcs(10, 20, side, 6.15),
        pixel_scale_arcsec=6.15,
        extras={"flags": flags, "variance": np.full((side, side), 0.04)},
        center_source_xy=(100.0, 200.0),
    )


def test_aperture_photometry_removes_the_local_background() -> None:
    point = aperture_photometry(synthetic_frame(), radius_px=1.5)
    assert point["background"] == pytest.approx(2.0, abs=0.01)
    assert point["flux"] > 3.0  # excess of the "star" over the sky
    expected_err = np.sqrt(0.04 * point["n_pixels"]) / point["n_pixels"]
    assert point["flux_err"] == pytest.approx(expected_err, abs=1e-6)  # rounded to 6 decimals
    assert point["flags_value"] == 0


def test_aperture_reports_flags_inside_the_aperture() -> None:
    point = aperture_photometry(synthetic_frame(flags_at_centre=1), radius_px=1.5)
    assert point["flags_value"] == 1


# --- service: quality and spectrum ----------------------------------------------------
def test_quality_requires_the_image_first(service_factory) -> None:
    from conftest import FakeTransport, votable_response

    service = service_factory(FakeTransport([votable_response()]))
    observation = service.search(133.795129, -7.245147, 5.0).observations[0]
    with pytest.raises(ImageNotFoundError):
        service.quality(observation.id)


def test_spectrum_is_sorted_by_wavelength_and_flags_bad_points(service_factory, monkeypatch) -> None:
    from conftest import FakeTransport, votable_response

    service = service_factory(FakeTransport([votable_response()]))
    observations = service.search(133.795129, -7.245147, 1.2).observations
    waves = {o.id: 1.0 + i for i, o in enumerate(reversed(observations))}
    flagged_id = observations[0].id

    def fake_frame(observation_id):
        entry = service._entry(observation_id)
        return synthetic_frame(flags_at_centre=1 if observation_id == flagged_id else 0), entry

    monkeypatch.setattr(service, "search", lambda *a, **k: type("R", (), {
        "observations": observations, "data_source": "live"})())
    monkeypatch.setattr(service, "get_frame", fake_frame)
    monkeypatch.setattr(service, "_wavelength_for", lambda entry, frame: (waves[entry.observation_id], 0.05))

    spectrum = service.spectrum(133.795129, -7.245147, aperture_arcsec=9.0, max_exposures=60)

    lambdas = [p["wavelength_um"] for p in spectrum["points"]]
    assert lambdas == sorted(lambdas) and len(lambdas) == len(observations)
    bad = [p for p in spectrum["points"] if p["flagged"]]
    assert [p["observation_id"] for p in bad] == [flagged_id]
    assert bad[0]["flags"] == ["TRANSIENT"]
    assert spectrum["unit"] == "MJy/sr"
