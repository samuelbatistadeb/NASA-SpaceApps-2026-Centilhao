"""Concurrency guards for product requests (no network, SYNTHETIC data)."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Mapping

from app.services.irsa_client import HttpResponse, IrsaClient

from conftest import (
    SYNTHETIC_HOST,
    SYNTHETIC_SIA2_URL,
    FakeTransport,
    build_synthetic_fits,
    votable_response,
)

IBE_URL = f"https://{SYNTHETIC_HOST}/ibe/data/spherex/synthetic/{{}}.fits"


class SlowCountingTransport:
    """Thread-safe transport that answers a FITS after a delay and counts overlap."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self.calls = 0
        self._lock = threading.Lock()
        self._fits = build_synthetic_fits()

    def request(self, method: str, url: str, *, params: Mapping[str, Any] | None = None,
                headers=None, timeout=None, max_bytes=None, stop_when=None) -> HttpResponse:
        with self._lock:
            self.calls += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(self.delay)
        with self._lock:
            self.active -= 1
        return HttpResponse(200, self._fits, {"content-type": "application/fits"}, url)


def test_simultaneous_cutouts_are_limited() -> None:
    transport = SlowCountingTransport()
    client = IrsaClient(
        sia2_base_url=SYNTHETIC_SIA2_URL,
        transport=transport,
        max_concurrent_product_requests=2,
        sleep=lambda _s: None,
    )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(
            lambda i: client.fetch_ibe_cutout(IBE_URL.format(i), 10.0, 20.0, 0.02),
            range(8),
        ))

    assert transport.calls == 8
    assert transport.max_active == 2


def test_downloads_share_the_same_limit() -> None:
    transport = SlowCountingTransport()
    client = IrsaClient(
        sia2_base_url=SYNTHETIC_SIA2_URL,
        transport=transport,
        max_concurrent_product_requests=1,
        sleep=lambda _s: None,
    )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: client.download_fits(f"https://{SYNTHETIC_HOST}/f{i}.fits"), range(4)))

    assert transport.max_active == 1


def test_same_image_requested_in_parallel_is_built_once(service_factory) -> None:
    """Main viewer + thumbnail asking the same observation must cost one cutout."""
    search_transport = FakeTransport([votable_response()])
    service = service_factory(search_transport)
    observation = service.search(133.795129, -7.245147, 1.0).observations[0]

    slow = SlowCountingTransport(delay=0.1)
    service._client._transport = slow  # same client used by the cutout service

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _i: service.get_image(observation.id), range(5)))

    assert slow.calls == 1
    assert len({r.content for r in results}) == 1
    assert results[0].content.startswith(b"\x89PNG")
