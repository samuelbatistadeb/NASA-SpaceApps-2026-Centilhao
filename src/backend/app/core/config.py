"""Application configuration for the SPHEREx Explorer backend.

Every setting is read from environment variables using the ``SPHEREX_`` prefix.
No credential is stored in the source code: if a service ever requires a secret,
it must be provided through an environment variable (a local ``.env`` file is
already ignored by git).

This module is the single place where the IRSA service addresses are read. The
SIA v2 endpoint ``https://irsa.ipac.caltech.edu/SIA`` was verified by real
queries (DECISÃO 007 and DECISÃO 009) and is the default. IRSA has no
standalone cutout service: cutouts are requested from the IBE address of each
product (``<access_url>?center=..&size=..``), so the cutout address stays empty
by default.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

logger = logging.getLogger(__name__)

#: Prefix used for every environment variable read by the backend.
ENV_PREFIX = "SPHEREX_"

# --- Named environment variables -------------------------------------------------
ENV_IRSA_SIA2_URL = "SPHEREX_IRSA_SIA2_URL"
ENV_IRSA_CUTOUT_URL = "SPHEREX_IRSA_CUTOUT_URL"
ENV_IRSA_DATA_BASE_URL = "SPHEREX_IRSA_DATA_BASE_URL"
ENV_HTTP_TIMEOUT = "SPHEREX_HTTP_TIMEOUT_SECONDS"
ENV_HTTP_MAX_ATTEMPTS = "SPHEREX_HTTP_MAX_ATTEMPTS"
ENV_USER_AGENT = "SPHEREX_USER_AGENT"
ENV_MAX_CUTOUT_PIXELS = "SPHEREX_MAX_CUTOUT_PIXELS"
ENV_MAX_FITS_BYTES = "SPHEREX_MAX_FITS_BYTES"
ENV_DEFAULT_CUTOUT_PIXELS = "SPHEREX_DEFAULT_CUTOUT_PIXELS"
ENV_MIN_FOV = "SPHEREX_MIN_FOV_ARCMIN"
ENV_MAX_FOV = "SPHEREX_MAX_FOV_ARCMIN"
ENV_CACHE_DIR = "SPHEREX_CACHE_DIR"
ENV_CACHE_TTL = "SPHEREX_CACHE_TTL_SECONDS"
ENV_CORS_ORIGINS = "SPHEREX_CORS_ORIGINS"
ENV_PORT = "SPHEREX_PORT"
ENV_CUTOUT_MODE = "SPHEREX_CUTOUT_MODE"
ENV_ALLOWED_DOWNLOAD_HOSTS = "SPHEREX_ALLOWED_DOWNLOAD_HOSTS"

#: SIA v2 endpoint of IRSA, verified on 2026-11-14 (DECISÃO 007 / 009).
VERIFIED_IRSA_SIA_URL = "https://irsa.ipac.caltech.edu/SIA"

#: Hosts from which scientific files may be downloaded (RNF-006).
DEFAULT_ALLOWED_DOWNLOAD_HOSTS: tuple[str, ...] = ("irsa.ipac.caltech.edu",)

#: Default user agent sent to IRSA. It identifies the project and the challenge.
DEFAULT_USER_AGENT = "SPHERExExplorer/0.1 (NASA Space Apps Challenge 2026)"

#: Default HTTP timeout (seconds) for a single request to IRSA.
DEFAULT_TIMEOUT_SECONDS = 30.0

#: Default number of attempts (1 = no retry) for transient failures.
DEFAULT_MAX_ATTEMPTS = 3

#: Default maximum size of a downloaded FITS file (512 MiB).
DEFAULT_MAX_FITS_BYTES = 512 * 1024 * 1024

#: Default maximum side (in pixels) of a locally produced cutout.
DEFAULT_MAX_CUTOUT_PIXELS = 2048

#: Default cutout side (in pixels) used when the pixel scale cannot be determined.
DEFAULT_DEFAULT_CUTOUT_PIXELS = 256

#: Application level (not scientific) field-of-view limits, in arcminutes.
DEFAULT_MIN_FOV_ARCMIN = 0.1
DEFAULT_MAX_FOV_ARCMIN = 120.0

#: Default cache lifetime, in seconds.
DEFAULT_CACHE_TTL_SECONDS = 3600

#: Cutout strategy: 'auto' (decide by configuration), 'remote' or 'local'.
DEFAULT_CUTOUT_MODE = "auto"

#: Accepted values of the cutout mode.
CUTOUT_MODES = ("auto", "remote", "local")

#: Localhost origins allowed by default (development only).
DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)

#: Repository root, used to build the default cache directory.
REPO_ROOT = Path(__file__).resolve().parents[4]

#: Default cache directory, following ``docs/architecture/system.md`` section 9.
DEFAULT_CACHE_DIR = REPO_ROOT / "data" / "cache" / "spherex"


class ConfigurationError(RuntimeError):
    """Raised when an environment variable holds an unusable value."""


def _load_dotenv() -> None:
    """Load a local ``.env`` file when python-dotenv is available.

    The file is optional and is ignored by git. Failures are non fatal: the
    process simply relies on the real environment.
    """
    try:  # pragma: no cover - depends on the local environment
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    env_file = REPO_ROOT / ".env"
    if env_file.exists():  # pragma: no cover - depends on the local environment
        load_dotenv(env_file, override=False)


def _get_str(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _get_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ConfigurationError(f"{name} must be a number, got {raw!r}") from exc


def _get_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Runtime configuration of the backend.

    Attributes are immutable; a new instance is created by :meth:`from_env`.
    """

    # --- IRSA services ---
    irsa_sia2_base_url: str = VERIFIED_IRSA_SIA_URL
    irsa_cutout_base_url: str = ""
    irsa_data_base_url: str = ""
    allowed_download_hosts: tuple[str, ...] = DEFAULT_ALLOWED_DOWNLOAD_HOSTS

    # --- HTTP behaviour ---
    http_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    http_max_attempts: int = DEFAULT_MAX_ATTEMPTS
    user_agent: str = DEFAULT_USER_AGENT

    # --- Processing guards ---
    max_cutout_pixels: int = DEFAULT_MAX_CUTOUT_PIXELS
    max_fits_bytes: int = DEFAULT_MAX_FITS_BYTES
    default_cutout_pixels: int = DEFAULT_DEFAULT_CUTOUT_PIXELS

    # --- Query limits (application level, not scientific) ---
    min_fov_arcmin: float = DEFAULT_MIN_FOV_ARCMIN
    max_fov_arcmin: float = DEFAULT_MAX_FOV_ARCMIN
    min_ra_deg: float = 0.0
    max_ra_deg: float = 360.0
    min_dec_deg: float = -90.0
    max_dec_deg: float = 90.0

    # --- Cache ---
    cache_dir: Path = field(default=DEFAULT_CACHE_DIR)
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS

    # --- Cutout strategy ---
    cutout_mode: str = DEFAULT_CUTOUT_MODE

    # --- Web server ---
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    port: int = 8000

    def validate(self) -> "Settings":
        """Check internal consistency and raise :class:`ConfigurationError`."""
        if self.min_fov_arcmin <= 0:
            raise ConfigurationError("min_fov_arcmin must be greater than zero")
        if self.max_fov_arcmin < self.min_fov_arcmin:
            raise ConfigurationError("max_fov_arcmin must be >= min_fov_arcmin")
        if self.http_timeout_seconds <= 0:
            raise ConfigurationError("http_timeout_seconds must be greater than zero")
        if self.http_max_attempts < 1:
            raise ConfigurationError("http_max_attempts must be >= 1")
        if self.max_fits_bytes <= 0:
            raise ConfigurationError("max_fits_bytes must be greater than zero")
        if self.default_cutout_pixels <= 0:
            raise ConfigurationError("default_cutout_pixels must be greater than zero")
        if self.max_cutout_pixels < self.default_cutout_pixels:
            raise ConfigurationError(
                "max_cutout_pixels must be >= default_cutout_pixels"
            )
        if not (0.0 <= self.min_ra_deg < self.max_ra_deg <= 360.0):
            raise ConfigurationError("invalid RA range")
        if not (-90.0 <= self.min_dec_deg <= self.max_dec_deg <= 90.0):
            raise ConfigurationError("invalid Dec range")
        if self.cutout_mode not in CUTOUT_MODES:
            raise ConfigurationError(
                f"cutout_mode must be one of {CUTOUT_MODES}, got {self.cutout_mode!r}"
            )
        return self

    @property
    def irsa_sia2_configured(self) -> bool:
        """Whether a SIA2 endpoint address is available."""
        return bool(self.irsa_sia2_base_url)

    @property
    def irsa_cutout_configured(self) -> bool:
        """Whether a cutout endpoint address is available."""
        return bool(self.irsa_cutout_base_url)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        """Build the settings from environment variables."""
        environment = os.environ if env is None else env

        raw_origins = environment.get(ENV_CORS_ORIGINS)
        if raw_origins and raw_origins.strip():
            origins = tuple(
                origin.strip()
                for origin in raw_origins.split(",")
                if origin.strip()
            )
        else:
            origins = DEFAULT_CORS_ORIGINS

        cache_dir_raw = environment.get(ENV_CACHE_DIR)
        cache_dir = (
            Path(cache_dir_raw).expanduser()
            if cache_dir_raw and cache_dir_raw.strip()
            else DEFAULT_CACHE_DIR
        )

        raw_hosts = environment.get(ENV_ALLOWED_DOWNLOAD_HOSTS)
        if raw_hosts and raw_hosts.strip():
            hosts = tuple(h.strip() for h in raw_hosts.split(",") if h.strip())
        else:
            hosts = DEFAULT_ALLOWED_DOWNLOAD_HOSTS

        settings = cls(
            irsa_sia2_base_url=_get_str(
                environment, ENV_IRSA_SIA2_URL, VERIFIED_IRSA_SIA_URL
            ),
            allowed_download_hosts=hosts,
            irsa_cutout_base_url=_get_str(environment, ENV_IRSA_CUTOUT_URL, ""),
            irsa_data_base_url=_get_str(environment, ENV_IRSA_DATA_BASE_URL, ""),
            http_timeout_seconds=_get_float(
                environment, ENV_HTTP_TIMEOUT, DEFAULT_TIMEOUT_SECONDS
            ),
            http_max_attempts=_get_int(
                environment, ENV_HTTP_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS
            ),
            user_agent=_get_str(environment, ENV_USER_AGENT, DEFAULT_USER_AGENT),
            max_cutout_pixels=_get_int(
                environment, ENV_MAX_CUTOUT_PIXELS, DEFAULT_MAX_CUTOUT_PIXELS
            ),
            max_fits_bytes=_get_int(
                environment, ENV_MAX_FITS_BYTES, DEFAULT_MAX_FITS_BYTES
            ),
            default_cutout_pixels=_get_int(
                environment, ENV_DEFAULT_CUTOUT_PIXELS, DEFAULT_DEFAULT_CUTOUT_PIXELS
            ),
            min_fov_arcmin=_get_float(
                environment, ENV_MIN_FOV, DEFAULT_MIN_FOV_ARCMIN
            ),
            max_fov_arcmin=_get_float(
                environment, ENV_MAX_FOV, DEFAULT_MAX_FOV_ARCMIN
            ),
            cache_dir=cache_dir,
            cache_ttl_seconds=_get_int(
                environment, ENV_CACHE_TTL, DEFAULT_CACHE_TTL_SECONDS
            ),
            cutout_mode=_get_str(environment, ENV_CUTOUT_MODE, DEFAULT_CUTOUT_MODE),
            cors_origins=origins,
            port=_get_int(environment, ENV_PORT, 8000),
        )
        return settings.validate()


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide settings, loading them on first use."""
    global _SETTINGS
    if _SETTINGS is None:
        _load_dotenv()
        _SETTINGS = Settings.from_env()
        if not _SETTINGS.irsa_sia2_configured:
            logger.warning(
                "%s is not configured: the API will answer SOURCE_UNAVAILABLE "
                "until the official IRSA endpoint is verified.",
                ENV_IRSA_SIA2_URL,
            )
    return _SETTINGS


def reset_settings_cache() -> None:
    """Forget the cached settings (used by tests)."""
    global _SETTINGS
    _SETTINGS = None
