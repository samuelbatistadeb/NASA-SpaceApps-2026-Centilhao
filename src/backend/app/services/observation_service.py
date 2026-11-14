"""Orchestration of the archive query and of the observation sequence.

The service is responsible for:

1. Querying the archive (with the disk cache in front of the client).
2. Translating the records of the archive into the schemas of the API
   contract.
3. Ordering the observations chronologically.
4. Building the processed image of an observation on demand.

It never invents a value: a field that the archive does not publish stays
``None`` (``docs/architecture/requirements.md`` RC-005).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from app.api.errors import (
    ImageNotFoundError,
    InvalidParametersError,
    NoObservationsFoundError,
)
from app.core.config import Settings
from app.schemas.observation import (
    Observation,
    ObservationMetadata,
    ObservationResponse,
    QueryParams,
    Target,
)
from app.services.cache import (
    NAMESPACE_IMAGES,
    NAMESPACE_OBSERVATIONS,
    NAMESPACE_QUERIES,
    DiskCache,
)
from app.services.cutout_service import CutoutRequest, CutoutService
from app.services.fits_processor import VISUAL_NORMALIZATION_DESCRIPTION
from app.services.irsa_client import IrsaClient, _to_float, _to_str, pick, radius_from_fov

logger = logging.getLogger(__name__)

#: Reference instant used to keep the ordering deterministic.
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass
class ObservationEntry:
    """Everything needed to rebuild the image of an observation."""

    observation_id: str
    record: dict[str, Any]
    ra_deg: float
    dec_deg: float
    fov_arcmin: float

    def to_dict(self) -> dict[str, Any]:
        """Serialisable representation used by the disk cache."""
        return {
            "observation_id": self.observation_id,
            "record": self.record,
            "ra_deg": self.ra_deg,
            "dec_deg": self.dec_deg,
            "fov_arcmin": self.fov_arcmin,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservationEntry":
        """Rebuild an entry from its serialised representation."""
        return cls(
            observation_id=str(payload["observation_id"]),
            record=dict(payload.get("record") or {}),
            ra_deg=float(payload["ra_deg"]),
            dec_deg=float(payload["dec_deg"]),
            fov_arcmin=float(payload["fov_arcmin"]),
        )


@dataclass
class ImageResult:
    """The processed image of an observation."""

    content: bytes
    content_type: str = "image/png"
    metadata: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class _BuiltObservation:
    """An observation together with the archive record that produced it."""

    observation: Observation
    record: dict[str, Any]


class ObservationService:
    """Coordinate the archive query, the ordering and the image generation."""

    def __init__(
        self,
        client: IrsaClient,
        cache: DiskCache,
        cutout_service: CutoutService,
        settings: Settings,
    ) -> None:
        self._client = client
        self._cache = cache
        self._cutout_service = cutout_service
        self._settings = settings
        self._registry: dict[str, ObservationEntry] = {}

    # -- public API -------------------------------------------------------------
    def search(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> ObservationResponse:
        """Query the archive and return the observations in chronological order.

        Raises:
            InvalidParametersError: The parameters are outside the accepted
                ranges.
            NoObservationsFoundError: The archive returned no product.
            SourceUnavailableError: The archive could not be reached.
        """
        self._validate(ra_deg, dec_deg, fov_arcmin)

        records = self._query_records(ra_deg, dec_deg, fov_arcmin)
        if not records:
            raise NoObservationsFoundError(
                "Nenhuma observação foi encontrada para os parâmetros informados."
            )

        built = self._build_observations(records, ra_deg, dec_deg, fov_arcmin)
        built = self._sort_observations(built)
        built = self._remove_duplicates(built)
        observations = [item.observation for item in built]

        self._register(built, ra_deg, dec_deg, fov_arcmin)

        return ObservationResponse(
            target=Target(ra_deg=ra_deg, dec_deg=dec_deg),
            query=QueryParams(fov_arcmin=fov_arcmin),
            total_observations=len(observations),
            observations=observations,
        )

    def get_image(self, observation_id: str) -> ImageResult:
        """Return the processed image of an observation.

        Raises:
            ImageNotFoundError: The observation is unknown or has no image.
            SourceUnavailableError: The product could not be retrieved.
            ProcessingError: The product could not be processed.
        """
        entry = self._registry.get(observation_id)
        if entry is None:
            cached = self._cache.get_json(NAMESPACE_OBSERVATIONS, observation_id)
            if cached:
                entry = ObservationEntry.from_dict(cached)
                self._registry[observation_id] = entry
        if entry is None:
            raise ImageNotFoundError(
                "Nenhuma imagem processada está disponível para esta observação."
            )

        request = self._build_cutout_request(entry)
        cache_key = self._image_cache_key(entry)
        content = self._cache.get_bytes(NAMESPACE_IMAGES, cache_key)
        if content is not None:
            metadata = self._cache.get_json(NAMESPACE_OBSERVATIONS, f"{observation_id}.meta")
            return ImageResult(
                content=content,
                metadata=dict(metadata or {}),
                headers=self._image_headers(dict(metadata or {})),
            )

        result = self._cutout_service.build_cutout(request)
        from app.services.fits_processor import render_png

        content = render_png(result.data)
        metadata = dict(result.metadata)
        metadata.setdefault("visual_normalization", VISUAL_NORMALIZATION_DESCRIPTION)
        metadata.setdefault("cutout_strategy", result.strategy.value)

        self._cache.set_bytes(NAMESPACE_IMAGES, cache_key, content)
        self._cache.set_json(NAMESPACE_OBSERVATIONS, f"{observation_id}.meta", metadata)

        return ImageResult(
            content=content,
            metadata=metadata,
            headers=self._image_headers(metadata),
        )

    # -- internals --------------------------------------------------------------
    def _validate(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> None:
        """Validate the query parameters against the configured limits."""
        if not (self._settings.min_ra_deg <= ra_deg < self._settings.max_ra_deg):
            raise InvalidParametersError(
                "Ascensão Reta deve estar entre 0 e 360 graus (exclusive)."
            )
        if not (self._settings.min_dec_deg <= dec_deg <= self._settings.max_dec_deg):
            raise InvalidParametersError(
                "Declinação deve estar entre -90 e +90 graus."
            )
        if not (
            self._settings.min_fov_arcmin
            <= fov_arcmin
            <= self._settings.max_fov_arcmin
        ):
            raise InvalidParametersError(
                "Campo de visão deve estar entre "
                f"{self._settings.min_fov_arcmin} e {self._settings.max_fov_arcmin} "
                "minutos de arco."
            )

    def _query_records(
        self, ra_deg: float, dec_deg: float, fov_arcmin: float
    ) -> list[dict[str, Any]]:
        """Return the records of the archive, using the cache when possible."""
        cache_key = self._query_cache_key(ra_deg, dec_deg, fov_arcmin)
        cached = self._cache.get_json(NAMESPACE_QUERIES, cache_key)
        if cached is not None:
            logger.info("Query cache hit for %s", cache_key)
            return [dict(item) for item in cached]

        records = self._client.query_by_position(
            ra_deg,
            dec_deg,
            radius_from_fov(fov_arcmin),
            fov_arcmin=fov_arcmin,
        )
        self._cache.set_json(NAMESPACE_QUERIES, cache_key, records)
        return records

    def _query_cache_key(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> str:
        """Stable key of a query (disk cache)."""
        return DiskCache.make_key(
            "query",
            f"{ra_deg:.6f}",
            f"{dec_deg:.6f}",
            f"{fov_arcmin:.6f}",
            self._client.sia2_base_url,
        )

    def _image_cache_key(self, entry: ObservationEntry) -> str:
        """Stable key of a generated image (disk cache)."""
        record = entry.record
        return DiskCache.make_key(
            "image",
            str(pick(record, "product_id") or ""),
            str(pick(record, "band") or ""),
            str(pick(record, "detector") or ""),
            f"{entry.ra_deg:.6f}",
            f"{entry.dec_deg:.6f}",
            f"{entry.fov_arcmin:.6f}",
            self._settings.cutout_mode,
        )

    def _build_observations(
        self,
        records: list[dict[str, Any]],
        ra_deg: float,
        dec_deg: float,
        fov_arcmin: float,
    ) -> list[_BuiltObservation]:
        """Translate the archive records into the schemas of the contract."""
        built: list[_BuiltObservation] = []
        for record in records:
            product_id = _to_str(pick(record, "product_id"))
            band = _to_str(pick(record, "band"))
            detector = _to_str(pick(record, "detector"))
            observed_at, timing_status, observed_at_source = self._extract_observed_at(record)

            metadata = ObservationMetadata(
                product_id=product_id,
                quality=_to_float(pick(record, "quality")),
                observed_at_source=observed_at_source,
                timing_status=timing_status,
                instrument=_to_str(pick(record, "instrument")),
                exposure_time_s=_to_float(pick(record, "exposure")),
                wavelength_min_nm=_to_float(pick(record, "em_min")),
                wavelength_max_nm=_to_float(pick(record, "em_max")),
                wcs=self._extract_wcs(record),
                contamination_flags=self._extract_flags(record),
                source=_to_str(pick(record, "provenance")),
                original_file_url=_to_str(pick(record, "access_url")),
                data_release=_to_str(pick(record, "data_release")),
                cutout_strategy=self._strategy_value(record),
                cutout_size_pixels=None,
                visual_normalization=VISUAL_NORMALIZATION_DESCRIPTION,
                duplicate_count=0,
            )

            observation_id = self._build_observation_id(product_id, band, detector)
            observation = Observation(
                id=observation_id,
                observed_at=observed_at,
                band=band,
                detector=detector,
                image_url=f"/api/images/{observation_id}",
                metadata=metadata,
            )
            built.append(_BuiltObservation(observation=observation, record=record))
        return built

    def _strategy_value(self, record: Mapping[str, Any]) -> str | None:
        """Return the cutout strategy that would be applied to the product."""
        request = CutoutRequest(
            product_id=_to_str(pick(record, "product_id")),
            access_url=_to_str(pick(record, "access_url")),
            cutout_service_ref=_to_str(pick(record, "cutout_service_ref")),
        )
        try:
            return self._cutout_service.decide_strategy(request).value
        except Exception:  # noqa: BLE001 - the strategy must never break a query
            return None

    @staticmethod
    def _build_observation_id(
        product_id: str | None, band: str | None, detector: str | None
    ) -> str:
        """Return the deterministic internal identifier of an observation."""
        canonical = f"{product_id or ''}|{band or ''}|{detector or ''}"
        digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
        return f"obs_{digest}"

    @staticmethod
    def _extract_observed_at(
        record: Mapping[str, Any],
    ) -> tuple[datetime | None, str, str | None]:
        """Resolve the observation instant published by the archive.

        Returns:
            The instant (UTC), the criterion used and the original value.
        """
        raw_mjd = pick(record, "mjd_obs")
        mjd = _to_float(raw_mjd)
        if mjd is not None:
            from datetime import timedelta

            instant = _EPOCH + timedelta(days=mjd - 40587.0)
            return instant, "mjd_observation_date", str(raw_mjd)

        for alias, criterion in (("t_min", "observation_date"), ("t_max", "interval_start")):
            raw = _to_str(pick(record, alias))
            if not raw:
                continue
            parsed = _parse_datetime(raw)
            if parsed is not None:
                return parsed, criterion, raw

        release = _to_str(pick(record, "release_date"))
        if release:
            parsed = _parse_datetime(release)
            if parsed is not None:
                return parsed, "release_date_fallback", release

        return None, "unresolved", None

    @staticmethod
    def _extract_wcs(record: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return the minimal WCS information published for the product."""
        raw = pick(record, "wcs")
        if not isinstance(raw, Mapping):
            return None
        wcs: dict[str, Any] = {}
        for key in (
            "ctype",
            "crval",
            "crpix",
            "cdelt",
            "cunit",
            "radesys",
            "equinox",
            "pixscale",
            "shape",
        ):
            if key not in raw:
                continue
            value = raw[key]
            if isinstance(value, (str, int, float, bool)) or value is None:
                wcs[key] = value
            elif isinstance(value, (list, tuple)):
                wcs[key] = [item for item in value if isinstance(item, (str, int, float, bool))]
        return wcs or None

    @staticmethod
    def _extract_flags(record: Mapping[str, Any]) -> list[str] | None:
        """Return the contamination or quality flags published for the product."""
        raw = pick(record, "contamination")
        if raw is None:
            return None
        if isinstance(raw, str):
            flags = [item.strip() for item in raw.replace(";", ",").split(",")]
            flags = [item for item in flags if item]
            return flags or None
        if isinstance(raw, (list, tuple)):
            flags = [str(item).strip() for item in raw]
            flags = [item for item in flags if item]
            return flags or None
        return None

    @staticmethod
    def _sort_observations(
        built: list[_BuiltObservation],
    ) -> list[_BuiltObservation]:
        """Order the observations chronologically (oldest first)."""
        return sorted(
            built,
            key=lambda item: (
                item.observation.observed_at is None,
                item.observation.observed_at or _EPOCH,
                item.observation.metadata.product_id or "",
            ),
        )

    @staticmethod
    def _remove_duplicates(
        built: list[_BuiltObservation],
    ) -> list[_BuiltObservation]:
        """Remove repeated products, counting the duplicates."""
        seen: dict[tuple[str, str, str], _BuiltObservation] = {}
        unique: list[_BuiltObservation] = []
        for item in built:
            observation = item.observation
            key = (
                observation.metadata.product_id or "",
                observation.band or "",
                observation.detector or "",
            )
            if not key[0]:
                unique.append(item)
                continue
            if key in seen:
                seen[key].observation.metadata.duplicate_count += 1
                continue
            seen[key] = item
            unique.append(item)
        return unique

    def _register(
        self,
        built: list[_BuiltObservation],
        ra_deg: float,
        dec_deg: float,
        fov_arcmin: float,
    ) -> None:
        """Keep the resolved records so that the image endpoint can find them."""
        for item in built:
            entry = ObservationEntry(
                observation_id=item.observation.id,
                record=dict(item.record),
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                fov_arcmin=fov_arcmin,
            )
            self._registry[item.observation.id] = entry
            self._cache.set_json(
                NAMESPACE_OBSERVATIONS, item.observation.id, entry.to_dict()
            )

    def _build_cutout_request(self, entry: ObservationEntry) -> CutoutRequest:
        """Build the request used to retrieve the pixels of an observation."""
        record = entry.record
        return CutoutRequest(
            product_id=_to_str(pick(record, "product_id")),
            access_url=_to_str(pick(record, "access_url")),
            ra_deg=entry.ra_deg,
            dec_deg=entry.dec_deg,
            fov_arcmin=entry.fov_arcmin,
            pixel_scale_arcsec=_to_float(pick(record, "pixel_scale")),
            cutout_service_ref=_to_str(pick(record, "cutout_service_ref")),
        )

    @staticmethod
    def _image_headers(metadata: Mapping[str, Any]) -> dict[str, str]:
        """Headers that identify the image as a processed visual representation."""
        headers = {
            "X-SpherEx-Image-Type": "visual-representation",
            "Cache-Control": "no-store",
        }
        normalization = metadata.get("visual_normalization")
        if normalization:
            headers["X-SpherEx-Normalization"] = str(normalization)
        strategy = metadata.get("cutout_strategy")
        if strategy:
            headers["X-SpherEx-Cutout-Strategy"] = str(strategy)
        return headers


def _parse_datetime(text: str) -> datetime | None:
    """Parse an ISO 8601 timestamp, accepting the ``Z`` suffix."""
    candidate = text.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
