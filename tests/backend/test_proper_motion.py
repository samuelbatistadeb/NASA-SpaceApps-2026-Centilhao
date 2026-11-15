"""Proper-motion propagation (pendência 2): astrometry, service and API.

Reference values are the propagated positions published in
``docs/science/target-catalog.md`` (§3.1-§3.3), computed independently from
Gaia DR3 / the J2000 position, and an astropy cross-check.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.observations import get_observation_service
from app.main import app
from app.services.astrometry import ProperMotion, jyear_from_datetime, propagate_position

from conftest import FakeTransport, HttpResponse
from test_sia_real_response import FIXTURE, WISE0855_DEC, WISE0855_RA


def angular_sep_arcsec(ra1, dec1, ra2, dec2) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(min(1.0, cos_c))) * 3600.0


@pytest.mark.parametrize(
    ("ra", "dec", "pmra", "pmdec", "ref", "epoch", "expected_ra", "expected_dec"),
    [
        # WISE 0855: SIMBAD J2000 (Kirkpatrick et al. 2021) -> 2025.35 (§3.3, DECISÃO 019)
        (133.81890825, -7.247048, -8123.7, 673.2, 2000.0, 2025.35, 133.761244, -7.242304),
        # ...and -> 2010.3: lands on the AllWISE W2 source / discovery designation (~1")
        (133.81890825, -7.247048, -8123.7, 673.2, 2000.0, 2010.3, 133.795478, -7.245121),
        # Barnard, Gaia DR3 2016.0 -> 2025.60 (§3.1)
        (269.44850252543836, 4.739420051112412, -801.550978, 10362.394207, 2016.0, 2025.60,
         269.446358, 4.767053),
        # eps Indi A, Gaia DR3 2016.0 -> 2025.30 (§3.2)
        (330.8724078795965, -56.79725466122902, 3966.661, -2536.192, 2016.0, 2025.30,
         330.891121, -56.803806),
    ],
)
def test_propagation_matches_the_target_catalog(
    ra, dec, pmra, pmdec, ref, epoch, expected_ra, expected_dec
) -> None:
    got_ra, got_dec = propagate_position(ra, dec, ProperMotion(pmra, pmdec, ref), epoch)
    # The catalogue values are rounded to 1e-6 deg (0.0036").
    assert angular_sep_arcsec(got_ra, got_dec, expected_ra, expected_dec) < 0.03


def test_zero_interval_keeps_the_position() -> None:
    motion = ProperMotion(-8123.7, 673.2, 2025.35)
    assert propagate_position(133.737467, -7.240406, motion, 2025.35) == pytest.approx(
        (133.737467, -7.240406)
    )


def test_julian_year_of_known_instants() -> None:
    assert jyear_from_datetime(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)) == pytest.approx(2000.0)
    # First WISE 0855 product; reference: astropy Time("2025-05-05T16:48:02").jyear
    first = datetime(2025, 5, 5, 16, 48, 2, tzinfo=timezone.utc)
    assert jyear_from_datetime(first) == pytest.approx(2025.3420945192283, abs=1e-9)


def real_sia_response() -> HttpResponse:
    return HttpResponse(200, FIXTURE.read_bytes(), {"content-type": "application/x-votable+xml"})


WISE_MOTION = ProperMotion(-8123.7, 673.2, 2025.35)


def test_each_observation_is_cut_at_its_own_epoch(service_factory) -> None:
    service = service_factory(FakeTransport([real_sia_response()]))
    response = service.search(WISE0855_RA, WISE0855_DEC, 3.0, motion=WISE_MOTION)

    for item in response.observations:
        meta = item.metadata
        assert meta.position_source == "proper_motion"
        expected = propagate_position(
            WISE0855_RA, WISE0855_DEC, WISE_MOTION, jyear_from_datetime(item.observed_at)
        )
        assert (meta.cutout_center_ra_deg, meta.cutout_center_dec_deg) == pytest.approx(expected)
        entry = service._registry[item.id]
        assert (entry.ra_deg, entry.dec_deg) == pytest.approx(expected)

    # The fixture spans ~3.2 h on 2025-05-05: first and last centres differ.
    first, last = response.observations[0], response.observations[-1]
    assert first.metadata.cutout_center_ra_deg != last.metadata.cutout_center_ra_deg


def test_without_motion_the_requested_position_is_used(service_factory) -> None:
    service = service_factory(FakeTransport([real_sia_response()]))
    response = service.search(WISE0855_RA, WISE0855_DEC, 3.0)

    for item in response.observations:
        assert item.metadata.position_source == "requested"
        assert item.metadata.cutout_center_ra_deg == pytest.approx(WISE0855_RA)


def test_moving_target_query_is_centred_mid_survey_and_widened(service_factory) -> None:
    transport = FakeTransport([real_sia_response()])
    service = service_factory(transport)
    service.search(WISE0855_RA, WISE0855_DEC, 3.0, motion=WISE_MOTION)

    pos = transport.requests[0]["params"]["POS"].split()
    ra, dec, radius = float(pos[1]), float(pos[2]), float(pos[3])
    expected_ra, expected_dec = propagate_position(WISE0855_RA, WISE0855_DEC, WISE_MOTION, 2026.0)
    assert (ra, dec) == pytest.approx((expected_ra, expected_dec), abs=1e-6)
    # half-diagonal of 3' plus 8.15"/yr over 1.5 yr
    assert radius == pytest.approx(0.0353553 + 8151.5 * 1.5 / 3.6e6, abs=1e-5)


def test_ids_differ_between_different_queries(service_factory) -> None:
    service = service_factory(FakeTransport([real_sia_response(), real_sia_response()]))
    with_motion = service.search(WISE0855_RA, WISE0855_DEC, 3.0, motion=WISE_MOTION)
    without = service.search(WISE0855_RA, WISE0855_DEC, 3.0)

    assert {o.id for o in with_motion.observations}.isdisjoint(o.id for o in without.observations)


def test_api_requires_the_three_motion_parameters(service_factory) -> None:
    service = service_factory(FakeTransport([real_sia_response()]))
    app.dependency_overrides[get_observation_service] = lambda: service
    try:
        client = TestClient(app)
        base = {"ra_deg": WISE0855_RA, "dec_deg": WISE0855_DEC, "fov_arcmin": 3}
        partial = client.get("/api/observations", params={**base, "pm_dec_masyr": 673.2})
        assert partial.status_code == 400
        assert partial.json()["error"]["code"] == "INVALID_PARAMETERS"

        full = client.get(
            "/api/observations",
            params={**base, "pm_ra_cosdec_masyr": -8123.7, "pm_dec_masyr": 673.2,
                    "ref_epoch_jyear": 2025.35},
        )
        assert full.status_code == 200
        sources = {o["metadata"]["position_source"] for o in full.json()["observations"]}
        assert sources == {"proper_motion"}
    finally:
        app.dependency_overrides.pop(get_observation_service, None)


def test_targets_publish_their_proper_motion() -> None:
    targets = {t["name"]: t for t in TestClient(app).get("/api/targets").json()["targets"]}
    wise = targets["WISE 0855"]
    assert (wise["pm_ra_cosdec_masyr"], wise["pm_dec_masyr"], wise["ref_epoch_jyear"]) == (
        -8123.7, 673.2, 2025.35,
    )
    for target in targets.values():
        assert target["ref_epoch_jyear"] is not None
