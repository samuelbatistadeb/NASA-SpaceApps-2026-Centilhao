"""Simple disk cache for the query answers and the generated images.

The MVP does not use a database (``docs/architecture/system.md`` section 12).
Two namespaces are kept inside the cache directory:

* ``queries``: the raw records returned by the archive, serialised as JSON.
* ``images``: the PNG generated for an observation.
* ``observations``: the resolved record of an observation, so that the image
  endpoint can find the product even after the process was restarted.

Entries expire after ``SPHEREX_CACHE_TTL_SECONDS``. Manual invalidation is
done by deleting the cache directory.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Cache namespaces.
NAMESPACE_QUERIES = "queries"
NAMESPACE_IMAGES = "images"
NAMESPACE_OBSERVATIONS = "observations"


class DiskCache:
    """File based cache with a time to live."""

    def __init__(self, directory: Path | str, ttl_seconds: int = 3600) -> None:
        self.directory = Path(directory)
        self.ttl_seconds = int(ttl_seconds)

    # -- helpers ----------------------------------------------------------------
    @staticmethod
    def make_key(*parts: Any) -> str:
        """Return a stable key for the given parts."""
        canonical = "|".join("" if part is None else str(part) for part in parts)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def path(self, namespace: str, key: str) -> Path:
        """Return the file that stores an entry."""
        return self.directory / namespace / f"{key}.bin"

    def _ensure_directory(self, namespace: str) -> Path:
        target = self.directory / namespace
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _is_expired(self, path: Path) -> bool:
        """Tell whether an entry is older than the configured time to live.

        A time to live of zero (or less) disables the cache: every entry is
        considered expired.
        """
        if self.ttl_seconds <= 0:
            return True
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:  # pragma: no cover - defensive
            return True
        return age > self.ttl_seconds

    # -- JSON -------------------------------------------------------------------
    def get_json(self, namespace: str, key: str, *, allow_stale: bool = False) -> Any | None:
        """Return a cached JSON payload, or ``None`` when missing or expired.

        ``allow_stale`` ignores the time to live (used as a fallback when the
        archive is unavailable, and for immutable entries).
        """
        entry = self.get_json_entry(namespace, key)
        if entry is None:
            return None
        payload, _created_at, expired = entry
        if expired and not allow_stale:
            return None
        return payload

    def get_json_entry(self, namespace: str, key: str) -> tuple[Any, float, bool] | None:
        """Return ``(payload, created_at, expired)`` or ``None`` when missing."""
        path = self.path(namespace, key)
        if not path.exists():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # pragma: no cover - defensive
            return None
        if not isinstance(envelope, dict) or "payload" not in envelope:
            return None
        created_at = float(envelope.get("created_at") or path.stat().st_mtime)
        return envelope["payload"], created_at, self._is_expired(path)

    def set_json(self, namespace: str, key: str, payload: Any) -> None:
        """Store a JSON payload in the cache."""
        self._ensure_directory(namespace)
        envelope = {"created_at": time.time(), "payload": payload}
        path = self.path(namespace, key)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(envelope), encoding="utf-8")
        os.replace(temporary, path)

    # -- bytes ------------------------------------------------------------------
    def get_bytes(self, namespace: str, key: str, *, allow_stale: bool = False) -> bytes | None:
        """Return cached binary content, or ``None`` when missing or expired."""
        path = self.path(namespace, key)
        if not path.exists():
            return None
        if not allow_stale and self._is_expired(path):
            return None
        try:
            return path.read_bytes()
        except OSError:  # pragma: no cover - defensive
            return None

    def set_bytes(self, namespace: str, key: str, payload: bytes) -> None:
        """Store binary content in the cache."""
        self._ensure_directory(namespace)
        path = self.path(namespace, key)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, path)
