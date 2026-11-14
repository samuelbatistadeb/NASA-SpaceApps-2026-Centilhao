"""Tests of the cutout strategy."""

from __future__ import annotations

from app.services.cutout_service import CutoutRequest, CutoutStrategy
from app.services.irsa_client import IrsaClient

from conftest import (
    SYNTHETIC_CUTOUT_URL,
    SYNTHETIC_SIA2_URL,
    FakeTransport,
    fits_response,
)


# --- Cutout strategy -----------------------------------------------------------
def make_cutout_service(transport: FakeTransport, settings, cutout_url: str = ""):
    """Build the cutout service under test."""
    from app.services.cutout_service import CutoutService

    client = IrsaClient(
        sia2_base_url=SYNTHETIC_SIA2_URL,
        cutout_base_url=cutout_url,
        transport=transport,
        sleep=lambda _seconds: None,
    )
    return CutoutService(client, settings)


def test_strategy_is_local_when_the_service_is_not_configured(settings) -> None:
    """Without the cutout service the local download must be used."""
    service = make_cutout_service(FakeTransport(), settings)

    strategy = service.decide_strategy(
        CutoutRequest(cutout_service_ref="synthetic-service-ref")
    )

    assert strategy is CutoutStrategy.LOCAL_DOWNLOAD


def test_strategy_is_remote_when_the_service_is_referenced(settings) -> None:
    """A configured service referenced by the record must be used."""
    service = make_cutout_service(
        FakeTransport(), settings, cutout_url=SYNTHETIC_CUTOUT_URL
    )

    strategy = service.decide_strategy(
        CutoutRequest(cutout_service_ref="synthetic-service-ref")
    )

    assert strategy is CutoutStrategy.REMOTE_CUTOUT


def test_strategy_is_local_when_the_record_does_not_reference_the_service(
    settings,
) -> None:
    """A configured service without a reference in the record stays unused."""
    service = make_cutout_service(
        FakeTransport(), settings, cutout_url=SYNTHETIC_CUTOUT_URL
    )

    strategy = service.decide_strategy(CutoutRequest(cutout_service_ref=None))

    assert strategy is CutoutStrategy.LOCAL_DOWNLOAD


def test_local_cutout_extracts_the_plane(settings) -> None:
    """The local strategy must download the file and cut it."""
    transport = FakeTransport([fits_response()])
    service = make_cutout_service(transport, settings)

    result = service.build_cutout(
        CutoutRequest(
            product_id="synthetic-product-001",
            access_url="https://synthetic-irsa.invalid/files/synthetic-product-001.fits",
            ra_deg=133.795129,
            dec_deg=-7.245147,
            fov_arcmin=1.0,
        )
    )

    assert result.strategy is CutoutStrategy.LOCAL_DOWNLOAD
    assert result.data.ndim == 2
    assert result.metadata["cutout_strategy"] == "local_download"
    assert transport.requests[0]["method"] == "GET"


def test_remote_cutout_uses_the_service(settings) -> None:
    """The remote strategy must ask the cutout service."""
    transport = FakeTransport([fits_response()])
    service = make_cutout_service(
        transport, settings, cutout_url=SYNTHETIC_CUTOUT_URL
    )

    result = service.build_cutout(
        CutoutRequest(
            product_id="synthetic-product-001",
            access_url="https://synthetic-irsa.invalid/files/synthetic-product-001.fits",
            ra_deg=32.0,
            dec_deg=32.0,
            fov_arcmin=1.0,
            cutout_service_ref="synthetic-service-ref",
        )
    )

    assert result.strategy is CutoutStrategy.REMOTE_CUTOUT
    assert result.metadata["cutout_center_source"] == "remote_cutout_service"
    assert transport.requests[0]["url"].startswith(SYNTHETIC_CUTOUT_URL)
