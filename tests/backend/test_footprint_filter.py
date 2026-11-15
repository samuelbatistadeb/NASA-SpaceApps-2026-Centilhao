"""Tests of the footprint pre-filter (DECISÃO 007, item 6).

The polygon ``REAL_S_REGION`` is copied unchanged from the first row of the
real SIA answer saved in ``fixtures/sia_spherex_dr1_wise0855.xml``. The other
polygons are synthetic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.api.errors import NoObservationsFoundError
from app.services.observation_service import ObservationService
from app.services.sky_coverage import parse_s_region, polygon_contains_position
from app.services.irsa_client import HttpResponse
from conftest import FakeTransport

REAL_FIXTURE = Path(__file__).parent / "fixtures" / "sia_spherex_dr1_wise0855.xml"

REAL_S_REGION = (
    "POLYGON ICRS 133.24990295057214 -6.792366530370936 "
    "136.573730639645 -7.893897878777517 "
    "135.6087246915983 -11.252283174147388 "
    "132.22997686194108 -10.127262014271603 "
    "133.24990295057214 -6.792366530370936"
)

#: 2 x 2 degree synthetic square centred on (10, 0).
SQUARE = [(9.0, -1.0), (11.0, -1.0), (11.0, 1.0), (9.0, 1.0)]


def test_real_polygon_is_parsed_without_the_closing_vertex() -> None:
    vertices = parse_s_region(REAL_S_REGION)

    assert vertices is not None
    assert len(vertices) == 4
    assert vertices[0] == pytest.approx((133.24990295057214, -6.792366530370936))


@pytest.mark.parametrize(
    "text",
    [None, "", 42, "CIRCLE ICRS 10 0 1", "POLYGON ICRS 1 2 3", "POLYGON ICRS 1 2 3 4", "POLYGON 1 2 x 4 5 6"],
)
def test_unreadable_region_gives_none(text) -> None:
    assert parse_s_region(text) is None


def test_frame_token_is_optional() -> None:
    assert parse_s_region("POLYGON 9 -1 11 -1 11 1 9 1") == SQUARE


@pytest.mark.parametrize(
    ("ra_deg", "dec_deg", "expected"),
    [
        (10.0, 0.0, True),
        (10.9, 0.9, True),
        (11.1, 0.0, False),
        (10.0, 1.1, False),
        (8.9, -0.9, False),
        (190.0, 0.0, False),  # antipodal side: vertices cannot be projected
    ],
)
def test_position_inside_or_outside_a_square(ra_deg, dec_deg, expected) -> None:
    assert polygon_contains_position(SQUARE, ra_deg, dec_deg) is expected


def test_vertex_order_does_not_matter() -> None:
    assert polygon_contains_position(list(reversed(SQUARE)), 10.0, 0.0) is True


def test_polygon_across_ra_zero() -> None:
    square = [(359.0, -1.0), (1.0, -1.0), (1.0, 1.0), (359.0, 1.0)]

    assert polygon_contains_position(square, 0.2, 0.0) is True
    assert polygon_contains_position(square, 359.8, 0.0) is True
    assert polygon_contains_position(square, 2.0, 0.0) is False


def test_polygon_around_the_pole() -> None:
    cap = [(0.0, 88.0), (90.0, 88.0), (180.0, 88.0), (270.0, 88.0)]

    assert polygon_contains_position(cap, 45.0, 89.5) is True
    assert polygon_contains_position(cap, 45.0, 85.0) is False


def test_real_footprint_contains_a_position_well_inside_it() -> None:
    vertices = parse_s_region(REAL_S_REGION)

    # Mean of the 4 corners: necessarily inside a convex detector footprint.
    assert polygon_contains_position(vertices, 134.4155, -9.0165) is True
    assert polygon_contains_position(vertices, 130.0, -9.0) is False


def test_filter_keeps_records_without_region_and_drops_non_covering_ones() -> None:
    records = [
        {"obs_id": "covers", "s_region": "POLYGON ICRS 9 -1 11 -1 11 1 9 1"},
        {"obs_id": "edge-only", "s_region": "POLYGON ICRS 11.5 -1 13.5 -1 13.5 1 11.5 1"},
        {"obs_id": "no-region"},
        {"obs_id": "unreadable", "s_region": "CIRCLE ICRS 10 0 1"},
    ]

    kept = ObservationService._filter_by_footprint(records, 10.0, 0.0)

    assert [record["obs_id"] for record in kept] == ["covers", "no-region", "unreadable"]


def test_search_fails_when_no_product_covers_the_position(service_factory) -> None:
    # Real SIA answer (5 products around WISE 0855) served for a position
    # ~4 degrees away, outside every published footprint.
    response = HttpResponse(
        status_code=200,
        content=REAL_FIXTURE.read_bytes(),
        headers={"content-type": "application/x-votable+xml"},
        url="https://irsa.ipac.caltech.edu/SIA",
    )
    service = service_factory(FakeTransport([response]))

    with pytest.raises(NoObservationsFoundError):
        service.search(130.0, -9.0, 5.0)
