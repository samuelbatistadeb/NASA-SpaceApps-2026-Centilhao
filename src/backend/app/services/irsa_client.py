"""Client for the IRSA / IPAC services that archive the SPHEREx mission data.

Verified behaviour (DECISÃO 007 and DECISÃO 009, real queries on 2026-11-14):

* Discovery: SIA v2 at ``https://irsa.ipac.caltech.edu/SIA`` (``/SIA2`` is 404),
  answering a VOTable whose FIELDs carry ``ID="col_N"`` and ObsCore names.
* Cutout: there is no standalone cutout service. The IBE serves a cutout of
  each product by appending ``?center=<ra>,<dec>d&size=<deg>`` to its
  ``access_url`` (:meth:`IrsaClient.fetch_ibe_cutout`). HTTP 422 ("Arrays do
  not overlap.") and 500 mean that the product does not cover the position.

An empty SIA address still means "source not configured" and raises
:class:`SourceUnavailableError`. The HTTP transport is injectable so that the
test-suite never touches the network.
"""

from __future__ import annotations

import io
import json
import logging
import math
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlparse

import httpx
import numpy as np

from app.api.errors import (
    ImageNotFoundError,
    MalformedResponseError,
    SourceUnavailableError,
)

logger = logging.getLogger(__name__)

# --- Service addresses -----------------------------------------------------------
#: SIA v2 endpoint verified on 2026-11-14 (DECISÃO 007 / 009).
IRSA_SIA2_BASE_URL: str = "https://irsa.ipac.caltech.edu/SIA"
#: IRSA has no standalone cutout service; see :meth:`IrsaClient.fetch_ibe_cutout`.
IRSA_CUTOUT_BASE_URL: str = ""

#: Path fragment that identifies an IBE product address (cutout capable).
IBE_DATA_PATH = "/ibe/data/"

#: HTTP statuses of an IBE cutout meaning "the product does not cover the
#: position" (observed: 422 "Arrays do not overlap.", and 500). Not retried.
IBE_NO_OVERLAP_STATUS_CODES = frozenset({422, 500})

#: Default HTTP timeout, in seconds.
DEFAULT_TIMEOUT_SECONDS = 30.0
#: Default number of attempts for transient failures.
DEFAULT_MAX_ATTEMPTS = 3
#: Default maximum number of simultaneous product requests (cutouts and
#: downloads). IRSA answers 503 "Server busy" under many parallel requests.
DEFAULT_MAX_CONCURRENT_PRODUCT_REQUESTS = 3
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
    # ``instrument_name`` is NOT an alias: on SPHEREx it is always "SPHEREx"
    # and would be shown as if it were the detector. See ``extract_detector``.
    "detector": ("detector_name", "detector"),
    "band": (
        "energy_bandpassname",
        "band_name",
        "band",
        "band_pass",
        "filter_name",
    ),
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


#: Size of a FITS block and of a header card.
_FITS_BLOCK = 2880
_FITS_CARD = 80


def _fits_card_value(card: str) -> str:
    """Return the raw value of a FITS header card (``KEY = value / comment``)."""
    value = card[10:] if card[8:10] == "= " else ""
    if value.lstrip().startswith("'"):
        text = value.lstrip()[1:]
        return text.split("'", 1)[0].strip()
    return value.split("/", 1)[0].strip()


