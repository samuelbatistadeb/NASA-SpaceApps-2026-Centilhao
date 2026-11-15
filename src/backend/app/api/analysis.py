"""Analysis endpoints built on the common frame.

* ``GET /api/coverage`` -- complete/partial frames for each field of view,
  computed from the detector polygons (no image is downloaded).
* ``GET /api/composite`` -- mean of several epochs of one detector (higher
  signal-to-noise) or the difference between two groups of epochs (sources
  that moved show up as bright/dark pairs).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Response

from app.api.errors import InvalidParametersError
from app.api.observations import get_observation_service
from app.services.astrometry import ProperMotion
from app.services.observation_service import ObservationService

router = APIRouter(tags=["analysis"])


def _motion(
    pm_ra_cosdec_masyr: float | None,
    pm_dec_masyr: float | None,
    ref_epoch_jyear: float | None,
) -> ProperMotion | None:
    values = (pm_ra_cosdec_masyr, pm_dec_masyr, ref_epoch_jyear)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise InvalidParametersError(
            "Para corrigir o movimento próprio informe juntos "
            "pm_ra_cosdec_masyr, pm_dec_masyr e ref_epoch_jyear."
        )
    return ProperMotion(pm_ra_cosdec_masyr, pm_dec_masyr, ref_epoch_jyear)


def _ids(text: str | None) -> list[str]:
    return [item.strip() for item in (text or "").split(",") if item.strip()]


@router.get("/coverage", summary="Complete and partial frames for each field of view")
def get_coverage(
    ra_deg: float = Query(..., ge=0.0, lt=360.0),
    dec_deg: float = Query(..., ge=-90.0, le=90.0),
    pm_ra_cosdec_masyr: float | None = Query(None, ge=-30000.0, le=30000.0),
    pm_dec_masyr: float | None = Query(None, ge=-30000.0, le=30000.0),
    ref_epoch_jyear: float | None = Query(None, ge=1900.0, le=2100.0),
    service: ObservationService = Depends(get_observation_service),
) -> dict[str, Any]:
    """Return, for 1-30 arcmin, how many observations give a complete frame."""
    motion = _motion(pm_ra_cosdec_masyr, pm_dec_masyr, ref_epoch_jyear)
    return service.coverage(ra_deg, dec_deg, motion)


@router.get(
    "/composite",
    summary="Mean or difference of epochs on the common frame (PNG)",
    response_class=Response,
)
def get_composite(
    op: str = Query(..., description="'mean' (group A) or 'diff' (mean A - mean B)."),
    a: str = Query(..., description="Comma separated observation ids (group A)."),
    b: str | None = Query(None, description="Comma separated observation ids (group B)."),
    service: ObservationService = Depends(get_observation_service),
) -> Response:
    """Return the combined image as a PNG; metadata in X-SpherEx-* headers."""
    result = service.composite(op, _ids(a), _ids(b))
    return Response(content=result.content, media_type="image/png", headers=result.headers)
