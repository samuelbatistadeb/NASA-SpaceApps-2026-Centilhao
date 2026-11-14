"""Tests of the image endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.observations import get_observation_service
from app.main import app

from conftest import FakeTransport, fits_response, votable_response


def make_client(service_factory, transport: FakeTransport) -> TestClient:
    """Build a client bound to a service backed by the fake transport."""
    service = service_factory(transport)
    app.dependency_overrides[get_observation_service] = lambda: service
    return TestClient(app)


def test_image_of_a_known_observation_is_returned_as_png(service_factory) -> None:
    """The processed image must be a real PNG."""
    transport = FakeTransport([votable_response(), fits_response()])
    client = make_client(service_factory, transport)
    try:
        response = client.get(
            "/api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5"
        )
        assert response.status_code == 200
        observation_id = response.json()["observations"][0]["id"]

        image = client.get(f"/api/images/{observation_id}")
    finally:
        app.dependency_overrides.clear()

    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(image.content) > 1000
    assert image.headers["x-spherex-image-type"] == "visual-representation"
    assert "percentile stretch" in image.headers["x-spherex-normalization"]


def test_image_of_an_unknown_observation_is_not_found(service_factory) -> None:
    """An unknown observation must produce ``IMAGE_NOT_FOUND``."""
    client = make_client(service_factory, FakeTransport())
    try:
        response = client.get("/api/images/obs_0000000000000000")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "IMAGE_NOT_FOUND"


def test_image_of_a_broken_product_is_a_processing_error(service_factory) -> None:
    """A file that cannot be processed must produce ``PROCESSING_ERROR``."""
    from app.services.irsa_client import HttpResponse

    broken = HttpResponse(
        status_code=200,
        content=b"this is not a FITS file",
        headers={"content-type": "application/fits"},
        url="https://synthetic-irsa.invalid/files/synthetic-product-001.fits",
    )
    transport = FakeTransport([votable_response(), broken])
    client = make_client(service_factory, transport)
    try:
        response = client.get(
            "/api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5"
        )
        observation_id = response.json()["observations"][0]["id"]

        image = client.get(f"/api/images/{observation_id}")
    finally:
        app.dependency_overrides.clear()

    assert image.status_code == 500
    assert image.json()["error"]["code"] == "PROCESSING_ERROR"
