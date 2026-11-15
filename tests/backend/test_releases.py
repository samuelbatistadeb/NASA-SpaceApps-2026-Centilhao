"""Tests of the configurable SPHEREx collections and ``GET /api/releases``.

No network: the SIA self-description comes either from the real answer saved
on 2026-11-14 (``fixtures/sia_spherex_dr1_wise0855.xml``) or from a SYNTHETIC
VOTable written below; HTTP goes through :class:`FakeTransport`.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.releases import (
    SOURCE_CONFIG,
    SOURCE_DISCOVERED,
    SOURCE_FALLBACK,
    CollectionResolver,
    build_resolver,
    filter_image_collections,
    get_collection_resolver,
)
from app.core.config import (
    DEFAULT_SPHEREX_COLLECTIONS,
    DEFAULT_SPHEREX_HIPS_BASE,
    ConfigurationError,
    Settings,
    get_settings,
)
from app.main import app
from app.services.irsa_client import IrsaClient, parse_sia_collection_options

from conftest import SYNTHETIC_SIA2_URL, FakeTransport, votable_response

REAL_SIA_ANSWER = Path(__file__).parent / "fixtures" / "sia_spherex_dr1_wise0855.xml"

#: SYNTHETIC self-description: invented collection names for the tests.
SYNTHETIC_SELF_DESCRIPTION = b"""<?xml version="1.0" encoding="utf-8"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
  <RESOURCE type="meta" utype="adhoc:this">
    <GROUP name="inputParams">
      <PARAM name="COLLECTION" datatype="char" arraysize="*" value="">
        <VALUES type="actual">
          <OPTION value="synthetic_other"/>
          <OPTION value="spherex_dr9"/>
          <OPTION value="spherex_dr9_cube"/>
          <OPTION value="spherex_dr9_deep"/>
          <OPTION value="spherex_qr9"/>
        </VALUES>
      </PARAM>
    </GROUP>
  </RESOURCE>
