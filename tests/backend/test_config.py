"""Tests of the application configuration."""

from __future__ import annotations

import pytest

from app.core.config import (
    DEFAULT_CORS_ORIGINS,
    ENV_ALLOWED_DOWNLOAD_HOSTS,
    ENV_CUTOUT_MODE,
    ENV_IRSA_SIA2_URL,
    VERIFIED_IRSA_SIA_URL,
    ConfigurationError,
    Settings,
    get_settings,
)


def test_default_settings_use_the_verified_sia_endpoint() -> None:
    """Without configuration the verified IRSA SIA v2 endpoint is used."""
    settings = Settings.from_env(env={})
    assert settings.irsa_sia2_base_url == VERIFIED_IRSA_SIA_URL
    assert settings.irsa_sia2_configured is True
    # IRSA has no standalone cutout service (IBE cutouts use the access_url).
    assert settings.irsa_cutout_base_url == ""
    assert settings.irsa_cutout_configured is False
    assert settings.allowed_download_hosts == ("irsa.ipac.caltech.edu",)


def test_allowed_download_hosts_can_be_overridden() -> None:
    settings = Settings.from_env(
        env={ENV_ALLOWED_DOWNLOAD_HOSTS: "a.example.invalid, b.example.invalid"}
    )
    assert settings.allowed_download_hosts == ("a.example.invalid", "b.example.invalid")


def test_settings_read_prefixed_environment_variables() -> None:
    """The ``SPHEREX_`` variables must be read from the environment."""
    settings = Settings.from_env(
        env={
            ENV_IRSA_SIA2_URL: "https://example.invalid/sia2",
            "SPHEREX_HTTP_TIMEOUT_SECONDS": "12.5",
            "SPHEREX_HTTP_MAX_ATTEMPTS": "5",
            "SPHEREX_MAX_FOV_ARCMIN": "45",
            "SPHEREX_MIN_FOV_ARCMIN": "0.5",
            "SPHEREX_CACHE_TTL_SECONDS": "120",
            ENV_CUTOUT_MODE: "local",
            "SPHEREX_CORS_ORIGINS": "http://localhost:9000, http://127.0.0.1:9000",
            "SPHEREX_PORT": "9001",
        }
    )
    assert settings.irsa_sia2_base_url == "https://example.invalid/sia2"
    assert settings.irsa_sia2_configured is True
    assert settings.http_timeout_seconds == 12.5
    assert settings.http_max_attempts == 5
    assert settings.max_fov_arcmin == 45.0
    assert settings.min_fov_arcmin == 0.5
    assert settings.cache_ttl_seconds == 120
    assert settings.cutout_mode == "local"
    assert settings.cors_origins == ("http://localhost:9000", "http://127.0.0.1:9000")
    assert settings.port == 9001


def test_default_cors_origins_are_localhost_only() -> None:
    """The development CORS list must only contain localhost origins."""
    settings = Settings.from_env(env={})
    assert settings.cors_origins == DEFAULT_CORS_ORIGINS
    for origin in settings.cors_origins:
        assert "localhost" in origin or "127.0.0.1" in origin


def test_invalid_fov_range_is_rejected() -> None:
    """An inverted field-of-view range must be refused."""
    with pytest.raises(ConfigurationError):
        Settings.from_env(
            env={"SPHEREX_MIN_FOV_ARCMIN": "10", "SPHEREX_MAX_FOV_ARCMIN": "1"}
        )


def test_invalid_cutout_mode_is_rejected() -> None:
    """An unknown cutout mode must be refused."""
    with pytest.raises(ConfigurationError):
        Settings.from_env(env={ENV_CUTOUT_MODE: "magic"})


def test_get_settings_is_cached() -> None:
    """The settings must be created only once per process."""
    assert get_settings() is get_settings()
