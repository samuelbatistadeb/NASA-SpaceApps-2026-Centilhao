"""Client for the IRSA / IPAC services that archive the SPHEREx mission data.

.. warning::

   **The official service addresses are still PENDING VERIFICATION.**

   ``docs/science/data-sources.md`` states that the SIA2 endpoint, the cutout
   service and the download addresses have to be confirmed against the official
   IRSA documentation. Because of that, the module level constants below are
   intentionally **empty**: an empty address means "source not configured" and
   the client raises :class:`SourceUnavailableError`, which the API publishes as
   ``SOURCE_UNAVAILABLE``. The backend never queries an unverified address and
   never returns fictitious observations.

   Points to be completed once the researcher confirms the official addresses:

   * ``IRSA_SIA2_BASE_URL`` -- official SIA2 endpoint of the SPHEREx archive.
   * ``IRSA_CUTOUT_BASE_URL`` -- official cutout service of IRSA (if it exists).
   * ``IrsaClient._build_sia2_params`` -- exact accepted parameter names.
   * ``IrsaClient._build_cutout_params`` -- exact accepted cutout parameters.
   * ``IrsaClient._parse_sia2_payload`` -- real response format and column names.

The HTTP transport is injectable so that the test-suite never touches the
network.
"""

from __future__ import annotations

import io
import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlparse

import httpx
import numpy as np

from app.api.errors import (
    MalformedResponseError,
    SourceUnavailableError,
)

logger = logging.getLogger(__name__)

# --- Addresses pending verification by the researcher --------------------------
# TODO(RESEARCHER-PENDING): replace with the official IRSA addresses and
# document them in ``docs/science/data-sources.md``.
IRSA_SIA2_BASE_URL: str = ""
IRSA_CUTOUT_BASE_URL: str = ""

#: Default HTTP timeout, in seconds.
DEFAULT_TIMEOUT_SECONDS = 30.0
#: Default number of attempts for transient failures.
DEFAULT_MAX_ATTEMPTS = 3
#: Default user agent identifying the project.
DEFAULT_USER_AGENT = "SPHERExExplorer/0.1 (NASA Space Apps Challenge 2026)"

#: HTTP statuses that are worth a new attempt.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

#: Base delay (seconds) of the exponential backoff between attempts.
RETRY_BACKOFF_SECONDS = 1.0

#: Aliases used to read the standard IVOA/SHAPE columns of a SIA2 record.
#: The first alias found in the record wins; a missing column yields ``None``.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "product_id": (
        "obs_publisher_did",
        "product_key",
        "obs_id",
        "dataset_id",
        "product_id",
        "access_url",
    ),
    "access_url": ("access_url", "download_url", "url"),
    "access_format": ("access_format", "format"),
    "access_estsize": ("access_estsize", "file_size", "size_bytes"),
    "title": ("obs_title", "title"),
    "description": ("obs_description", "description"),
    "instrument": ("instrument_name", "instrument", "facility_name"),
    "detector": ("detector_name", "detector", "instrument_name"),
    "band": ("band_name", "band", "band_pass", "filter_name"),
    "band_units": ("band_units", "band_unit"),
    "em_min": ("em_min", "em_min_nm", "wavelength_min_nm", "spec_start"),
    "em_max": ("em_max", "em_max_nm", "wavelength_max_nm", "spec_end"),
    "mjd_obs": ("mjd-obs", "mjd_obs", "mjd_start", "mjd"),
    "t_min": ("t_min", "datestart", "date-obs", "date_obs", "datetime", "start_time"),
    "t_max": ("t_max", "dateend", "end_time"),
    "release_date": ("obs_release_date", "release_date", "data_release_date"),
    "quality": ("quality", "q", "quality_flag", "photom_quality"),
    "exposure": ("t_exptime", "exptime", "exposure_time", "t_exptime_s"),
    "pixel_scale": ("s_pixel_scale", "pixel_scale", "platescale"),
    "ra": ("s_ra", "ra", "ra_deg", "s_ra_deg"),
    "dec": ("s_dec", "dec", "dec_deg", "s_dec_deg"),
    "fov": ("s_fov", "fov", "s_fov_deg"),
    "provenance": ("provenance", "source", "orig_source", "publisher_id"),
    "data_rights": ("data_rights", "rights"),
    "contamination": ("contamination", "contamination_flag", "flags"),
    "wcs": ("wcs", "wcs_info"),
    "cutout_service_ref": ("cutout_service_ref", "service_ref", "cutout_service"),
    "data_release": ("data_release", "collection_name", "obs_collection"),
}