def fits_bytes_through_extension(
    buffer: bytes | bytearray, extname: str = "IMAGE"
) -> int | None:
    """Return how many bytes of ``buffer`` hold every HDU up to ``extname``.

    FITS files are sequential (header blocks, then data padded to 2880 bytes),
    so a client may stop reading once the wanted extension is complete. SPHEREx
    Level 2 products store ``IMAGE`` right after the primary HDU, while the
    large ``EPSF`` table (~3.9 MB, unused here) comes last (verified on a real
    IBE cutout, 2026-11-14). Returns ``None`` while the buffer is not enough
    (or the extension is not found), which means "keep reading".
    """
    position = 0
    size = len(buffer)
    while position + _FITS_BLOCK <= size:
        cards: dict[str, str] = {}
        header_end = None
        cursor = position
        while cursor + _FITS_BLOCK <= size and header_end is None:
            block = buffer[cursor:cursor + _FITS_BLOCK].decode("ascii", errors="replace")
            cursor += _FITS_BLOCK
            for offset in range(0, _FITS_BLOCK, _FITS_CARD):
                card = block[offset:offset + _FITS_CARD]
                key = card[:8].strip()
                if key == "END":
                    header_end = cursor
                    break
                if key and key not in cards:
                    cards[key] = _fits_card_value(card)
        if header_end is None:
            return None
        try:
            bitpix = abs(int(cards.get("BITPIX", "8")))
            naxis = int(cards.get("NAXIS", "0"))
            pcount = int(cards.get("PCOUNT", "0"))
            gcount = int(cards.get("GCOUNT", "1"))
            axes = [int(cards.get(f"NAXIS{i}", "0")) for i in range(1, naxis + 1)]
        except ValueError:
            return None
        elements = math.prod(axes) if axes else 0
        data_bytes = (bitpix // 8) * gcount * (pcount + elements) if naxis else 0
        data_end = header_end + math.ceil(data_bytes / _FITS_BLOCK) * _FITS_BLOCK
        if cards.get("EXTNAME", "").upper() == extname.upper():
            return data_end if data_end <= size else None
        position = data_end
    return None


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
        stop_when: Callable[[bytes], int | None] | None = None,
    ) -> HttpResponse:
        """Perform an HTTP request and return the response.

        ``stop_when`` (optional) receives the body read so far and returns the
        number of bytes that are enough; the transport may then stop reading.
        """
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
        stop_when: Callable[[bytes], int | None] | None = None,
    ) -> HttpResponse:
        """Perform an HTTP request, optionally aborting above ``max_bytes``.

        With ``stop_when`` the body is streamed and the connection is closed as
        soon as the callback says the bytes read so far are enough.
        """
        if max_bytes is None and stop_when is None:
            response = self._client.request(
                method, url, params=params, headers=headers, timeout=timeout
            )
            return HttpResponse(
                status_code=response.status_code,
                content=response.content,
                headers=dict(response.headers),
                url=str(response.url),
            )

        body = bytearray()
        with self._client.stream(
            method, url, params=params, headers=headers, timeout=timeout
        ) as response:
            watch = stop_when is not None and response.status_code == 200
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if max_bytes is not None and len(body) > max_bytes:
                    raise SourceUnavailableError(
                        "O arquivo excede o tamanho máximo permitido pelo aplicativo.",
                        detail=f"download above {max_bytes} bytes aborted",
                    )
                if watch:
                    enough = stop_when(body)  # no copy: only headers are parsed
                    if enough is not None and len(body) >= enough:
                        del body[enough:]
                        break  # leaving the context manager closes the stream
            return HttpResponse(
                status_code=response.status_code,
                content=bytes(body),
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


#: ``obs_publisher_did`` of SPHEREx ends with the detector, e.g.
#: ``ivo://irsa.ipac/spherex_dr1?2025W19_1B_0116_1/D3``.
_DID_DETECTOR_PATTERN = re.compile(r"/D(\d+)$")
#: ``energy_bandpassname`` of SPHEREx names the detector, e.g. ``SPHEREx-D3``.
_BANDPASS_DETECTOR_PATTERN = re.compile(r"^SPHEREx-D(\d+)$", re.IGNORECASE)


def extract_detector(record: Mapping[str, Any]) -> str | None:
    """Return the detector of a record (``"D1"`` .. ``"D6"``) or ``None``.

    The IRSA SIA v2 answer for SPHEREx has no detector column (verified on
    2026-11-14). The detector is published in ``obs_publisher_did`` (suffix
    ``/D<n>``) and in ``energy_bandpassname`` (``SPHEREx-D<n>``). An explicit
    detector column, when present, wins. Nothing is guessed.
    """
    explicit = pick(record, "detector")
    if explicit not in (None, ""):
        return str(explicit).strip()

    did = _to_str(record.get("obs_publisher_did"))
    if did:
        match = _DID_DETECTOR_PATTERN.search(did)
        if match:
            return f"D{match.group(1)}"

    bandpass = _to_str(record.get("energy_bandpassname"))
    if bandpass:
        match = _BANDPASS_DETECTOR_PATTERN.match(bandpass)
        if match:
            return f"D{match.group(1)}"
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
        max_concurrent_product_requests: int = DEFAULT_MAX_CONCURRENT_PRODUCT_REQUESTS,
    ) -> None:
        #: Limits simultaneous cutouts/downloads across all request threads.
        self._product_slots = threading.BoundedSemaphore(
            max(1, int(max_concurrent_product_requests))
        )
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
        url = self.sia2_base_url
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
        url = self.cutout_base_url
        response = self._request_with_retry("GET", url, params=params)
        return response.content

    @staticmethod
    def supports_ibe_cutout(access_url: str | None) -> bool:
        """Whether ``access_url`` is an IRSA IBE product address."""
        if not access_url:
            return False
        parsed = urlparse(access_url)
        return parsed.scheme == "https" and IBE_DATA_PATH in parsed.path

    def fetch_ibe_cutout(
        self,
        access_url: str,
        ra_deg: float,
        dec_deg: float,
        size_deg: float,
    ) -> bytes:
        """Request an IBE cutout of one product: ``<access_url>?center=..&size=..``.

        Args:
            access_url: IBE address of the full FITS product (from the SIA).
            ra_deg: Right ascension of the cutout centre (ICRS, degrees).
            dec_deg: Declination of the cutout centre (ICRS, degrees).
            size_deg: Side of the square cutout, in degrees.

        Raises:
            ImageNotFoundError: The product does not cover the position.
            SourceUnavailableError: The address is invalid or IRSA failed.
        """
        if not self.supports_ibe_cutout(access_url):
            raise SourceUnavailableError(
                "O produto não oferece recorte pelo IRSA.",
                detail=f"not an IBE address: {access_url}",
            )
        if access_url.split("#", 1)[0].find("?") != -1:
            raise SourceUnavailableError(
                "Endereço de arquivo científico inválido.",
                detail=f"access_url already has a query string: {access_url}",
            )
        self._validate_download_url(access_url)
        params = {
            "center": f"{ra_deg:.6f},{dec_deg:.6f}d",
            "size": f"{size_deg:.6f}",
        }
        with self._product_slots:
            response = self._request_with_retry(
                "GET",
                access_url,
                params=params,
                max_bytes=self.max_fits_bytes,
                terminal_statuses=IBE_NO_OVERLAP_STATUS_CODES,
                stop_when=fits_bytes_through_extension,
            )
        if response.status_code in IBE_NO_OVERLAP_STATUS_CODES:
            raise ImageNotFoundError(
                "Este produto não cobre a posição solicitada.",
                detail=f"IBE cutout HTTP {response.status_code}: {response.text[:200]}",
            )
        return response.content

    def download_fits(self, url: str) -> bytes:
        """Download a scientific file, enforcing the size guard.

        Raises:
            SourceUnavailableError: The address is invalid or the download
                failed.
        """
        target = self._resolve_data_url(url)
        self._validate_download_url(target)
        with self._product_slots:
            response = self._request_with_retry(
                "GET",
                target,
                max_bytes=self.max_fits_bytes,
                stop_when=fits_bytes_through_extension,
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
        """Build parameters for the IRSA SIA v2 service."""

        params: dict[str, Any] = {
            "POS": (
                f"CIRCLE {ra_deg:.6f} "
                f"{dec_deg:.6f} {radius_deg:.6f}"
            ),
            "COLLECTION": [
                "spherex_dr1",
                "spherex_qr3",
                "spherex_dr1_deep",
                "spherex_qr3_deep",
            ],
            "RESPONSEFORMAT": "votable",
            "MAXREC": 1000,
        }

        if band is not None:
            raise ValueError(
                "Band filtering is not enabled in this version."
            )

        if start_date is not None or end_date is not None:
            raise ValueError(
                "Temporal filtering is not enabled in this version."
            )

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
        terminal_statuses: frozenset[int] = frozenset(),
        stop_when: Callable[[bytes], int | None] | None = None,
    ) -> HttpResponse:
        """Execute a request, retrying transient failures.

        Statuses in ``terminal_statuses`` are returned to the caller at once,
        without retry and without raising, so it can interpret them.
        """
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        last_error: Exception | None = None

        extra: dict[str, Any] = {"stop_when": stop_when} if stop_when is not None else {}
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._transport.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    max_bytes=max_bytes,
                    **extra,
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
                if response.status_code in terminal_statuses:
                    return response
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
            columns = array.dtype.names or ()
            # astropy names the array columns after the FIELD ``ID`` when it
            # exists. IRSA declares ``ID="col_N"``, so the public ``name`` must
            # be used as key (verified on a real SIA answer, 2026-11-14).
            field_names = [field.name or field.ID for field in table.fields]
            if len(field_names) != len(columns):
                field_names = list(columns)
            for row in array:
                record: dict[str, Any] = {}
                for column, name in zip(columns, field_names):
                    record[str(name).strip().lower()] = _to_python(row[column])
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
