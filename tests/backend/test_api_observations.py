"""Tests of the public API with the FastAPI ``TestClient``.

Every payload used here is SYNTHETIC (see ``conftest.py``). No test touches
the network.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.observations import get_observation_service
from app.main import app

from conftest import FakeTransport, votable_response


@pytest.fixture
def client_factory(service_factory):
    """Build a ``TestClient`` bound to a service backed by a fake transport."""

    def factory(transport: FakeTransport) -> TestClient:
        service = service_factory(transport)
        app.dependency_overrides[get_observation_service] = lambda: service
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()


def test_health_reports_the_service_status(client_factory) -> None:
    """The health check must answer without any scientific content."""
    client = client_factory(FakeTransport())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_observations_with_results(client_factory) -> None:
    """A successful query must follow the contract of the API."""
    transport = FakeTransport([votable_response()])
    client = client_factory(transport)

    response = client.get(
        "/api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["target"] == {"ra_deg": 133.795129, "dec_deg": -7.245147}
    assert payload["query"] == {"fov_arcmin": 5.0}
    assert payload["total_observations"] == 3
    assert len(payload["observations"]) == 3

    first = payload["observations"][0]
    assert first["id"].startswith("obs_")
    assert first["image_url"] == f"/api/images/{first['id']}"
    assert first["metadata"]["product_id"] == "synthetic-product-001"
    assert first["observed_at"] is not None
    assert payload["observations"][-1]["observed_at"] is None


def test_observations_without_results(client_factory) -> None:
    """An empty answer must produce the documented error."""
    transport = FakeTransport([votable_response(b"")])
    client = client_factory(transport)

    response = client.get(
        "/api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5"
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NO_OBSERVATIONS_FOUND"
    assert "error" in body and "message" in body["error"]


@pytest.mark.parametrize(
    "query",
    [
        "ra_deg=400&dec_deg=-7.245147&fov_arcmin=5",
        "ra_deg=133.795129&dec_deg=95&fov_arcmin=5",
        "ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=0",
        "ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=100000",
        "ra_deg=abc&dec_deg=-7.245147&fov_arcmin=5",
    ],
)
def test_observations_with_invalid_parameters(client_factory, query: str) -> None:
    """Invalid parameters must produce ``INVALID_PARAMETERS``."""
    transport = FakeTransport()
    client = client_factory(transport)

    response = client.get(f"/api/observations?{query}")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PARAMETERS"
    assert transport.requests == []


def test_observations_with_a_filter_that_is_not_validated(client_factory) -> None:
    """A filter that is not scientifically validated must be refused."""
    transport = FakeTransport()
    client = client_factory(transport)

    response = client.get(
        "/api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5&band=synthetic"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PARAMETERS"
    assert transport.requests == []


def test_observations_with_an_unavailable_source(client_factory) -> None:
    """A failure of the source must produce ``SOURCE_UNAVAILABLE``."""
    transport = FakeTransport([httpx.ConnectTimeout("timed out")])
    client = client_factory(transport)

    response = client.get(
        "/api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5"
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SOURCE_UNAVAILABLE"


def test_observations_without_a_configured_source(tmp_path) -> None:
    """Without a configured endpoint the source must be reported as unavailable."""
    from app.core.config import Settings
    from app.services.cache import DiskCache
    from app.services.cutout_service import CutoutService
    from app.services.irsa_client import IrsaClient
    from app.services.observation_service import ObservationService

    local_settings = Settings(cache_dir=tmp_path / "cache")
    client = IrsaClient(sia2_base_url="", transport=FakeTransport())
    cache = DiskCache(local_settings.cache_dir, local_settings.cache_ttl_seconds)
    service = ObservationService(
        client, cache, CutoutService(client, local_settings), local_settings
    )
    app.dependency_overrides[get_observation_service] = lambda: service
    try:
        response = TestClient(app).get(
            "/api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SOURCE_UNAVAILABLE"


def test_unknown_observation_image_is_not_found(client_factory) -> None:
    """An unknown observation must produce ``IMAGE_NOT_FOUND``."""
    client = client_factory(FakeTransport())

    response = client.get("/api/images/obs_0000000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "IMAGE_NOT_FOUND"
