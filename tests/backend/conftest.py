"""Shared fixtures of the backend test-suite.

.. warning::

   **Every fixture of this module is SYNTHETIC.** The records, the VOTable and
   the FITS file built here were written by hand for the tests. They do NOT
   represent SPHEREx observations, do NOT use real archive identifiers and
   must never be presented as scientific data.

   The names always carry the prefix ``synthetic_`` and the addresses use the
   reserved ``.invalid`` domain (RFC 2606), so that a test can never reach a
   real server.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pytest

# --- Make the ``app`` package importable without installing it ---------------
BACKEND_ROOT = Path(__file__).resolve().parents[2] / "src" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.services.cache import DiskCache  # noqa: E402
from app.services.cutout_service import CutoutService  # noqa: E402
from app.services.irsa_client import HttpResponse, IrsaClient  # noqa: E402
from app.services.observation_service import ObservationService  # noqa: E402

#: Reserved domain used by the synthetic fixtures (RFC 2606).
SYNTHETIC_HOST = "synthetic-irsa.invalid"
SYNTHETIC_SIA2_URL = f"https://{SYNTHETIC_HOST}/sia2"
SYNTHETIC_CUTOUT_URL = f"https://{SYNTHETIC_HOST}/cutout"


# --- Synthetic payloads --------------------------------------------------------
SYNTHETIC_VOTABLE_ROWS: tuple[dict[str, str], ...] = (
    {
        "obs_publisher_did": "synthetic-product-002",
        "obs_id": "synthetic-dataset-002",
        "access_url": f"https://{SYNTHETIC_HOST}/files/synthetic-product-002.fits",
        "access_format": "application/fits",
        "s_ra": "133.795129",
        "s_dec": "-7.245147",
        "s_fov": "0.100000",
        "mjd-obs": "60000.500000",
        "t_min": "2025-05-20T00:00:00",
        "t_max": "2025-05-20T00:00:01",
        "band_name": "synthetic-band-b",
        "band_units": "um",
        "em_min": "1.100000",
        "em_max": "1.400000",
        "detector_name": "synthetic-detector-1",
        "instrument_name": "synthetic-instrument",
        "t_exptime": "300.0",
        "provenance": "synthetic-archive",
        "obs_release_date": "2026-01-01T00:00:00",
        "quality": "1.0",
        "s_pixel_scale": "0.300000",
        "cutout_service_ref": "",
    },
    {
        "obs_publisher_did": "synthetic-product-001",
        "obs_id": "synthetic-dataset-001",
        "access_url": f"https://{SYNTHETIC_HOST}/files/synthetic-product-001.fits",
        "access_format": "application/fits",
        "s_ra": "133.795129",
        "s_dec": "-7.245147",
        "s_fov": "0.100000",
        "mjd-obs": "59000.250000",
        "t_min": "2024-03-15T06:00:00",
        "t_max": "2024-03-15T06:00:01",
        "band_name": "synthetic-band-a",
        "band_units": "um",
        "em_min": "0.900000",
        "em_max": "1.100000",
        "detector_name": "synthetic-detector-1",
        "instrument_name": "synthetic-instrument",
        "t_exptime": "280.0",
        "provenance": "synthetic-archive",
        "obs_release_date": "2026-01-01T00:00:00",
        "quality": "0.8",
        "s_pixel_scale": "0.300000",
        "cutout_service_ref": "",
    },
    {
        # Row without any temporal reference: the observation time must remain
        # unresolved instead of being invented.
        "obs_publisher_did": "synthetic-product-003",
        "obs_id": "synthetic-dataset-003",
        "access_url": f"https://{SYNTHETIC_HOST}/files/synthetic-product-003.fits",
        "access_format": "application/fits",
        "s_ra": "133.795129",
        "s_dec": "-7.245147",
        "s_fov": "0.100000",
        "mjd-obs": "",
        "t_min": "",
        "t_max": "",
        "band_name": "synthetic-band-a",
        "band_units": "um",
        "em_min": "",
        "em_max": "",
        "detector_name": "synthetic-detector-2",
        "instrument_name": "synthetic-instrument",
        "t_exptime": "",
        "provenance": "synthetic-archive",
        "obs_release_date": "",
        "quality": "",
        "s_pixel_scale": "0.300000",
        "cutout_service_ref": "",
    },
)

SYNTHETIC_VOTABLE_COLUMNS = tuple(SYNTHETIC_VOTABLE_ROWS[0].keys())


def build_synthetic_votable(
    rows: Iterable[Mapping[str, str]] = SYNTHETIC_VOTABLE_ROWS,
) -> bytes:
    """Build a SYNTHETIC VOTable that mimics a SIA2 answer.

    The content is invented for the tests only.
    """
    columns = list(SYNTHETIC_VOTABLE_COLUMNS)
    fields = "\n".join(
        f'      <FIELD name="{column}" datatype="char" arraysize="*"/>'
        for column in columns
    )
    table_rows = []
    for row in rows:
        cells = "".join(
            f"<TD>{row.get(column, '')}</TD>" for column in columns
        )
        table_rows.append(f"        <TR>{cells}</TR>")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
  <RESOURCE type="results">
    <TABLE name="synthetic-results">
      <DESCRIPTION>Synthetic SIA2-like table used only by the test-suite.</DESCRIPTION>
{fields}
      <DATA>
        <TABLEDATA>
{chr(10).join(table_rows)}
        </TABLEDATA>
      </DATA>
    </TABLE>
  </RESOURCE>
</VOTABLE>
"""
    return xml.encode("utf-8")


