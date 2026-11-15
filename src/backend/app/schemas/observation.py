"""Pydantic models mirroring ``docs/architecture/api-contract.md``.

The field names and types below follow the API contract exactly. Every field
that cannot be obtained from the scientific source is ``None``: the backend
never fills a missing value with an invented one (RC-005).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Target(BaseModel):
    """Celestial coordinates requested by the user."""

    model_config = ConfigDict(extra="forbid")

    ra_deg: float = Field(
        ...,
        ge=0.0,
        lt=360.0,
        description="Right ascension in decimal degrees (ICRS), 0 <= ra < 360.",
    )
    dec_deg: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Declination in decimal degrees (ICRS), -90 <= dec <= 90.",
    )


class QueryParams(BaseModel):
    """Parameters actually applied to the archive query."""

    model_config = ConfigDict(extra="forbid")

    fov_arcmin: float = Field(
        ...,
        gt=0.0,
        description="Field of view used for the query, in arcminutes.",
    )


class ObservationMetadata(BaseModel):
    """Complementary metadata preserved for each observation.

    ``product_id`` and ``quality`` keep the names and types used by the API
    contract example. The remaining fields are required by the contract
    section 6 ("preserve the metadata whenever available") and are all
    optional: a field that the archive does not provide stays ``None``.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str | None = Field(
        None,
        description="Identifier of the original archive product (traceability).",
    )
    quality: float | None = Field(
        None,
        description="Quality value published for the product, when available.",
    )
    observed_at_source: str | None = Field(
        None,
        description=(
            "Original temporal reference exactly as published by the archive "
            "(not normalised), preserving the original scale."
        ),
    )
    timing_status: str | None = Field(
        None,
        description=(
            "How the observation time was resolved: 'observation_date', "
            "'mjd_observation_date', 'interval_start' or 'unresolved'. The "
            "release date of the product is never used as observation time."
        ),
    )
    instrument: str | None = Field(
        None, description="Instrument or facility name published for the product."
    )
    exposure_time_s: float | None = Field(
        None, description="Exposure time in seconds, when published."
    )
    wavelength_min_nm: float | None = Field(
        None, description="Lower wavelength bound of the band, in nanometres."
    )
    wavelength_max_nm: float | None = Field(
        None, description="Upper wavelength bound of the band, in nanometres."
    )
    wcs: dict[str, Any] | None = Field(
        None,
        description="Minimal World Coordinate System information of the product.",
    )
    contamination_flags: list[str] | None = Field(
        None, description="Contamination or quality flags published for the product."
    )
    source: str | None = Field(
        None, description="Provenance of the product (publisher or archive)."
    )
    original_file_url: str | None = Field(
        None, description="Reference to the original scientific file (FITS).",
    )
    data_release: str | None = Field(
        None, description="Data release the product belongs to, when published."
    )
    cutout_strategy: str | None = Field(
        None,
        description=(
            "How the displayed image was produced: 'remote_cutout' (cutout "
            "service) or 'local_download' (full file download plus local "
            "cutout)."
        ),
    )
    cutout_size_pixels: int | None = Field(
        None, description="Side of the generated cutout, in pixels."
    )
    visual_normalization: str | None = Field(
        None,
        description=(
            "Description of the display normalisation. The visual stretch is "
            "NOT a photometric measurement."
        ),
    )
    duplicate_count: int = Field(
        0,
        ge=0,
        description="Number of duplicate archive records merged into this entry.",
    )
    cutout_center_ra_deg: float | None = Field(
        None, description="Right ascension (ICRS, degrees) at the centre of the cutout."
    )
    cutout_center_dec_deg: float | None = Field(
        None, description="Declination (ICRS, degrees) at the centre of the cutout."
    )
    coverage_fraction: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of the requested square field that lies inside the "
            "detector footprint (from s_region); 1 = complete frame."
        ),
    )
    frame: str | None = Field(
        None,
        description=(
            "Geometry of the image: 'common_north_up' (resampled onto a TAN "
            "grid centred on the target, north up, east left)."
        ),
    )
    position_source: str | None = Field(
        None,
        description=(
            "'requested' (the position given in the query) or 'proper_motion' "
            "(position propagated to the epoch of this exposure)."
        ),
    )


class Observation(BaseModel):
    """A single observation returned by the archive."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(
        ...,
        description="Internal identifier of the observation, used in /api/images/{id}.",
    )
    observed_at: datetime | None = Field(
        None,
        description=(
            "Instant of the observation in UTC (ISO 8601). Null when the "
            "archive does not publish a resolvable observation time."
        ),
    )
    band: str | None = Field(
        None, description="Spectral band identifier published for the product."
    )
    detector: str | None = Field(
        None, description="Detector identifier published for the product."
    )
    image_url: str | None = Field(
        None,
        description="Relative URL of the processed image of this observation.",
    )
    metadata: ObservationMetadata = Field(
        default_factory=ObservationMetadata,
        description="Complementary metadata preserved from the archive.",
    )


class ObservationResponse(BaseModel):
    """Successful response of ``GET /api/observations``."""

    model_config = ConfigDict(extra="ignore")

    target: Target = Field(
        ..., description="Celestial coordinates requested by the user."
    )
    query: QueryParams = Field(
        ..., description="Parameters applied to the archive query."
    )
    total_observations: int = Field(
        ..., ge=0, description="Number of observations returned."
    )
    observations: list[Observation] = Field(
        default_factory=list,
        description="Observations ordered by observation time, oldest first.",
    )
    data_source: str | None = Field(
        None,
        description=(
            "'live' (queried now), 'cache' (recent cached answer) or "
            "'stale_cache' (IRSA unavailable: last cached answer, possibly outdated)."
        ),
    )
    data_cached_at: str | None = Field(
        None, description="When the cached answer was obtained (UTC ISO 8601)."
    )


class ErrorDetail(BaseModel):
    """Body of the ``error`` object used by every error response."""

    model_config = ConfigDict(extra="ignore")

    code: str = Field(
        ...,
        description=(
            "Machine readable error code: INVALID_PARAMETERS, "
            "NO_OBSERVATIONS_FOUND, SOURCE_UNAVAILABLE, PROCESSING_ERROR, "
            "IMAGE_NOT_FOUND or INTERNAL_ERROR."
        ),
    )
    message: str = Field(
        ..., description="Human readable description of the error."
    )


class ErrorResponse(BaseModel):
    """Error envelope defined in the API contract section 8."""

    model_config = ConfigDict(extra="ignore")

    error: ErrorDetail = Field(..., description="Error details.")


class HealthResponse(BaseModel):
    """Health check payload (no scientific content)."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(..., description="Service status, 'ok' when running.")
