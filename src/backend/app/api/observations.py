"""Router with the endpoints of the public API.

The routes follow ``docs/architecture/api-contract.md``:

* ``GET /api/observations`` -- spatial query, chronological answer.
* ``GET /api/images/{observation_id}`` -- processed image of an observation.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, Query, Response

from app.api.errors import InvalidParametersError
from app.api.releases import get_collection_resolver
from app.core.config import Settings, get_settings
from app.schemas.observation import ObservationResponse
from app.services.astrometry import ProperMotion
from app.services.cache import DiskCache
from app.services.cutout_service import CutoutService
from app.services.irsa_client import IrsaClient
from app.services.observation_service import ObservationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observations"])


@lru_cache(maxsize=1)
def get_irsa_client() -> IrsaClient:
    """Return the client of the IRSA archive, built from the configuration."""
    settings = get_settings()
    return IrsaClient(
        sia2_base_url=settings.irsa_sia2_base_url,
        cutout_base_url=settings.irsa_cutout_base_url,
        data_base_url=settings.irsa_data_base_url,
        timeout=settings.http_timeout_seconds,
        max_attempts=settings.http_max_attempts,
        user_agent=settings.user_agent,
        max_fits_bytes=settings.max_fits_bytes,
        allowed_download_hosts=settings.allowed_download_hosts,
        max_concurrent_product_requests=settings.max_concurrent_product_requests,
        collections=get_collection_resolver().collections,
    )


@lru_cache(maxsize=1)
def get_observation_service() -> ObservationService:
    """Return the orchestration service used by the routes."""
    settings: Settings = get_settings()
    client = get_irsa_client()
    cache = DiskCache(settings.cache_dir, settings.cache_ttl_seconds)
    cutout_service = CutoutService(client, settings)
    return ObservationService(client, cache, cutout_service, settings)


@router.get(
    "/observations",
    response_model=ObservationResponse,
    summary="Query the SPHEREx archive for a sky position",
    description=(
        "Queries the IRSA/SPHEREx archive for the observations that cover the "
        "requested coordinates and returns them in chronological order."
    ),
)
def list_observations(
    ra_deg: float = Query(
        ...,
        ge=0.0,
        lt=360.0,
        description="Right ascension in decimal degrees (ICRS), 0 <= ra < 360.",
    ),
    dec_deg: float = Query(
        ...,
        ge=-90.0,
        le=90.0,
        description="Declination in decimal degrees (ICRS), -90 <= dec <= 90.",
    ),
    fov_arcmin: float = Query(
        ...,
        gt=0.0,
        description="Field of view in arcminutes.",
    ),
    start_date: str | None = Query(
        None,
        description=(
            "Start date of the temporal filter. Not enabled yet: the filter is "
            "only implemented after the scientific validation of the query."
        ),
    ),
    end_date: str | None = Query(
        None,
        description=(
            "End date of the temporal filter. Not enabled yet: the filter is "
            "only implemented after the scientific validation of the query."
        ),
    ),
    band: str | None = Query(
        None,
        description=(
            "Spectral band filter. Not enabled yet: the filter is only "
            "implemented after the scientific validation of the query."
        ),
    ),
    pm_ra_cosdec_masyr: float | None = Query(
        None,
        ge=-30000.0,
        le=30000.0,
        description=(
            "Proper motion in RA, already multiplied by cos(dec), in mas/yr "
            "(Gaia pmra convention). Requires pm_dec_masyr and ref_epoch_jyear."
        ),
    ),
    pm_dec_masyr: float | None = Query(
        None, ge=-30000.0, le=30000.0, description="Proper motion in Dec, in mas/yr."
    ),
    ref_epoch_jyear: float | None = Query(
        None,
        ge=1900.0,
        le=2100.0,
        description=(
            "Julian year of the given ra_deg/dec_deg (e.g. 2016.0). With the "
            "proper motion, each observation is cut at the propagated position."
        ),
    ),
    service: ObservationService = Depends(get_observation_service),
) -> ObservationResponse:
    """Return the observations available for the requested coordinates."""
    unsupported = [
        name
        for name, value in (
            ("start_date", start_date),
            ("end_date", end_date),
            ("band", band),
        )
        if value is not None
    ]
    if unsupported:
        raise InvalidParametersError(
            "Os parâmetros "
            + ", ".join(unsupported)
            + " ainda não estão validados cientificamente e não são aceitos "
            "nesta versão da API."
        )

    motion_values = (pm_ra_cosdec_masyr, pm_dec_masyr, ref_epoch_jyear)
    motion: ProperMotion | None = None
    if any(value is not None for value in motion_values):
        if any(value is None for value in motion_values):
            raise InvalidParametersError(
                "Para corrigir o movimento próprio informe juntos "
                "pm_ra_cosdec_masyr, pm_dec_masyr e ref_epoch_jyear."
            )
        motion = ProperMotion(pm_ra_cosdec_masyr, pm_dec_masyr, ref_epoch_jyear)

    return service.search(ra_deg, dec_deg, fov_arcmin, motion=motion)


@router.get(
    "/images/{observation_id}",
    summary="Processed image of an observation",
    description=(
        "Returns the processed visual representation of the observation. The "
        "image is a visual rendering of the scientific product and is not a "
        "photometric measurement."
    ),
    response_class=Response,
)
def get_observation_image(
    observation_id: str,
    service: ObservationService = Depends(get_observation_service),
) -> Response:
    """Return the PNG of an observation.

    Args:
        observation_id: Internal identifier of the observation, as published in
            the ``id`` field of the observations list.
    """
    result = service.get_image(observation_id)
    headers = {"Content-Disposition": f'inline; filename="{observation_id}.png"'}
    headers.update(result.headers)
    return Response(
        content=result.content,
        media_type=result.content_type,
        headers=headers,
    )
