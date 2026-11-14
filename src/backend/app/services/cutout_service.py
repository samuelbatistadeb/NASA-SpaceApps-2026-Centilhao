"""Strategy used to obtain the pixels displayed for an observation.

Two strategies are supported:

``REMOTE_CUTOUT``
    The IRSA cutout service extracts the region and returns it. Less data
    travels over the network, which is the option preferred by the project
    (``docs/architecture/system.md`` section 11).

``LOCAL_DOWNLOAD``
    The original FITS file is downloaded and the region is extracted locally
    with ``astropy.nddata.Cutout2D``.

The choice is made by configuration, never by trial and error, and it is
recorded in the metadata of the observation so that the origin of the displayed
pixels stays auditable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np

from app.api.errors import ProcessingError
from app.core.config import Settings
from app.services import fits_processor
from app.services.irsa_client import IrsaClient

logger = logging.getLogger(__name__)


class CutoutStrategy(str, Enum):
    """How the displayed pixels were obtained."""

    REMOTE_CUTOUT = "remote_cutout"
    LOCAL_DOWNLOAD = "local_download"


@dataclass
class CutoutRequest:
    """Everything needed to build the image of an observation."""

    product_id: str | None = None
    access_url: str | None = None
    ra_deg: float = 0.0
    dec_deg: float = 0.0
    fov_arcmin: float = 1.0
    pixel_scale_arcsec: float | None = None
    cutout_service_ref: str | None = None


@dataclass
class CutoutResult:
    """The plane to be rendered and the metadata that describes it."""

    data: np.ndarray
    strategy: CutoutStrategy
    metadata: dict[str, Any] = field(default_factory=dict)
    header: dict[str, Any] = field(default_factory=dict)
    observed_at: datetime | None = None


class CutoutService:
    """Build the image data of an observation."""

    def __init__(self, client: IrsaClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    # -- strategy ---------------------------------------------------------------
    def decide_strategy(self, request: CutoutRequest) -> CutoutStrategy:
        """Return the strategy to be used for the given request."""
        mode = self._settings.cutout_mode
        ibe_available = self._client.supports_ibe_cutout(request.access_url)
        remote_available = ibe_available or bool(self._client.cutout_base_url)

        if ibe_available and mode in ("auto", "remote"):
            return CutoutStrategy.REMOTE_CUTOUT

        if mode == "local":
            return CutoutStrategy.LOCAL_DOWNLOAD
        if mode == "remote":
            if remote_available:
                return CutoutStrategy.REMOTE_CUTOUT
            logger.warning(
                "Remote cutout requested but the IRSA cutout service is not "
                "configured; falling back to the local download."
            )
            return CutoutStrategy.LOCAL_DOWNLOAD

        if remote_available and request.cutout_service_ref:
            return CutoutStrategy.REMOTE_CUTOUT
        return CutoutStrategy.LOCAL_DOWNLOAD

    # -- execution --------------------------------------------------------------
    def build_cutout(self, request: CutoutRequest) -> CutoutResult:
        """Retrieve and cut the image of an observation.

        Raises:
            SourceUnavailableError: The file could not be retrieved.
            ProcessingError: The file could not be processed.
        """
        strategy = self.decide_strategy(request)
        if strategy is CutoutStrategy.REMOTE_CUTOUT:
            return self._build_remote_cutout(request, strategy)
        return self._build_local_cutout(request, strategy)

    def _build_remote_cutout(
        self, request: CutoutRequest, strategy: CutoutStrategy
    ) -> CutoutResult:
        """Ask IRSA for the region (IBE cutout of the product, when possible)."""
        size_arcsec = max(request.fov_arcmin * 60.0, 1.0)
        if self._client.supports_ibe_cutout(request.access_url):
            content = self._client.fetch_ibe_cutout(
                request.access_url,
                request.ra_deg,
                request.dec_deg,
                size_arcsec / 3600.0,
            )
            center_source = "ibe_cutout"
        else:
            content = self._client.fetch_cutout(
                request.ra_deg,
                request.dec_deg,
                size_arcsec,
                product_url=request.access_url,
            )
            center_source = "remote_cutout_service"
        image = fits_processor.load_image(content)
        metadata: dict[str, Any] = {
            "cutout_strategy": strategy.value,
            "cutout_center_source": center_source,
            "cutout_size_pixels": [int(image.data.shape[1]), int(image.data.shape[0])],
            "source_bytes": len(content),
        }
        metadata.update(fits_processor.extract_header_metadata(image.header))
        return CutoutResult(
            data=image.data,
            strategy=strategy,
            metadata=metadata,
            header=fits_processor.extract_header_metadata(image.header),
            observed_at=fits_processor.extract_observation_datetime(image.header),
        )

    def _build_local_cutout(
        self, request: CutoutRequest, strategy: CutoutStrategy
    ) -> CutoutResult:
        """Download the original file and cut the region locally."""
        if not request.access_url:
            raise ProcessingError(
                "O produto não informa um arquivo original para recortar.",
                detail=f"product_id={request.product_id}",
            )

        content = self._client.download_fits(request.access_url)
        image = fits_processor.load_image(content)
        header_metadata = fits_processor.extract_header_metadata(image.header)

        wcs = fits_processor.extract_wcs(image.header)
        arcsec_per_pixel = fits_processor.pixel_scale_arcsec(wcs) or request.pixel_scale_arcsec
        size_pixels, criterion = fits_processor.size_pixels_for_fov(
            request.fov_arcmin,
            arcsec_per_pixel=arcsec_per_pixel,
            default_pixels=self._settings.default_cutout_pixels,
            max_pixels=self._settings.max_cutout_pixels,
        )

        cutout = fits_processor.cutout_image(
            image, request.ra_deg, request.dec_deg, size_pixels
        )

        metadata: dict[str, Any] = {
            "cutout_strategy": strategy.value,
            "cutout_center_source": cutout.metadata.get("cutout_center_source"),
            "cutout_size_pixels": size_pixels,
            "cutout_size_criterion": criterion,
            "pixel_scale_arcsec": arcsec_per_pixel,
            "source_bytes": len(content),
        }
        if cutout.metadata.get("cutout_center_px") is not None:
            metadata["cutout_center_px"] = cutout.metadata["cutout_center_px"]
        metadata.update(header_metadata)

        return CutoutResult(
            data=cutout.data,
            strategy=strategy,
            metadata=metadata,
            header=header_metadata,
            observed_at=fits_processor.extract_observation_datetime(image.header),
        )