@dataclass(frozen=True)
class HttpResponse:
    """Minimal HTTP response returned by a transport."""

    status_code: int
    content: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)
    url: str = ""

    @property
    def text(self) -> str:
        """Decoded body, replacing undecodable bytes."""
        return self.content.decode("utf-8", errors="replace")

    @property
    def content_type(self) -> str:
        """Value of the ``Content-Type`` header, lower case."""
        for key, value in self.headers.items():
            if key.lower() == "content-type":
                return value.lower()
        return ""


class HttpTransport(Protocol):
    """Transport contract used by :class:`IrsaClient`.

    Implementations must raise ``httpx.TimeoutException`` or
    ``httpx.TransportError`` when the request cannot be completed.
    """

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        max_bytes: int | None = None,
    ) -> HttpResponse:
        """Perform an HTTP request and return the response."""
        ...


class HttpxTransport:
    """Real transport backed by :mod:`httpx`."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client if client is not None else httpx.Client(follow_redirects=True)
        self._owns_client = client is None

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        max_bytes: int | None = None,
    ) -> HttpResponse:
        """Perform an HTTP request, optionally aborting above ``max_bytes``."""
        if max_bytes is None:
            response = self._client.request(
                method, url, params=params, headers=headers, timeout=timeout
            )
            return HttpResponse(
                status_code=response.status_code,
                content=response.content,
                headers=dict(response.headers),
                url=str(response.url),
            )

        chunks: list[bytes] = []
        total = 0
        with self._client.stream(
            method, url, params=params, headers=headers, timeout=timeout
        ) as response:
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise SourceUnavailableError(
                        "O arquivo excede o tamanho máximo permitido pelo aplicativo.",
                        detail=f"download above {max_bytes} bytes aborted",
                    )
                chunks.append(chunk)
            return HttpResponse(
                status_code=response.status_code,
                content=b"".join(chunks),
                headers=dict(response.headers),
                url=str(response.url),
            )

    def close(self) -> None:
        """Close the underlying client when it is owned by this transport."""
        if self._owns_client:
            self._client.close()


def _to_python(value: Any) -> Any:
    """Convert a VOTable/JSON value into a plain Python object."""
    if value is None:
        return None
    if np.ma.is_masked(value):
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, str):
        return value.strip()
    return value


def _to_float(value: Any) -> float | None:
    """Convert a value to ``float`` or return ``None``."""
    value = _to_python(value)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    """Convert a value to ``int`` or return ``None``."""
    number = _to_float(value)
    if number is None:
        return None
    try:
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return None


def _to_str(value: Any) -> str | None:
    """Convert a value to ``str`` or return ``None`` when empty."""
    value = _to_python(value)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def pick(record: Mapping[str, Any], key: str) -> Any:
    """Return the first alias of ``key`` present in ``record``."""
    for alias in FIELD_ALIASES.get(key, (key,)):
        if alias in record:
            value = _to_python(record[alias])
            if value not in (None, ""):
                return value
    return None


class IrsaClient:
    """Query the IRSA archive and retrieve the products it describes."""

    def __init__(
        self,
        sia2_base_url: str = IRSA_SIA2_BASE_URL,
        cutout_base_url: str = IRSA_CUTOUT_BASE_URL,
        data_base_url: str = "",
        transport: HttpTransport | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        user_agent: str = DEFAULT_USER_AGENT,
        max_fits_bytes: int = 512 * 1024 * 1024,
        sleep: Callable[[float], None] = time.sleep,
        allowed_download_hosts: Sequence[str] = (),
    ) -> None:
        self.sia2_base_url = (sia2_base_url or "").strip()
        self.cutout_base_url = (cutout_base_url or "").strip()
        self.data_base_url = (data_base_url or "").strip()
        self.timeout = timeout
        self.max_attempts = max(1, int(max_attempts))
        self.user_agent = user_agent
        self.max_fits_bytes = max_fits_bytes
        self.allowed_download_hosts = tuple(allowed_download_hosts)
        self._sleep = sleep
        self._transport: HttpTransport = transport if transport is not None else HttpxTransport()

    # -- configuration ----------------------------------------------------------
    @property
    def is_configured(self) -> bool:
        """Whether a SIA2 endpoint address is available."""
        return bool(self.sia2_base_url)

    # -- public API -------------------------------------------------------------
    def query_by_position(
        self,
        ra_deg: float,
        dec_deg: float,
        radius_deg: float,
        *,
        fov_arcmin: float | None = None,
        band: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query the archive for products covering a sky position.

        Args:
            ra_deg: Right ascension of the centre, in decimal degrees.
            dec_deg: Declination of the centre, in decimal degrees.
            radius_deg: Search radius, in decimal degrees.
            fov_arcmin: Field of view that motivated the search, in arcminutes.
            band: Optional spectral band filter (not enabled in the MVP).
            start_date: Optional start of the temporal filter (not enabled).
            end_date: Optional end of the temporal filter (not enabled).

        Returns:
            The list of raw records returned by the service.

        Raises:
            SourceUnavailableError: The service is not configured, unreachable
                or answered with an error.
            MalformedResponseError: The payload could not be interpreted.
        """
        if not self.is_configured:
            raise SourceUnavailableError(
                "A fonte científica IRSA não está configurada neste ambiente.",
                detail="IRSA_SIA2_BASE_URL is empty",
            )

        params = self._build_sia2_params(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            radius_deg=radius_deg,
            fov_arcmin=fov_arcmin,
            band=band,
            start_date=start_date,
            end_date=end_date,
        )
        url = self._join(self.sia2_base_url, "query")
        response = self._request_with_retry("GET", url, params=params)
        return self._parse_sia2_payload(response)

    def fetch_cutout(
        self,
        ra_deg: float,
        dec_deg: float,
        size_arcsec: float,
        *,
        product_url: str | None = None,
    ) -> bytes:
        """Request a cutout from the IRSA cutout service.

        Raises:
            SourceUnavailableError: The cutout service is not configured or
                failed to answer.
        """
        if not self.cutout_base_url:
            raise SourceUnavailableError(
                "O serviço de recorte do IRSA não está configurado neste ambiente.",
                detail="IRSA_CUTOUT_BASE_URL is empty",
            )
        params = self._build_cutout_params(
            ra_deg=ra_deg, dec_deg=dec_deg, size_arcsec=size_arcsec
        )
        if product_url:
            params["PRODUCT"] = product_url
        url = self._join(self.cutout_base_url, "cutout")
        response = self._request_with_retry("GET", url, params=params)
        return response.content

    def download_fits(self, url: str) -> bytes:
        """Download a scientific file, enforcing the size guard.

        Raises:
            SourceUnavailableError: The address is invalid or the download
                failed.
        """
        target = self._resolve_data_url(url)
        self._validate_download_url(target)
        response = self._request_with_retry(
            "GET", target, max_bytes=self.max_fits_bytes
        )
        return response.content

    # -- internals --------------------------------------------------------------
    def _build_sia2_params(
        self,
        *,
        ra_deg: float,
        dec_deg: float,
        radius_deg: float,
        fov_arcmin: float | None = None,
        band: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Build the query parameters sent to the SIA2 service.

        TODO(RESEARCHER-PENDING): the parameter names below follow the IVOA
        SIA2 specification. They must be confirmed against the official
        SPHEREx service documentation before the first real query.
        """
        radius_arcsec = max(radius_deg, 1e-6) * 3600.0
        params: dict[str, Any] = {
            "POS": f"CIRCLE {ra_deg:.6f} {dec_deg:.6f} {radius_deg:.6f}",
            "SIZE": f"{radius_arcsec:.3f} arcsec",
            "FORMAT": "votable",
        }
        if band:
            params["BAND"] = band
        if start_date:
            params["TIME"] = start_date
        if end_date:
            params["TIME"] = f"{start_date},{end_date}" if start_date else end_date
        return params

    def _build_cutout_params(
        self, *, ra_deg: float, dec_deg: float, size_arcsec: float
    ) -> dict[str, Any]:
        """Build the parameters of the cutout service.

        TODO(RESEARCHER-PENDING): confirm the accepted parameter names.
        """
        return {
            "POS": f"CIRCLE {ra_deg:.6f} {dec_deg:.6f}",
            "SIZE": f"{size_arcsec:.3f} arcsec",
            "FORMAT": "fits",
        }

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        max_bytes: int | None = None,
    ) -> HttpResponse:
        """Execute a request, retrying transient failures."""
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._transport.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    max_bytes=max_bytes,
                )
            except SourceUnavailableError:
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("Timeout contacting %s (attempt %s)", url, attempt)
            except httpx.TransportError as exc:
                last_error = exc
                logger.warning("Transport error contacting %s: %s", url, exc)
            else:
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_attempts:
                    last_error = SourceUnavailableError(
                        "A fonte científica respondeu com erro temporário.",
                        detail=f"HTTP {response.status_code}",
                    )
                    logger.warning(
                        "HTTP %s from %s (attempt %s)",
                        response.status_code,
                        url,
                        attempt,
                    )
                else:
                    if response.status_code >= 400:
                        raise SourceUnavailableError(
                            "A fonte científica não pôde ser consultada.",
                            detail=f"HTTP {response.status_code} from {url}",
                        )
                    return response

            if attempt < self.max_attempts:
                self._sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

        raise SourceUnavailableError(
            "A fonte científica IRSA está indisponível neste momento.",
            detail=repr(last_error),
        )

    def _parse_sia2_payload(self, response: HttpResponse) -> list[dict[str, Any]]:
        """Interpret the payload returned by the service.

        Supports the VOTable format (standard for SIA2 services) and a plain
        JSON list of objects.
        """
        content = response.content
        if not content.strip():
            return []

        content_type = response.content_type
        looks_like_json = "json" in content_type or content.lstrip()[:1] in (b"[", b"{")

        if looks_like_json:
            return self._parse_json_payload(content)

        try:
            return self._parse_votable_payload(content)
        except MalformedResponseError:
            # Some services answer JSON without announcing the content type.
            return self._parse_json_payload(content)

    def _parse_votable_payload(self, content: bytes) -> list[dict[str, Any]]:
        """Parse a VOTable payload into a list of flat dictionaries."""
        try:
            from astropy.io.votable import parse as parse_votable
        except ImportError as exc:  # pragma: no cover - astropy is a dependency
            raise MalformedResponseError(
                "Não foi possível interpretar a resposta da fonte científica.",
                detail=f"astropy is not available: {exc}",
            ) from exc

        try:
            votable = parse_votable(io.BytesIO(content))
        except Exception as exc:  # noqa: BLE001 - any parse failure is the same
            raise MalformedResponseError(
                "Não foi possível interpretar a resposta da fonte científica.",
                detail=f"VOTable parse error: {exc}",
            ) from exc

        records: list[dict[str, Any]] = []
        for table in votable.iter_tables():
            array = table.array
            names = array.dtype.names or ()
            for row in array:
                record: dict[str, Any] = {}
                for name in names:
                    record[str(name).strip().lower()] = _to_python(row[name])
                records.append(record)
        return records

    def _parse_json_payload(self, content: bytes) -> list[dict[str, Any]]:
        """Parse a JSON payload into a list of flat dictionaries."""
        try:
            payload = json.loads(content.decode("utf-8", errors="replace"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise MalformedResponseError(
                "Não foi possível interpretar a resposta da fonte científica.",
                detail=f"JSON parse error: {exc}",
            ) from exc

        if isinstance(payload, dict):
            for key in ("data", "features", "results", "records", "rows"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break
            else:
                payload = []

        if not isinstance(payload, list):
            raise MalformedResponseError(
                "Não foi possível interpretar a resposta da fonte científica.",
                detail="JSON payload is not a list of records",
            )

        records: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                records.append(
                    {str(key).strip().lower(): _to_python(value) for key, value in item.items()}
                )
        return records

    def _resolve_data_url(self, url: str) -> str:
        """Return an absolute address for a product."""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if self.data_base_url:
            return f"{self.data_base_url.rstrip('/')}/{url.lstrip('/')}"
        raise SourceUnavailableError(
            "Não foi possível localizar o arquivo original do produto.",
            detail=f"relative url without base url: {url}",
        )

    def _validate_download_url(self, url: str) -> None:
        """Validate the address of a scientific file (RNF-006)."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise SourceUnavailableError(
                "Endereço de arquivo científico inválido.",
                detail=f"unsupported scheme: {parsed.scheme}",
            )
        if not parsed.netloc:
            raise SourceUnavailableError(
                "Endereço de arquivo científico inválido.",
                detail="missing host",
            )
        if self.allowed_download_hosts:
            host = parsed.hostname or ""
            allowed = any(
                host == item or host.endswith(f".{item}")
                for item in self.allowed_download_hosts
            )
            if not allowed:
                raise SourceUnavailableError(
                    "Endereço de arquivo científico inválido.",
                    detail=f"host not allowed: {host}",
                )
        if parsed.scheme == "http":
            logger.warning("Downloading over plain HTTP: %s", url)

    @staticmethod
    def _join(base: str, path: str) -> str:
        """Join a base address and a relative path."""
        return f"{base.rstrip('/')}/{path.lstrip('/')}"


def radius_from_fov(fov_arcmin: float) -> float:
    """Return the search radius (degrees) that covers a field of view.

    The radius is the half diagonal of the field, so the whole field is inside
    the searched circle.
    """
    half_diagonal_arcmin = (fov_arcmin / 2.0) * math.sqrt(2.0)
    return half_diagonal_arcmin / 60.0
