"""Tests of the disk cache."""

from __future__ import annotations

from pathlib import Path

from app.services.cache import DiskCache


def test_cache_key_is_stable(tmp_path: Path) -> None:
    """The same query must always produce the same key."""
    first = DiskCache.make_key("query", "133.795129", "-7.245147", "5.000000")
    second = DiskCache.make_key("query", "133.795129", "-7.245147", "5.000000")

    assert first == second
    assert first != DiskCache.make_key("query", "133.795129", "-7.245147", "6.000000")


def test_json_entries_round_trip(tmp_path: Path) -> None:
    """A JSON payload must be stored and read back."""
    cache = DiskCache(tmp_path / "cache", ttl_seconds=3600)

    cache.set_json("queries", "key", [{"product_id": "synthetic-product-001"}])

    assert cache.get_json("queries", "key") == [
        {"product_id": "synthetic-product-001"}
    ]


def test_binary_entries_round_trip(tmp_path: Path) -> None:
    """A binary payload must be stored and read back."""
    cache = DiskCache(tmp_path / "cache", ttl_seconds=3600)

    cache.set_bytes("images", "key", b"\x89PNG\r\n\x1a\n")

    assert cache.get_bytes("images", "key").startswith(b"\x89PNG")


def test_expired_entries_are_ignored(tmp_path: Path) -> None:
    """An entry older than the time to live must not be used."""
    cache = DiskCache(tmp_path / "cache", ttl_seconds=0)

    cache.set_json("queries", "key", [{"product_id": "synthetic-product-001"}])

    assert cache.get_json("queries", "key") is None


def test_missing_entries_return_none(tmp_path: Path) -> None:
    """An unknown key must not raise."""
    cache = DiskCache(tmp_path / "cache", ttl_seconds=3600)

    assert cache.get_json("queries", "missing") is None
    assert cache.get_bytes("images", "missing") is None