</VOTABLE>
"""


def _client(transport: FakeTransport, **kwargs) -> IrsaClient:
    return IrsaClient(
        sia2_base_url=SYNTHETIC_SIA2_URL,
        transport=transport,
        sleep=lambda _s: None,
        **kwargs,
    )


# --- configuration -------------------------------------------------------------
def test_default_collections_are_the_four_verified_ones() -> None:
    settings = Settings.from_env({})
    assert settings.spherex_collections == DEFAULT_SPHEREX_COLLECTIONS
    assert settings.discover_collections is False
    assert settings.hips_base_url == DEFAULT_SPHEREX_HIPS_BASE

    transport = FakeTransport([votable_response()])
    _client(transport).query_by_position(133.0, -7.0, 0.01)
    assert transport.requests[0]["params"]["COLLECTION"] == list(DEFAULT_SPHEREX_COLLECTIONS)


def test_explicit_env_list_is_sent_to_the_sia() -> None:
    settings = Settings.from_env(
        {"SPHEREX_COLLECTIONS": " spherex_dr2 , spherex_dr2_deep,spherex_dr2 "}
    )
    assert settings.spherex_collections == ("spherex_dr2", "spherex_dr2_deep")
    assert settings.discover_collections is False
    assert build_resolver(settings).current().source == SOURCE_CONFIG

    transport = FakeTransport([votable_response()])
    _client(transport, collections=settings.spherex_collections).query_by_position(
        133.0, -7.0, 0.01
    )
    assert transport.requests[0]["params"]["COLLECTION"] == ["spherex_dr2", "spherex_dr2_deep"]


def test_auto_enables_discovery_and_keeps_default_as_fallback() -> None:
    settings = Settings.from_env(
        {"SPHEREX_COLLECTIONS": "AUTO", "SPHEREX_HIPS_BASE": "https://hips.invalid/D"}
    )
    assert settings.discover_collections is True
    assert settings.spherex_collections == DEFAULT_SPHEREX_COLLECTIONS
    assert settings.hips_base_url == "https://hips.invalid/D"


def test_invalid_collection_name_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env({"SPHEREX_COLLECTIONS": "spherex_dr1&MAXREC=1"})


# --- self-description parsing and image filter --------------------------------
def test_real_sia_answer_advertises_the_spherex_collections() -> None:
    options = parse_sia_collection_options(REAL_SIA_ANSWER.read_bytes())
    spherex = [name for name in options if name.startswith("spherex")]
    assert spherex == [
        "spherex_dr1",
        "spherex_dr1_cube",
        "spherex_dr1_deep",
        "spherex_qr3",
        "spherex_qr3_deep",
    ]
    # The All-Sky Cube is not a per-observation image.
    assert sorted(filter_image_collections(options)) == sorted(DEFAULT_SPHEREX_COLLECTIONS)


def test_client_lists_collections_with_maxrec_zero() -> None:
    transport = FakeTransport([votable_response(SYNTHETIC_SELF_DESCRIPTION)])
    names = _client(transport).list_sia_collections()
    assert transport.requests[0]["params"] == {"MAXREC": 0}
    assert names[0] == "synthetic_other"
    assert filter_image_collections(names) == ["spherex_dr9", "spherex_dr9_deep", "spherex_qr9"]


# --- discovery -----------------------------------------------------------------
def test_discovery_ok_is_used_by_the_client_and_cached() -> None:
    transport = FakeTransport([votable_response(SYNTHETIC_SELF_DESCRIPTION)])
    discovery = _client(transport)
    now = [1_000.0]
    resolver = CollectionResolver(
        discover=True, fetch=discovery.list_sia_collections, ttl_seconds=60, clock=lambda: now[0]
    )

    state = resolver.current()
    assert state.source == SOURCE_DISCOVERED
    assert state.collections == ("spherex_dr9", "spherex_dr9_deep", "spherex_qr9")
    assert state.discovered_at is not None

    resolver.current()
    assert len(transport.requests) == 1  # cached inside the TTL

    query_transport = FakeTransport([votable_response()])
    _client(query_transport, collections=resolver.collections).query_by_position(1.0, 2.0, 0.01)
    assert query_transport.requests[0]["params"]["COLLECTION"] == list(state.collections)

    now[0] += 61
    resolver.current()
    assert len(transport.requests) == 2  # refreshed after the TTL


@pytest.mark.parametrize(
    "answer",
    [
        votable_response(b"<html>502 Proxy Error</html>", status=502),
        httpx.ConnectError("synthetic offline"),
        votable_response(b"<VOTABLE/>"),  # no COLLECTION parameter
    ],
)
def test_discovery_failure_falls_back_to_the_default_list(answer) -> None:
    transport = FakeTransport([answer])
    resolver = CollectionResolver(discover=True, fetch=_client(transport).list_sia_collections)

    state = resolver.current()
    assert state.source == SOURCE_FALLBACK
    assert state.collections == DEFAULT_SPHEREX_COLLECTIONS
    assert state.discovered_at is None


def test_failure_after_success_keeps_the_last_discovered_list() -> None:
    answers = iter([["spherex_dr9"], OSError("synthetic offline")])

    def fetch():
        item = next(answers)
        if isinstance(item, Exception):
            raise item
        return item

    now = [0.0]
    resolver = CollectionResolver(discover=True, fetch=fetch, ttl_seconds=10, clock=lambda: now[0])
    assert resolver.current().collections == ("spherex_dr9",)
    now[0] = 11
    state = resolver.current()
    assert (state.source, state.collections) == (SOURCE_DISCOVERED, ("spherex_dr9",))


def test_no_image_collection_advertised_falls_back() -> None:
    resolver = CollectionResolver(discover=True, fetch=lambda: ["spherex_dr1_cube", "other"])
    assert resolver.current().source == SOURCE_FALLBACK


# --- cache key ------------------------------------------------------------------
def test_query_signature_changes_with_the_collection_list() -> None:
    transport = FakeTransport()
    default = _client(transport)
    same = _client(transport, collections=list(reversed(DEFAULT_SPHEREX_COLLECTIONS)))
    other = _client(transport, collections=["spherex_dr2"])

    assert default.query_signature == same.query_signature
    assert default.query_signature != other.query_signature
    assert default.query_signature.startswith(SYNTHETIC_SIA2_URL)


# --- endpoint ---------------------------------------------------------------------
def test_releases_endpoint_reports_the_state() -> None:
    resolver = CollectionResolver(
        discover=True, fetch=lambda: ["spherex_dr9", "spherex_dr9_cube"], clock=lambda: 0.0
    )
    app.dependency_overrides[get_collection_resolver] = lambda: resolver
    app.dependency_overrides[get_settings] = lambda: Settings(hips_base_url="https://hips.invalid/D")
    try:
        body = TestClient(app).get("/api/releases").json()
    finally:
        app.dependency_overrides.clear()

    assert body == {
        "collections": ["spherex_dr9"],
        "source": "discovered",
        "discovered_at": "1970-01-01T00:00:00+00:00",
        "hips_base": "https://hips.invalid/D",
    }


def test_releases_endpoint_default_configuration() -> None:
    app.dependency_overrides[get_collection_resolver] = lambda: build_resolver(Settings())
    app.dependency_overrides[get_settings] = lambda: Settings()
    try:
        response = TestClient(app).get("/api/releases")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "collections": list(DEFAULT_SPHEREX_COLLECTIONS),
        "source": "config",
        "discovered_at": None,
        "hips_base": DEFAULT_SPHEREX_HIPS_BASE,
    }


def test_query_cache_key_changes_with_the_collections(service_factory) -> None:
    """A new data release must never be answered from the cache of the old one."""
    from conftest import FakeTransport

    service = service_factory(FakeTransport())
    before = service._query_cache_key(10.0, 20.0, 3.0)
    service._client._collections_source = ("spherex_dr2",)
    assert service._query_cache_key(10.0, 20.0, 3.0) != before
