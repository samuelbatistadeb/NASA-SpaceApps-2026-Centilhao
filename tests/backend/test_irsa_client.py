"""Tests of the IRSA client (query construction, retry and error translation)."""

from __future__ import annotations

import httpx
import pytest

from app.api.errors import MalformedResponseError, SourceUnavailableError
from app.services.irsa_client import (
    IRSA_CUTOUT_BASE_URL,
    IRSA_SIA2_BASE_URL,
    IrsaClient,
    radius_from_fov,
)

from conftest import (
    SYNTHETIC_SIA2_URL,
    FakeTransport,
    build_synthetic_json,
    build_synthetic_votable,
    fits_response,
    json_response,
    votable_response,
)


def make_client(transport: FakeTransport, **kwargs) -> IrsaClient:
    """Build a client that uses the fake transport."""
    options = {
        "sia2_base_url": SYNTHETIC_SIA2_URL,
        "transport": transport,
        "sleep": lambda _seconds: None,
    }
    options.update(kwargs)
    return IrsaClient(**options)


def test_endpoint_constants_are_empty_until_verified() -> None:
    """The addresses must stay empty until the researcher confirms them."""
    assert IRSA_SIA2_BASE_URL == ""
    assert IRSA_CUTOUT_BASE_URL == ""


def test_query_without_configured_endpoint_is_unavailable() -> None:
    """An unconfigured source must raise, never return fabricated data."""
    client = make_client(FakeTransport(), sia2_base_url="")
    with pytest.raises(SourceUnavailableError):
        client.query_by_position(10.0, 20.0, 0.1)


def test_query_sends_the_expected_parameters() -> None:
    """The query must carry the position, the size and the user agent."""
    transport = FakeTransport([votable_response()])
    client = make_client(transport, timeout=17.0)

    client.query_by_position(133.795129, -7.245147, radius_from_fov(5.0))

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request["method"] == "GET"
    assert request["url"].startswith(SYNTHETIC_SIA2_URL)
    assert "CIRCLE" in request["params"]["POS"]
    assert "133.795129" in request["params"]["POS"]
    assert "-7.245147" in request["params"]["POS"]
    assert request["params"]["SIZE"].endswith("arcsec")
    assert request["headers"]["User-Agent"].startswith("SPHERExExplorer")
    assert request["timeout"] == 17.0


def test_query_parses_a_synthetic_votable() -> None:
    """A VOTable answer must be converted into flat records."""
    transport = FakeTransport([votable_response()])
    client = make_client(transport)

    records = client.query_by_position(133.795129, -7.245147, 0.05)

    assert len(records) == 3
    assert records[0]["obs_publisher_did"] == "synthetic-product-002"
    assert records[0]["access_url"].startswith("https://synthetic-irsa.invalid/")


def test_query_parses_a_synthetic_json_answer() -> None:
    """A JSON answer must be accepted as well."""
    payload = build_synthetic_json(
        [{"obs_publisher_did": "synthetic-json-product", "access_url": "https://x.invalid/a.fits"}]
    )
    transport = FakeTransport([json_response(payload)])
    client = make_client(transport)

    records = client.query_by_position(10.0, 20.0, 0.05)

    assert records == [
        {
            "obs_publisher_did": "synthetic-json-product",
            "access_url": "https://x.invalid/a.fits",
        }
    ]


def test_empty_answer_returns_no_records() -> None:
    """An empty answer is an empty list, not an error."""
    transport = FakeTransport([votable_response(b"")])
    client = make_client(transport)

    assert client.query_by_position(10.0, 20.0, 0.05) == []


def test_malformed_answer_is_reported() -> None:
    """An unreadable payload must raise a dedicated error."""
    transport = FakeTransport([votable_response(b"<not-a-votable")])
    client = make_client(transport)

    with pytest.raises(MalformedResponseError):
        client.query_by_position(10.0, 20.0, 0.05)


def test_timeout_is_translated_to_source_unavailable() -> None:
    """A timeout must be published as an unavailable source."""
    transport = FakeTransport([httpx.ConnectTimeout("timed out")])
    client = make_client(transport)

    with pytest.raises(SourceUnavailableError):
        client.query_by_position(10.0, 20.0, 0.05)


def test_connection_error_is_translated_to_source_unavailable() -> None:
    """A connection error must be published as an unavailable source."""
    transport = FakeTransport([httpx.ConnectError("no route")])
    client = make_client(transport)

    with pytest.raises(SourceUnavailableError):
        client.query_by_position(10.0, 20.0, 0.05)


def test_server_error_is_retried() -> None:
    """A transient failure must be retried before giving up."""
    transport = FakeTransport(
        [
            votable_response(status=503),
            votable_response(status=500),
            votable_response(),
        ]
    )
    client = make_client(transport, max_attempts=3)

    records = client.query_by_position(10.0, 20.0, 0.05)

    assert len(records) == 3
    assert len(transport.requests) == 3


def test_server_error_after_retries_is_unavailable() -> None:
    """A persistent failure must end as an unavailable source."""
    transport = FakeTransport([votable_response(status=503)] * 3)
    client = make_client(transport, max_attempts=3)

    with pytest.raises(SourceUnavailableError):
        client.query_by_position(10.0, 20.0, 0.05)

    assert len(transport.requests) == 3


def test_client_error_is_not_retried() -> None:
    """A 4xx answer must not be repeated."""
    transport = FakeTransport([votable_response(status=404)])
    client = make_client(transport, max_attempts=3)

    with pytest.raises(SourceUnavailableError):
        client.query_by_position(10.0, 20.0, 0.05)

    assert len(transport.requests) == 1


def test_download_rejects_an_unsupported_scheme() -> None:
    """Only http(s) addresses may be downloaded."""
    client = make_client(FakeTransport())

    with pytest.raises(SourceUnavailableError):
        client.download_fits("file:///etc/passwd")


def test_download_rejects_an_unknown_host_when_restricted() -> None:
    """A host outside the allowed list must be refused."""
    client = make_client(
        FakeTransport(), allowed_download_hosts=("irsa.ipac.caltech.edu",)
    )

    with pytest.raises(SourceUnavailableError):
        client.download_fits("https://unexpected.invalid/file.fits")


def test_download_uses_the_configured_data_base_url() -> None:
    """A relative address must be resolved against the configured base."""
    transport = FakeTransport([fits_response()])
    client = make_client(transport, data_base_url="https://synthetic-irsa.invalid/data")

    content = client.download_fits("files/synthetic-product-001.fits")

    assert content
    assert transport.requests[0]["url"] == (
        "https://synthetic-irsa.invalid/data/files/synthetic-product-001.fits"
    )


def test_cutout_without_configured_service_is_unavailable() -> None:
    """The cutout service must refuse to work when it is not configured."""
    client = make_client(FakeTransport(), cutout_base_url="")

    with pytest.raises(SourceUnavailableError):
        client.fetch_cutout(10.0, 20.0, 60.0)


def test_radius_from_fov_covers_the_field() -> None:
    """The search radius must cover the whole field of view."""
    radius = radius_from_fov(60.0)
    assert radius == pytest.approx(0.7071067811865475, rel=1e-6)
