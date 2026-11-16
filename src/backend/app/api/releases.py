"""SPHEREx data releases in use: which SIA collections are queried.

New SPHEREx data arrive often (weekly Quick Releases, then Data Releases), so
the collection list must be easy to update:

* ``SPHEREX_COLLECTIONS=a,b,c`` -- explicit list (``source = "config"``).
* unset -- the four verified collections (``source = "config"``).
* ``SPHEREX_COLLECTIONS=auto`` -- the list is discovered from the IRSA SIA v2
  self-description (``source = "discovered"``) and refreshed after
  ``SPHEREX_COLLECTIONS_DISCOVERY_TTL_SECONDS``. When discovery fails and
  nothing was discovered before, the default list is used
  (``source = "fallback"``): the app is never left without a source.

Image filter (:func:`filter_image_collections`): the SIA self-description
lists collection *names* only, without the product type, so the filter is by
name: ``spherex_<dr|qr><n>`` with an optional ``_deep`` suffix. This keeps the
Spectral Image MEFs (``spherex_dr1``, ``spherex_qr3``, ``spherex_dr1_deep``,
``spherex_qr3_deep``) and drops ``spherex_dr1_cube`` (DR1 All-Sky Cube, not a
per-observation image; SPHEREx Data Access documentation). FACT: those are the
names observed on 2026-11-14. HYPOTHESIS: future releases follow the same
pattern (e.g. ``spherex_dr2``); a different naming needs an explicit list.

``GET /api/releases`` publishes the state so the frontend knows the versions.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Callable, Iterable, Sequence

from fastapi import APIRouter, Depends

from app.api.errors import ApiError
from app.core.config import DEFAULT_SPHEREX_COLLECTIONS, Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["releases"])

#: Spectral Image collections of SPHEREx (see the module docstring).
IMAGE_COLLECTION_PATTERN = re.compile(r"^spherex_(dr|qr)\d+(_deep)?$", re.IGNORECASE)

#: After a failed discovery, wait this long (seconds) before trying again.
DISCOVERY_RETRY_SECONDS = 300.0

SOURCE_CONFIG = "config"
SOURCE_DISCOVERED = "discovered"
SOURCE_FALLBACK = "fallback"


def filter_image_collections(names: Iterable[str]) -> list[str]:
    """Keep only the SPHEREx Spectral Image collections, without duplicates."""
    kept = (name.strip() for name in names if name and name.strip())
    return list(dict.fromkeys(n for n in kept if IMAGE_COLLECTION_PATTERN.match(n)))


@dataclass(frozen=True)
class ReleaseState:
    """Collections in use and where they came from."""

    collections: tuple[str, ...]
    source: str
    discovered_at: datetime | None = None


class CollectionResolver:
    """Decide which SIA collections are queried (thread safe)."""

    def __init__(
        self,
        *,
        discover: bool,
        configured: Sequence[str] = DEFAULT_SPHEREX_COLLECTIONS,
        fetch: Callable[[], Sequence[str]] | None = None,
        ttl_seconds: float = 6 * 3600,
        retry_seconds: float = DISCOVERY_RETRY_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._configured = tuple(configured) or DEFAULT_SPHEREX_COLLECTIONS
        self._discover = bool(discover and fetch is not None)
        self._fetch = fetch
        self._ttl = float(ttl_seconds)
        self._retry = float(retry_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._state: ReleaseState | None = None
        self._next_attempt = 0.0

    def current(self) -> ReleaseState:
        """Return the state, discovering again when it expired."""
        if not self._discover:
            return ReleaseState(self._configured, SOURCE_CONFIG)
        with self._lock:
            if self._state is None or self._clock() >= self._next_attempt:
                self._refresh()
            assert self._state is not None
            return self._state

    def collections(self) -> tuple[str, ...]:
        """Collections in use (provider for :class:`IrsaClient`)."""
        return self.current().collections

    def _refresh(self) -> None:
        now = self._clock()
        try:
            found = filter_image_collections(self._fetch())  # type: ignore[misc]
            if not found:
                raise ValueError("no SPHEREx image collection advertised")
        except (ApiError, ValueError, OSError) as exc:
            self._next_attempt = now + self._retry
            if self._state is None or self._state.source != SOURCE_DISCOVERED:
                self._state = ReleaseState(self._configured, SOURCE_FALLBACK)
            logger.warning(
                "SPHEREx collection discovery failed (%s); using %s list",
                exc,
                self._state.source,
            )
            return
        self._next_attempt = now + self._ttl
        self._state = ReleaseState(
            tuple(found), SOURCE_DISCOVERED, datetime.fromtimestamp(now, tz=timezone.utc)
        )
        logger.info("SPHEREx collections discovered: %s", ", ".join(found))


def build_resolver(settings: Settings) -> CollectionResolver:
    """Build the resolver from the settings (discovery uses its own client)."""
    fetch: Callable[[], Sequence[str]] | None = None
    if settings.discover_collections:
        from app.services.irsa_client import IrsaClient

        discovery_client = IrsaClient(
            sia2_base_url=settings.irsa_sia2_base_url,
            timeout=settings.http_timeout_seconds,
            max_attempts=settings.http_max_attempts,
            user_agent=settings.user_agent,
        )
        fetch = discovery_client.list_sia_collections
    return CollectionResolver(
        discover=settings.discover_collections,
        configured=settings.spherex_collections,
        fetch=fetch,
        ttl_seconds=settings.collections_discovery_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_collection_resolver() -> CollectionResolver:
    """Process-wide resolver, built from the configuration."""
    return build_resolver(get_settings())


@router.get(
    "/releases",
    summary="SPHEREx data releases in use",
    description=(
        "SIA v2 collections queried by the backend, where the list came from "
        "(config, discovered or fallback) and the HiPS base used for the sky map."
    ),
)
def get_releases(
    resolver: CollectionResolver = Depends(get_collection_resolver),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Return the collections in use and the HiPS base address."""
    state = resolver.current()
    return {
        "collections": list(state.collections),
        "source": state.source,
        "discovered_at": state.discovered_at.isoformat() if state.discovered_at else None,
        "hips_base": settings.hips_base_url,
    }