def build_synthetic_json(records: Iterable[Mapping[str, Any]]) -> bytes:
    """Build a SYNTHETIC JSON answer that mimics a SIA2 answer."""
    import json

    return json.dumps(list(records)).encode("utf-8")



def build_synthetic_fits(
    size: int = 64,
    date_obs: str = "2026-01-02T03:04:05",
    *,
    with_wcs: bool = True,
) -> bytes:
    """Build a synthetic FITS image for automated tests.

    The image and metadata are entirely synthetic.
    """

    from astropy.io import fits

    data = np.zeros((size, size), dtype=np.float32)

    yy, xx = np.mgrid[0:size, 0:size]

    data += 100.0 * np.exp(
        -(
            (xx - size / 2.0) ** 2
            + (yy - size / 2.0) ** 2
        ) / 50.0
    )

    header = fits.Header()

    header["DATE-OBS"] = date_obs
    header["EXPTIME"] = 300.0
    header["INSTRUME"] = "synthetic-instrument"
    header["DETECTOR"] = "synthetic-detector-1"
    header["BUNIT"] = "MJy/sr"

    if with_wcs:
        # Synthetic celestial WCS centered on the test target.
        header["CTYPE1"] = "RA---TAN"
        header["CTYPE2"] = "DEC--TAN"

        header["CRVAL1"] = 133.795129
        header["CRVAL2"] = -7.245147

        header["CRPIX1"] = (size + 1) / 2.0
        header["CRPIX2"] = (size + 1) / 2.0

        header["CDELT1"] = -0.001
        header["CDELT2"] = 0.001

        header["CUNIT1"] = "deg"
        header["CUNIT2"] = "deg"
        header["RADESYS"] = "ICRS"

    primary = fits.PrimaryHDU()

    image_hdu = fits.ImageHDU(
        data=data,
        header=header,
        name="IMAGE",
    )

    hdulist = fits.HDUList(
        [primary, image_hdu]
    )

    buffer = io.BytesIO()

    hdulist.writeto(buffer)

    return buffer.getvalue()


