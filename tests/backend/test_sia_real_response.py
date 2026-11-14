"""Tests against a REAL answer of the IRSA SIA v2 service (no network).

The fixture ``fixtures/sia_spherex_dr1_wise0855.xml`` is an authentic answer,
saved unchanged on 2026-11-14 from::

    https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1
        &POS=circle+133.795129+-7.245147+0.01&RESPONSEFORMAT=votable&MAXREC=5

It contains 5 SPHEREx DR1 Level 2 products around WISE 0855. The first row
is the same product as the local file
``level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits`` (MJD-OBS
60800.700028461, DATE-OBS 2025-05-05T16:48:02.459).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.irsa_client import HttpResponse, extract_detector
from conftest import FakeTransport

FIXTURE = Path(__file__).parent / "fixtures" / "sia_spherex_dr1_wise0855.xml"

WISE0855_RA = 133.795129
WISE0855_DEC = -7.245147

#: DATE-OBS read from the header of the real FITS file of the first row.
FIRST_PRODUCT_DATE_OBS = datetime(2025, 5, 5, 16, 48, 2, 459000, tzinfo=timezone.utc)


@pytest.fixture
def real_sia_response() -> HttpResponse:
    return HttpResponse(
        status_code=200,
        content=FIXTURE.read_bytes(),
        headers={"content-type": "application/x-votable+xml"},
        url="https://irsa.ipac.caltech.edu/SIA",
    )


def _search(service_factory, response):
    service = service_factory(FakeTransport([response]))
    return service.search(WISE0855_RA, WISE0855_DEC, 1.0)


def test_real_votable_is_parsed(service_factory, real_sia_response) -> None:
    service = service_factory(FakeTransport([real_sia_response]))
    records = service._client._parse_sia2_payload(real_sia_response)

    assert len(records) == 5
    for record in records:
        assert record["obs_collection"] == "spherex_dr1"
        assert record["access_url"].startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/")
        assert isinstance(record["t_min"], float)


def test_epoch_comes_from_t_min_mjd(service_factory, real_sia_response) -> None:
    response = _search(service_factory, real_sia_response)

    assert response.total_observations == 5
    first = response.observations[0]
    assert first.metadata.timing_status == "mjd_observation_date"
    assert first.metadata.observed_at_source == "60800.700028"
    # t_min is rounded to 1e-6 d (~0.09 s) in the SIA answer.
    delta = abs((first.observed_at - FIRST_PRODUCT_DATE_OBS).total_seconds())
    assert delta < 1.0


def test_release_date_is_never_used_as_epoch(service_factory, real_sia_response) -> None:
    response = _search(service_factory, real_sia_response)

    for observation in response.observations:
        assert observation.observed_at is not None
        assert observation.observed_at.year == 2025  # release date is 2026-09-27
        assert observation.metadata.timing_status == "mjd_observation_date"


def test_observations_are_chronological(service_factory, real_sia_response) -> None:
    response = _search(service_factory, real_sia_response)
    instants = [item.observed_at for item in response.observations]

    assert instants == sorted(instants)
    assert len(set(instants)) == 3  # 3 distinct exposures, 2 of them seen by D3+D6


def test_detector_is_read_from_the_product(service_factory, real_sia_response) -> None:
    response = _search(service_factory, real_sia_response)

    detectors = [item.detector for item in response.observations]
    assert set(detectors) == {"D3", "D6"}
    assert "SPHEREx" not in detectors


def test_access_url_belongs_to_the_same_product(service_factory, real_sia_response) -> None:
    response = _search(service_factory, real_sia_response)

    for observation in response.observations:
        did = observation.metadata.product_id
        url = observation.metadata.original_file_url
        exposure, detector = did.split("?", 1)[1].split("/")
        assert f"level2_{exposure}{detector}_" in url
        assert f"/{detector[1:]}/" in url


def test_wavelength_is_published_in_nm(service_factory, real_sia_response) -> None:
    # em_min/em_max come in metres (FIELD unit="m"): 1.63010e-06 m, 2.43460e-06 m.
    response = _search(service_factory, real_sia_response)
    first = response.observations[0]

    assert first.metadata.wavelength_min_nm == pytest.approx(1630.1)
    assert first.metadata.wavelength_max_nm == pytest.approx(2434.6)


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"obs_publisher_did": "ivo://irsa.ipac/spherex_dr1?2025W19_1B_0116_1/D3"}, "D3"),
        ({"energy_bandpassname": "SPHEREx-D6"}, "D6"),
        ({"detector_name": "synthetic-detector-1", "obs_publisher_did": "x/D2"}, "synthetic-detector-1"),
        ({"instrument_name": "SPHEREx"}, None),
        ({}, None),
    ],
)
def test_extract_detector(record, expected) -> None:
    assert extract_detector(record) == expected
