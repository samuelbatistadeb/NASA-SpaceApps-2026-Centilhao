"""Tests of the IBE cutout (``<access_url>?center=..&size=..``), without network.

The addresses use the reserved ``.invalid`` domain with an IBE-like path; the
FITS payload is the SYNTHETIC file of ``conftest.py``.
"""

from __future__ import annotations

import pytest

from app.api.errors import ImageNotFoundError, SourceUnavailableError
from app.core.config import Settings
from app.services.cutout_service import CutoutRequest, CutoutService, CutoutStrategy
from app.services.irsa_client import HttpResponse, IrsaClient

from conftest import SYNTHETIC_HOST, SYNTHETIC_SIA2_URL, FakeTransport, fits_response

IBE_URL = f"https://{SYNTHETIC_HOST}/ibe/data/spherex/dr1/level2/synthetic/3/synthetic_D3.fits"


def make_client(transport: FakeTransport, **kwargs) -> IrsaClient:
    options = {
        "sia2_base_url": SYNTHETIC_SIA2_URL,
        "transport": transport,
        "sleep": lambda _seconds: None,
    }
    options.update(kwargs)
    return IrsaClient(**options)


def text_response(status: int, body: bytes = b"") -> HttpResponse:
    return HttpResponse(status_code=status, content=body, headers={"content-type": "text/plain"})


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (IBE_URL, True),
        ("https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/x.fits", True),
        (f"https://{SYNTHETIC_HOST}/files/synthetic-product-001.fits", False),
        ("http://irsa.ipac.caltech.edu/ibe/data/x.fits", False),  # https only
        (None, False),
        ("", False),
    ],
)
def test_supports_ibe_cutout(url, expected) -> None:
    assert IrsaClient.supports_ibe_cutout(url) is expected


def test_ibe_cutout_appends_center_and_size_to_the_access_url() -> None:
    transport = FakeTransport([fits_response()])
    client = make_client(transport)

    content = client.fetch_ibe_cutout(IBE_URL, 133.795129, -7.245147, 0.02)

    assert content
    request = transport.requests[0]
    assert request["method"] == "GET"
    assert request["url"] == IBE_URL
    assert request["params"] == {"center": "133.795129,-7.245147d", "size": "0.020000"}
    assert request["max_bytes"] == client.max_fits_bytes


@pytest.mark.parametrize("status", [422, 500])
def test_no_overlap_is_image_not_found_and_not_retried(status) -> None:
    transport = FakeTransport([text_response(status, b"Arrays do not overlap.")])
    client = make_client(transport, max_attempts=3)

    with pytest.raises(ImageNotFoundError):
        client.fetch_ibe_cutout(IBE_URL, 10.0, 20.0, 0.02)

    assert len(transport.requests) == 1


def test_server_busy_is_retried() -> None:
    transport = FakeTransport(
        [text_response(503, b"Server busy, retry later."), fits_response()]
    )
    client = make_client(transport, max_attempts=3)

    assert client.fetch_ibe_cutout(IBE_URL, 10.0, 20.0, 0.02)
    assert len(transport.requests) == 2


def test_ibe_cutout_respects_the_allowed_hosts() -> None:
    client = make_client(FakeTransport(), allowed_download_hosts=("irsa.ipac.caltech.edu",))

    with pytest.raises(SourceUnavailableError):
        client.fetch_ibe_cutout(IBE_URL, 10.0, 20.0, 0.02)


def test_non_ibe_address_is_refused() -> None:
    client = make_client(FakeTransport())

    with pytest.raises(SourceUnavailableError):
        client.fetch_ibe_cutout(f"https://{SYNTHETIC_HOST}/files/a.fits", 10.0, 20.0, 0.02)


def test_auto_mode_uses_the_ibe_cutout(tmp_path) -> None:
    transport = FakeTransport([fits_response()])
    settings = Settings(cache_dir=tmp_path, irsa_sia2_base_url=SYNTHETIC_SIA2_URL)
    service = CutoutService(make_client(transport), settings)
    request = CutoutRequest(
        product_id="synthetic-product-001",
        access_url=IBE_URL,
        ra_deg=133.795129,
        dec_deg=-7.245147,
        fov_arcmin=1.2,
    )

    assert service.decide_strategy(request) is CutoutStrategy.REMOTE_CUTOUT
    result = service.build_cutout(request)

    assert result.strategy is CutoutStrategy.REMOTE_CUTOUT
    assert result.metadata["cutout_center_source"] == "ibe_cutout"
    assert result.data.ndim == 2
    sent = transport.requests[0]
    assert sent["url"] == IBE_URL
    assert sent["params"]["size"] == "0.020000"  # 1.2 arcmin = 0.02 deg


def test_local_mode_keeps_the_full_download(tmp_path) -> None:
    settings = Settings(
        cache_dir=tmp_path, irsa_sia2_base_url=SYNTHETIC_SIA2_URL, cutout_mode="local"
    )
    service = CutoutService(make_client(FakeTransport()), settings)

    strategy = service.decide_strategy(CutoutRequest(access_url=IBE_URL))

    assert strategy is CutoutStrategy.LOCAL_DOWNLOAD