# --- Fakes ---------------------------------------------------------------------
class FakeTransport:
    """Transport fake that never touches the network.

    The queued answers are consumed in order. Exceptions are raised instead of
    being returned, which allows the simulation of timeouts and connection
    errors. When the queue is exhausted the last answer is repeated, which
    simulates a persistent failure (the client retries transient errors).
    """

    def __init__(self, answers: Iterable[Any] | None = None) -> None:
        self.answers: list[Any] = list(answers or [])
        self.requests: list[dict[str, Any]] = []
        self._last_answer: Any = None

    def queue(self, *answers: Any) -> "FakeTransport":
        """Add answers to the queue and return the transport."""
        self.answers.extend(answers)
        return self

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        max_bytes: int | None = None,
        stop_when: Any = None,
    ) -> HttpResponse:
        """Record the request and return (or raise) the queued answer.

        Like the real transport, ``stop_when`` truncates a 200 body to the
        number of bytes it reports as enough.
        """
        self.requests.append(
            {
                "method": method,
                "url": url,
                "params": dict(params or {}),
                "headers": dict(headers or {}),
                "timeout": timeout,
                "max_bytes": max_bytes,
                "stop_when": stop_when,
            }
        )
        if self.answers:
            self._last_answer = self.answers.pop(0)
        elif self._last_answer is None:
            raise AssertionError(f"FakeTransport has no queued answer for {url}")
        answer = self._last_answer
        if isinstance(answer, Exception):
            raise answer
        if stop_when is not None and answer.status_code == 200:
            enough = stop_when(answer.content)
            if enough is not None:
                return HttpResponse(
                    answer.status_code, answer.content[:enough], answer.headers, answer.url
                )
        return answer


def json_response(payload: bytes, status: int = 200) -> HttpResponse:
    """Build a JSON HTTP response."""
    return HttpResponse(
        status_code=status,
        content=payload,
        headers={"content-type": "application/json"},
        url=SYNTHETIC_SIA2_URL,
    )


def votable_response(payload: bytes | None = None, status: int = 200) -> HttpResponse:
    """Build a VOTable HTTP response."""
    content = payload if payload is not None else build_synthetic_votable()
    return HttpResponse(
        status_code=status,
        content=content,
        headers={"content-type": "text/xml"},
        url=SYNTHETIC_SIA2_URL,
    )


def fits_response(payload: bytes | None = None, status: int = 200) -> HttpResponse:
    """Build a FITS HTTP response."""
    content = payload if payload is not None else build_synthetic_fits()
    return HttpResponse(
        status_code=status,
        content=content,
        headers={"content-type": "application/fits"},
        url=f"https://{SYNTHETIC_HOST}/files/synthetic-product-001.fits",
    )


# --- Fixtures ------------------------------------------------------------------
@pytest.fixture
def synthetic_votable() -> bytes:
    """SYNTHETIC VOTable payload."""
    return build_synthetic_votable()


@pytest.fixture
def synthetic_fits() -> bytes:
    """SYNTHETIC FITS payload."""
    return build_synthetic_fits()


@pytest.fixture
def fake_transport() -> FakeTransport:
    """Transport fake without queued answers."""
    return FakeTransport()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing to a temporary cache and without any IRSA address."""
    return Settings(
        cache_dir=tmp_path / "cache",
        cache_ttl_seconds=3600,
        irsa_sia2_base_url=SYNTHETIC_SIA2_URL,
    )


@pytest.fixture
def service_factory(tmp_path: Path):
    """Factory that builds an :class:`ObservationService` without network."""

    def factory(
        transport: FakeTransport,
        *,
        cutout_url: str = "",
        **setting_overrides: Any,
    ) -> ObservationService:
        local_settings = Settings(
            cache_dir=tmp_path / "cache",
            cache_ttl_seconds=setting_overrides.pop("cache_ttl_seconds", 3600),
            irsa_sia2_base_url=SYNTHETIC_SIA2_URL,
            irsa_cutout_base_url=cutout_url,
            **setting_overrides,
        )
        client = IrsaClient(
            sia2_base_url=local_settings.irsa_sia2_base_url,
            cutout_base_url=local_settings.irsa_cutout_base_url,
            transport=transport,
            timeout=local_settings.http_timeout_seconds,
            max_attempts=local_settings.http_max_attempts,
            max_fits_bytes=local_settings.max_fits_bytes,
            sleep=lambda _seconds: None,
        )
        cache = DiskCache(
            local_settings.cache_dir, local_settings.cache_ttl_seconds
        )
        cutout_service = CutoutService(client, local_settings)
        return ObservationService(client, cache, cutout_service, local_settings)

    return factory
