"""Contingency when IRSA is unavailable: expired cache is served and flagged."""

from __future__ import annotations

import os
import time

import pytest

from app.api.errors import SourceUnavailableError
from app.services.cache import NAMESPACE_QUERIES

from conftest import FakeTransport, votable_response


def expire_all(cache_dir) -> None:
    old = time.time() - 10 * 24 * 3600
    for root, _dirs, files in os.walk(cache_dir):
        for name in files:
            os.utime(os.path.join(root, name), (old, old))


def test_live_then_cached_then_stale_when_irsa_is_down(service_factory, tmp_path) -> None:
    transport = FakeTransport([votable_response()])
    service = service_factory(transport, http_max_attempts=1)

    first = service.search(133.795129, -7.245147, 5.0)
    assert first.data_source == "live" and first.data_cached_at is None

    second = service.search(133.795129, -7.245147, 5.0)
    assert second.data_source == "cache"
    assert len(transport.requests) == 1

    expire_all(tmp_path / "cache" / NAMESPACE_QUERIES)
    transport.queue(votable_response(status=502))
    stale = service.search(133.795129, -7.245147, 5.0)

    assert stale.data_source == "stale_cache"
    assert stale.data_cached_at is not None
    assert [o.id for o in stale.observations] == [o.id for o in first.observations]


def test_without_any_cache_the_outage_is_reported(service_factory) -> None:
    service = service_factory(FakeTransport([votable_response(status=502)]), http_max_attempts=1)
    with pytest.raises(SourceUnavailableError):
        service.search(133.795129, -7.245147, 5.0)
