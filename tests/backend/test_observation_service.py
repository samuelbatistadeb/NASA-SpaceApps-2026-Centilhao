"""Tests of the orchestration service (ordering, mapping and absence of data)."""

from __future__ import annotations

import pytest

from app.api.errors import InvalidParametersError, NoObservationsFoundError
from app.services.observation_service import ObservationService

from conftest import (
    SYNTHETIC_VOTABLE_ROWS,
    FakeTransport,
    build_synthetic_votable,
    votable_response,
)


def build_service(transport: FakeTransport, service_factory) -> ObservationService:
    """Build the service under test."""
    return service_factory(transport)


def test_observations_are_sorted_chronologically(
    service_factory: object,
) -> None:
    """The sequence must start on the oldest observation."""
    transport = FakeTransport([votable_response()])
    service = service_factory(transport)

    response = service.search(133.795129, -7.245147, 5.0)

    assert response.total_observations == 3
    timestamps = [item.observed_at for item in response.observations]
    assert timestamps[0] is not None and timestamps[1] is not None
    assert timestamps[0] < timestamps[1]
    assert response.observations[0].metadata.product_id == "synthetic-product-001"
    assert response.observations[1].metadata.product_id == "synthetic-product-002"


def test_observation_without_date_is_kept_last_and_null(service_factory: object) -> None:
    """An observation without a resolvable date must not receive an invented one."""
    transport = FakeTransport([votable_response()])
    service = service_factory(transport)

    response = service.search(133.795129, -7.245147, 5.0)

    last = response.observations[-1]
    assert last.observed_at is None
    assert last.metadata.timing_status == "unresolved"
    assert last.metadata.observed_at_source is None


def test_record_is_mapped_to_the_contract_schema(service_factory: object) -> None:
    """The published fields must come from the archive record."""
    transport = FakeTransport([votable_response()])
    service = service_factory(transport)

    response = service.search(133.795129, -7.245147, 5.0)

    observation = response.observations[0]
    assert observation.id.startswith("obs_")
    assert observation.band == "synthetic-band-a"
    assert observation.detector == "synthetic-detector-1"
    assert observation.image_url == f"/api/images/{observation.id}"
    assert observation.metadata.product_id == "synthetic-product-001"
    assert observation.metadata.quality == 0.8
    assert observation.metadata.timing_status == "mjd_observation_date"
    assert observation.metadata.observed_at_source == "59000.250000"
    assert observation.metadata.instrument == "synthetic-instrument"
    assert observation.metadata.exposure_time_s == 280.0
    assert observation.metadata.wavelength_min_nm == 0.9
    assert observation.metadata.source == "synthetic-archive"
    assert observation.metadata.original_file_url.endswith("synthetic-product-001.fits")
    assert "percentile stretch" in (observation.metadata.visual_normalization or "")


def test_missing_fields_stay_null(service_factory: object) -> None:
    """Fields that the archive does not publish must remain ``None``."""
    transport = FakeTransport([votable_response()])
    service = service_factory(transport)

    response = service.search(133.795129, -7.245147, 5.0)

    third = response.observations[2]
    assert third.metadata.quality is None
    assert third.metadata.exposure_time_s is None
    assert third.metadata.wavelength_min_nm is None
    assert third.metadata.data_release is None


def test_without_results_the_service_raises(service_factory: object) -> None:
    """An empty answer must be reported as 'no observation found'."""
    transport = FakeTransport([votable_response(b"")])
    service = service_factory(transport)

    with pytest.raises(NoObservationsFoundError):
        service.search(133.795129, -7.245147, 5.0)


def test_duplicated_products_are_merged(service_factory: object) -> None:
    """The same product must not be repeated in the sequence."""
    row = SYNTHETIC_VOTABLE_ROWS[1]
    payload = build_synthetic_votable([row, dict(row)])
    transport = FakeTransport([votable_response(payload)])
    service = service_factory(transport)

    response = service.search(133.795129, -7.245147, 5.0)

    assert response.total_observations == 1
    assert response.observations[0].metadata.duplicate_count == 1


def test_observation_id_is_deterministic(service_factory: object) -> None:
    """The identifier of an observation must be stable between queries."""
    transport = FakeTransport([votable_response(), votable_response()])
    service = service_factory(transport)

    first = service.search(133.795129, -7.245147, 5.0)
    second = service.search(133.795129, -7.245147, 5.0)

    assert [item.id for item in first.observations] == [
        item.id for item in second.observations
    ]


def test_repeated_query_uses_the_cache(service_factory: object) -> None:
    """The second identical query must not reach the archive again."""
    transport = FakeTransport([votable_response()])
    service = service_factory(transport)

    service.search(133.795129, -7.245147, 5.0)
    service.search(133.795129, -7.245147, 5.0)

    assert len(transport.requests) == 1


def test_field_of_view_outside_the_limits_is_refused(service_factory: object) -> None:
    """A field of view outside the configured range must be refused."""
    transport = FakeTransport()
    service = service_factory(transport)

    with pytest.raises(InvalidParametersError):
        service.search(133.795129, -7.245147, 10_000.0)


def test_coordinates_outside_the_limits_are_refused(service_factory: object) -> None:
    """Invalid coordinates must be refused before any query."""
    transport = FakeTransport()
    service = service_factory(transport)

    with pytest.raises(InvalidParametersError):
        service.search(400.0, -7.245147, 5.0)
    with pytest.raises(InvalidParametersError):
        service.search(133.795129, 95.0, 5.0)
