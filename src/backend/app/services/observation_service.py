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
import io
import logging
import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

import numpy as np

from app.api.errors import (
    ImageNotFoundError,
    InvalidParametersError,
    NoObservationsFoundError,
    ProcessingError,
    SourceUnavailableError,
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
from app.services.irsa_client import (
    FIELD_ALIASES,
    IrsaClient,
    _to_float,
    _to_str,
    extract_detector,
    pick,
    radius_from_fov,
)
from app.services.astrometry import (
    ProperMotion,
    jyear_from_datetime,
    propagate_position,
)
from app.services import fits_processor
from app.services.common_frame import (
    SPHEREX_PIXEL_SCALE_ARCSEC,
    FrameImage,
    frame_side_pixels,
    frame_wcs,
    project_to_frame,
)
from app.services.spectral import (
    WAVELENGTH_SOURCE,
    WCS_WAVE_TAIL_BYTES,
    aperture_photometry,
    calibration_key,
    parse_wcs_wave_tail,
    wavelength_at,
)
from app.services.spherex_flags import (
    INFORMATIONAL_NAMES,
    bits_from_header,
    contamination_mask,
    decode,
    fraction_by_flag,
)
from app.services.sky_coverage import (
    footprint_coverage,
    parse_s_region,
    polygon_contains_position,
)

logger = logging.getLogger(__name__)

#: Display frame of the images: TAN, north up, east left, centred on the target.
FRAME_COMMON = "common_north_up"
#: Bumped whenever the rendering of the cached images changes.
_IMAGE_CACHE_VERSION = "frame-v2"  # v2: frames carry FLAGS and VARIANCE

#: Fields of view (arcmin) evaluated by :meth:`ObservationService.coverage`.
COVERAGE_FOVS_ARCMIN: tuple[float, ...] = (1.0, 2.0, 3.0, 5.0, 10.0, 15.0, 30.0)
#: Coverage from which a frame counts as complete (sampling tolerance).
COMPLETE_COVERAGE = 0.999
#: Maximum number of observations combined in one composite (cost guard:
#: each uncached frame is one IBE cutout).
MAX_COMPOSITE_FRAMES = 40

#: ``position_source`` values published in the metadata of each observation.
POSITION_REQUESTED = "requested"
POSITION_PROPER_MOTION = "proper_motion"

#: Middle of the SPHEREx survey window used to centre the archive query of a
#: moving target, and half of the window covered by the widened search cone.
#: DR1 epochs observed so far span 2025.3-2026.8 (docs/science/target-catalog.md).
_MOTION_QUERY_EPOCH_JYEAR = 2026.0
_MOTION_QUERY_HALF_SPAN_YEARS = 1.5

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


@dataclass(frozen=True)
class DataSource:
    """Where the archive records of an answer came from."""

    status: str  # "live" (IRSA now), "cache" (fresh cache), "stale_cache" (IRSA down)
    cached_at: float | None = None  # unix time of the cached answer

    @property
    def cached_at_iso(self) -> str | None:
        if self.cached_at is None:
            return None
        return datetime.fromtimestamp(self.cached_at, tz=timezone.utc).isoformat()


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
    #: Cutout centre (RA, Dec) of this observation; ``None`` = query position.
    center: tuple[float, float] | None = None


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
        # One lock per image cache key: concurrent requests for the same image
        # (e.g. main viewer + first thumbnail) wait for a single cutout.
        self._image_locks: dict[str, threading.Lock] = {}
        self._image_locks_guard = threading.Lock()
        #: WCS-WAVE tables by calibration key (detector + processing run).
        self._wave_tables: dict[str, Any] = {}

    # -- public API -------------------------------------------------------------
    def search(
        self,
        ra_deg: float,
        dec_deg: float,
        fov_arcmin: float,
        motion: ProperMotion | None = None,
    ) -> ObservationResponse:
        """Query the archive and return the observations in chronological order.

        Args:
            ra_deg: Right ascension (ICRS, degrees); with ``motion``, the
                position at ``motion.ref_epoch_jyear``.
            dec_deg: Declination (ICRS, degrees), same convention.
            fov_arcmin: Side of the cutout, in arcminutes.
            motion: Optional proper motion of the target. When given, every
                observation is filtered and cut at the position propagated to
                its own epoch (DECISÃO 007, item 8).

        Raises:
            InvalidParametersError: The parameters are outside the accepted
                ranges.
            NoObservationsFoundError: The archive returned no product.
            SourceUnavailableError: The archive could not be reached.
        """
        self._validate(ra_deg, dec_deg, fov_arcmin)

        query_ra, query_dec, margin_deg = ra_deg, dec_deg, 0.0
        if motion is not None:
            # Centre the cone on the middle of the SPHEREx survey and widen it by
            # the motion over half the window, so every epoch is covered.
            query_ra, query_dec = propagate_position(
                ra_deg, dec_deg, motion, _MOTION_QUERY_EPOCH_JYEAR
            )
            margin_deg = motion.total_masyr * _MOTION_QUERY_HALF_SPAN_YEARS / 3_600_000.0

        records, source = self._query_records(query_ra, query_dec, fov_arcmin, margin_deg)
        if not records:
            raise NoObservationsFoundError(
                "Nenhuma observação foi encontrada para os parâmetros informados."
            )

        center_of = self._center_function(ra_deg, dec_deg, motion)
        records = self._filter_by_footprint(records, ra_deg, dec_deg, center_of=center_of)
        if not records:
            raise NoObservationsFoundError(
                "Nenhuma observação cobre a posição informada: os produtos "
                "encontrados apenas tocam a borda da região consultada."
            )

        query_signature = self._query_signature(ra_deg, dec_deg, fov_arcmin, motion)
        built = self._build_observations(
            records, ra_deg, dec_deg, fov_arcmin,
            center_of=center_of, query_signature=query_signature,
        )
        built = self._sort_observations(built)
        built = self._remove_duplicates(built)
        observations = [item.observation for item in built]

        self._register(built, ra_deg, dec_deg, fov_arcmin)

        return ObservationResponse(
            target=Target(ra_deg=ra_deg, dec_deg=dec_deg),
            query=QueryParams(fov_arcmin=fov_arcmin),
            total_observations=len(observations),
            observations=observations,
            data_source=source.status,
            data_cached_at=source.cached_at_iso,
        )

    def coverage(
        self,
        ra_deg: float,
        dec_deg: float,
        motion: ProperMotion | None = None,
        fovs: tuple[float, ...] = COVERAGE_FOVS_ARCMIN,
    ) -> dict[str, Any]:
        """How many frames are complete/partial for each field of view.

        Computed from the detector polygons only (no image is downloaded), so
        the interface can show the cost/benefit of each FOV before searching.
        """
        self._validate(ra_deg, dec_deg, max(fovs))
        query_ra, query_dec, margin_deg = ra_deg, dec_deg, 0.0
        if motion is not None:
            query_ra, query_dec = propagate_position(
                ra_deg, dec_deg, motion, _MOTION_QUERY_EPOCH_JYEAR
            )
            margin_deg = motion.total_masyr * _MOTION_QUERY_HALF_SPAN_YEARS / 3_600_000.0
        records, source = self._query_records(query_ra, query_dec, max(fovs), margin_deg)

        center_of = self._center_function(ra_deg, dec_deg, motion)
        records = self._filter_by_footprint(records, ra_deg, dec_deg, center_of=center_of)
        records = self._unique_products(records)
        prepared = []
        epochs = []
        for record in records:
            ra, dec, _ = center_of(record)
            prepared.append((parse_s_region(record.get("s_region")), ra, dec))
            observed_at = self._extract_observed_at(record)[0]
            if observed_at is not None:
                epochs.append(jyear_from_datetime(observed_at))

        scale = SPHEREX_PIXEL_SCALE_ARCSEC
        rows = []
        for fov in fovs:
            complete = partial = 0
            for polygon, ra, dec in prepared:
                if polygon is None:
                    continue
                if footprint_coverage(polygon, ra, dec, fov) >= COMPLETE_COVERAGE:
                    complete += 1
                else:
                    partial += 1
            side = frame_side_pixels(fov, scale)
            ibe_side = math.ceil(fov * 60.0 * 1.5 / scale)
            rows.append({
                "fov_arcmin": fov,
                "pixels": side,
                "observations": len(prepared),
                "complete": complete,
                "partial": partial,
                # IMAGE HDU only (DECISÃO 012): float32 pixels + ~3 header blocks.
                "estimated_kb_per_image": round((ibe_side**2 * 4 + 3 * 2880) / 1024, 1),
            })

        motion_arcsec = None
        if motion is not None and len(epochs) >= 2:
            motion_arcsec = round(motion.total_masyr * (max(epochs) - min(epochs)) / 1000.0, 2)
        minimum = max(3.0, 4.0 * (motion_arcsec or 0.0) / 60.0)
        recommended = next((f for f in fovs if f >= minimum), fovs[-1])
        return {
            "fovs": rows,
            "recommended_fov_arcmin": recommended,
            "motion_arcsec_over_survey": motion_arcsec,
            "pixel_scale_arcsec": scale,
            "data_source": source.status,
            "data_cached_at": source.cached_at_iso,
        }

    def composite(
        self, op: str, ids_a: list[str], ids_b: list[str] | None = None
    ) -> ImageResult:
        """Combine observations already aligned on the common frame.

        * ``mean``: average of the frames of group A (same detector only), to
          raise the signal-to-noise ratio. Units stay MJy/sr.
        * ``diff``: mean(A) - mean(B), e.g. early vs late epochs, so that a
          source that moved shows up as a bright/dark pair.

        Each frame has its median (sky background, which changes with the
        zodiacal light between epochs) subtracted before combining. Pixels
        without data in a frame do not contribute; a pixel is "no data" only
        when no frame covers it.
        """
        ids_b = ids_b or []
        if op not in ("mean", "diff"):
            raise InvalidParametersError("A operação deve ser 'mean' ou 'diff'.")
        if not ids_a or (op == "diff" and not ids_b):
            raise InvalidParametersError(
                "Informe as observações do grupo A (e do grupo B para a diferença)."
            )
        if op == "mean" and ids_b:
            raise InvalidParametersError("A média usa apenas o grupo A.")
        total = len(ids_a) + len(ids_b)
        if total > MAX_COMPOSITE_FRAMES:
            raise InvalidParametersError(
                f"Combine no máximo {MAX_COMPOSITE_FRAMES} observações por vez."
            )

        cache_key = DiskCache.make_key(
            "composite", op, ",".join(sorted(ids_a)), ",".join(sorted(ids_b)),
            _IMAGE_CACHE_VERSION,
        )
        cached = self._cache.get_bytes(NAMESPACE_IMAGES, cache_key, allow_stale=True)
        meta_key = f"{cache_key}.meta"
        if cached is not None:
            metadata = dict(self._cache.get_json(NAMESPACE_OBSERVATIONS, meta_key, allow_stale=True) or {})
            return ImageResult(content=cached, metadata=metadata,
                               headers=self._composite_headers(metadata))

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=self._settings.max_concurrent_product_requests) as pool:
            frames_a = list(pool.map(self.get_frame, ids_a))
            frames_b = list(pool.map(self.get_frame, ids_b))

        all_frames = frames_a + frames_b
        shapes = {frame.data.shape for frame, _ in all_frames}
        if len(shapes) != 1:
            raise InvalidParametersError(
                "As observações combinadas precisam ter o mesmo campo de visão."
            )
        detectors = sorted({str(extract_detector(entry.record) or "?") for _, entry in all_frames})
        if len(detectors) > 1:
            raise InvalidParametersError(
                "Combine observações de um único detector: cada detector vê outra "
                f"faixa do infravermelho (recebido: {', '.join(detectors)})."
            )

        def stack(group):
            arrays = []
            for frame, _ in group:
                data = np.where(frame.outside, np.nan, frame.data)
                if "flags" in frame.extras:
                    # Cosmic rays, bad pixels, ghosts... would look like changes.
                    data = np.where(contamination_mask(frame.extras["flags"]), np.nan, data)
                background = np.nanmedian(data) if np.isfinite(data).any() else 0.0
                arrays.append(data - background)
            cube = np.stack(arrays)
            counts = np.isfinite(cube).sum(axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = np.nansum(cube, axis=0) / np.where(counts == 0, 1, counts)
            mean[counts == 0] = np.nan
            no_data = np.stack([frame.outside for frame, _ in group]).all(axis=0)
            return mean, no_data, counts

        mean_a, outside_a, counts_a = stack(frames_a)
        if op == "mean":
            result, outside = mean_a, outside_a
            limits = None
        else:
            mean_b, outside_b, _ = stack(frames_b)
            result = mean_a - mean_b
            outside = outside_a | outside_b
            valid = np.isfinite(result) & ~outside
            spread = float(np.percentile(np.abs(result[valid]), 99.0)) if valid.any() else 1.0
            limits = (-spread or -1.0, spread or 1.0)

        content = fits_processor.render_frame_png(result, outside, limits=limits)
        epochs = sorted(
            jyear_from_datetime(t) for t in (
                self._extract_observed_at(entry.record)[0] for _, entry in all_frames
            ) if t is not None
        )
        metadata = {
            "composite_op": op,
            "frames_a": len(frames_a),
            "frames_b": len(frames_b),
            "detector": detectors[0],
            "frame": FRAME_COMMON,
            "background": "median of each frame subtracted",
            "masked": "pixels with contamination FLAGS excluded",
            "epoch_span_jyear": [round(epochs[0], 4), round(epochs[-1], 4)] if epochs else None,
            "max_frames_per_pixel": int(counts_a.max()) if counts_a.size else 0,
            "difference_limits": list(limits) if limits else None,
        }
        self._cache.set_bytes(NAMESPACE_IMAGES, cache_key, content)
        self._cache.set_json(NAMESPACE_OBSERVATIONS, meta_key, metadata)
        return ImageResult(content=content, metadata=metadata,
                           headers=self._composite_headers(metadata))

    @staticmethod
    def _composite_headers(metadata: Mapping[str, Any]) -> dict[str, str]:
        headers = {
            "X-SpherEx-Image-Type": "composite-visual-representation",
            "X-SpherEx-Frame": "common-north-up",
            "Cache-Control": "no-store",
        }
        for key, header in (
            ("composite_op", "X-SpherEx-Composite-Op"),
            ("frames_a", "X-SpherEx-Frames-A"),
            ("frames_b", "X-SpherEx-Frames-B"),
            ("detector", "X-SpherEx-Detector"),
        ):
            if metadata.get(key) is not None:
                headers[header] = str(metadata[key])
        return headers

    def quality(self, observation_id: str) -> dict[str, Any]:
        """Contamination FLAGS at the target and over the frame of an observation.

        Available once the image was generated (the FLAGS travel with it).
        """
        entry = self._entry(observation_id)
        cache_key = self._image_cache_key(entry)
        frame = self._cached_frame(entry, cache_key)
        if frame is None or "flags" not in frame.extras:
            raise ImageNotFoundError(
                "A qualidade fica disponível depois que a imagem da observação é gerada."
            )
        _, flags_header = self._cached_headers(cache_key)
        bits = bits_from_header(flags_header)
        flags = frame.extras["flags"]
        valid = ~frame.outside
        centre = (flags.shape[0] - 1) // 2
        box = flags[max(centre - 1, 0):centre + 2, max(centre - 1, 0):centre + 2]
        value = int(np.bitwise_or.reduce(box.ravel())) if box.size else 0
        at_target = decode(value, bits)
        return {
            "observation_id": observation_id,
            "contaminated_at_target": any(
                b.name not in INFORMATIONAL_NAMES for b in at_target
            ),
            "flags_at_target": [
                {"bit": b.bit, "name": b.name, "description": b.description}
                for b in at_target if b.name not in INFORMATIONAL_NAMES
            ],
            "informational": [b.name for b in at_target if b.name in INFORMATIONAL_NAMES],
            "frame_flagged_fraction": fraction_by_flag(flags, valid, bits),
            "target_box_pixels": int(box.size),
            "source": "FLAGS HDU (SPHEREx Explanatory Supplement v2.0, Tabela 16)",
        }

    def spectrum(
        self,
        ra_deg: float,
        dec_deg: float,
        motion: ProperMotion | None = None,
        aperture_arcsec: float = 9.0,
        max_exposures: int = 60,
    ) -> dict[str, Any]:
        """Spectrum of a sky position built from many exposures.

        Each exposure sees the position at another place of the linear
        variable filter, hence at another wavelength. For each selected
        exposure: aperture mean minus the local background (annulus), error
        from the VARIANCE plane, wavelength and bandwidth from WCS-WAVE at the
        detector pixel where the position falls.
        """
        scale = SPHEREX_PIXEL_SCALE_ARCSEC
        radius_px = max(aperture_arcsec / scale, 0.5)
        fov = max(1.0, math.ceil(8.0 * radius_px * scale / 60.0 * 10) / 10)
        response = self.search(ra_deg, dec_deg, fov, motion=motion)
        chosen = self._spread_exposures(response.observations, max_exposures)

        from concurrent.futures import ThreadPoolExecutor

        def measure(observation: Observation) -> dict[str, Any] | None:
            try:
                frame, entry = self.get_frame(observation.id)
            except Exception as exc:  # noqa: BLE001 - one bad exposure must not stop the spectrum
                logger.info("Spectrum: skipping %s (%s)", observation.id, exc)
                return None
            point = aperture_photometry(frame, radius_px)
            if point is None:
                return None
            wave = self._wavelength_for(entry, frame)
            if wave is None:
                return None
            names = [b.name for b in decode(point.pop("flags_value"))
                     if b.name not in INFORMATIONAL_NAMES]
            return {
                "wavelength_um": round(wave[0], 5),
                "bandwidth_um": round(wave[1], 5),
                **point,
                "detector": observation.detector,
                "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
                "observation_id": observation.id,
                "flagged": bool(names),
                "flags": names,
            }

        with ThreadPoolExecutor(max_workers=self._settings.max_concurrent_product_requests) as pool:
            points = [p for p in pool.map(measure, chosen) if p is not None]
        points.sort(key=lambda p: p["wavelength_um"])
        return {
            "unit": "MJy/sr",
            "points": points,
            "n_exposures": len(chosen),
            "aperture_arcsec": aperture_arcsec,
            "frame_fov_arcmin": fov,
            "wavelength_source": WAVELENGTH_SOURCE,
            "flux_definition": (
                "média do brilho superficial na abertura menos a mediana de um anel "
                "de fundo (2 a 3 raios); erro a partir do plano VARIANCE"
            ),
            "data_source": response.data_source,
        }

    @staticmethod
    def _spread_exposures(observations: list[Observation], limit: int) -> list[Observation]:
        """Up to ``limit`` complete exposures, spread over detectors and time."""
        complete = [o for o in observations if (o.metadata.coverage_fraction or 0) >= COMPLETE_COVERAGE]
        pool = complete or list(observations)
        by_detector: dict[str, list[Observation]] = {}
        for observation in pool:  # chronological order is kept inside each detector
            by_detector.setdefault(observation.detector or "?", []).append(observation)
        chosen: list[Observation] = []
        per_detector = max(1, limit // max(len(by_detector), 1))
        for group in by_detector.values():
            step = max(len(group) / per_detector, 1.0)
            chosen.extend(group[int(i * step)] for i in range(min(per_detector, len(group))))
        return chosen[:limit]

    def _wavelength_for(
        self, entry: ObservationEntry, frame: FrameImage
    ) -> tuple[float, float] | None:
        """Wavelength/bandwidth (µm) at the detector pixel of the frame centre."""
        if frame.center_source_xy is None:
            return None
        image_header, _ = self._cached_headers(self._image_cache_key(entry))
        access_url = _to_str(pick(entry.record, "access_url"))
        if image_header is None or not access_url:
            return None
        table = self._wcs_wave_table(access_url, extract_detector(entry.record))
        if table is None:
            return None
        return wavelength_at(image_header, table, *frame.center_source_xy)

    def _wcs_wave_table(self, access_url: str, detector: str | None):
        """WCS-WAVE table of a product; one download per (detector, processing run)."""
        from astropy.io import fits

        key = calibration_key(access_url, detector)
        with self._image_locks_guard:
            if key in self._wave_tables:
                return self._wave_tables[key]
        cache_key = DiskCache.make_key("wcs-wave", key)
        payload = self._cache.get_bytes(NAMESPACE_IMAGES, cache_key, allow_stale=True)
        table = None
        if payload is not None:
            table = parse_wcs_wave_tail(payload)
        if table is None:
            try:
                tail = self._client.fetch_tail(access_url, WCS_WAVE_TAIL_BYTES)
            except Exception as exc:  # noqa: BLE001 - wavelength unknown, point skipped
                logger.warning("WCS-WAVE unavailable for %s: %s", access_url, exc)
                return None
            table = parse_wcs_wave_tail(tail)
            if table is not None:
                self._cache.set_bytes(NAMESPACE_IMAGES, cache_key, tail)
        with self._image_locks_guard:
            self._wave_tables[key] = table
        return table

    def _center_function(
        self, ra_deg: float, dec_deg: float, motion: ProperMotion | None
    ) -> Callable[[Mapping[str, Any]], tuple[float, float, str]]:
        """Return ``record -> (ra, dec, position_source)`` for this query."""

        def center_of(record: Mapping[str, Any]) -> tuple[float, float, str]:
            if motion is None:
                return ra_deg, dec_deg, POSITION_REQUESTED
            observed_at = self._extract_observed_at(record)[0]
            if observed_at is None:
                return ra_deg, dec_deg, POSITION_REQUESTED
            ra, dec = propagate_position(
                ra_deg, dec_deg, motion, jyear_from_datetime(observed_at)
            )
            return ra, dec, POSITION_PROPER_MOTION

        return center_of

    @staticmethod
    def _unique_products(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop repeated products (same identifier, band and detector)."""
        seen: set[tuple[str, str, str]] = set()
        unique = []
        for record in records:
            key = (
                str(pick(record, "product_id") or ""),
                str(pick(record, "band") or ""),
                str(extract_detector(record) or ""),
            )
            if key[0] and key in seen:
                continue
            seen.add(key)
            unique.append(record)
        return unique

    def get_image(self, observation_id: str) -> ImageResult:
        """Return the processed image of an observation.

        Raises:
            ImageNotFoundError: The observation is unknown or has no image.
            SourceUnavailableError: The product could not be retrieved.
            ProcessingError: The product could not be processed.
        """
        entry = self._entry(observation_id)
        cache_key = self._image_cache_key(entry)
        cached = self._cached_image(observation_id, cache_key)
        if cached is not None:
            return cached

        with self._image_lock(cache_key):
            # Another request may have produced the image while we waited.
            cached = self._cached_image(observation_id, cache_key)
            if cached is not None:
                return cached
            return self._build_image(observation_id, cache_key, entry)

    def get_frame(self, observation_id: str) -> tuple[FrameImage, ObservationEntry]:
        """Return the observation resampled onto the common frame (cached).

        Used to combine epochs (sum, difference). Raises
        :class:`ProcessingError` when the product has no celestial WCS.
        """
        entry = self._entry(observation_id)
        cache_key = self._image_cache_key(entry)
        frame = self._cached_frame(entry, cache_key)
        if frame is not None:
            return frame, entry
        with self._image_lock(cache_key):
            frame = self._cached_frame(entry, cache_key)
            if frame is None:
                self._build_image(observation_id, cache_key, entry)
                frame = self._cached_frame(entry, cache_key)
        if frame is None:
            raise ProcessingError(
                "Esta observação não pode ser alinhada ao quadro comum.",
                detail=f"no celestial WCS for {observation_id}",
            )
        return frame, entry

    def _entry(self, observation_id: str) -> ObservationEntry:
        """Find a registered observation (memory, then disk cache)."""
        entry = self._registry.get(observation_id)
        if entry is None:
            cached = self._cache.get_json(NAMESPACE_OBSERVATIONS, observation_id, allow_stale=True)
            if cached:
                entry = ObservationEntry.from_dict(cached)
                self._registry[observation_id] = entry
        if entry is None:
            raise ImageNotFoundError(
                "Nenhuma imagem processada está disponível para esta observação."
            )
        return entry

    def _cached_frame(self, entry: ObservationEntry, cache_key: str) -> FrameImage | None:
        """Load the common-frame arrays of an observation from the disk cache."""
        payload = self._cache.get_bytes(NAMESPACE_IMAGES, f"{cache_key}.frame", allow_stale=True)
        if payload is None:
            return None
        with np.load(io.BytesIO(payload)) as arrays:
            data = arrays["data"].astype(float)
            outside = arrays["outside"].astype(bool)
            scale = float(arrays["scale"])
            extras = {}
            if "flags" in arrays.files:
                extras["flags"] = arrays["flags"].astype(np.int64)
            if "variance" in arrays.files:
                extras["variance"] = arrays["variance"].astype(float)
            center_xy = (
                tuple(float(v) for v in arrays["center_source_xy"])
                if "center_source_xy" in arrays.files else None
            )
        wcs = frame_wcs(entry.ra_deg, entry.dec_deg, data.shape[0], scale)
        return FrameImage(
            data=data, outside=outside, wcs=wcs, pixel_scale_arcsec=scale,
            extras=extras, center_source_xy=center_xy,
        )

    def _cached_headers(self, cache_key: str) -> tuple[Any, Any]:
        """IMAGE and FLAGS headers of the source cutout (``None`` if unknown)."""
        from astropy.io import fits

        stored = self._cache.get_json(NAMESPACE_IMAGES, f"{cache_key}.headers", allow_stale=True)
        if not stored:
            return None, None
        image = fits.Header.fromstring(stored["image"]) if stored.get("image") else None
        flags = fits.Header.fromstring(stored["flags"]) if stored.get("flags") else None
        return image, flags

    def _image_lock(self, cache_key: str) -> threading.Lock:
        """Return the lock that serialises the generation of one image."""
        with self._image_locks_guard:
            return self._image_locks.setdefault(cache_key, threading.Lock())

    def _cached_image(self, observation_id: str, cache_key: str) -> ImageResult | None:
        """Return the image from the disk cache, when present."""
        content = self._cache.get_bytes(NAMESPACE_IMAGES, cache_key, allow_stale=True)
        if content is None:
            return None
        metadata = self._cache.get_json(NAMESPACE_OBSERVATIONS, f"{observation_id}.meta", allow_stale=True)
        return ImageResult(
            content=content,
            metadata=dict(metadata or {}),
            headers=self._image_headers(dict(metadata or {})),
        )

    def _build_image(
        self, observation_id: str, cache_key: str, entry: ObservationEntry
    ) -> ImageResult:
        """Retrieve, cut, resample onto the common frame, render and cache."""
        request = self._build_cutout_request(entry)
        result = self._cutout_service.build_cutout(request)
        metadata = dict(result.metadata)
        metadata.setdefault("visual_normalization", VISUAL_NORMALIZATION_DESCRIPTION)
        metadata.setdefault("cutout_strategy", result.strategy.value)

        wcs = result.source_wcs
        if result.source_data is not None and wcs is not None and wcs.has_celestial:
            frame = project_to_frame(
                result.source_data,
                wcs,
                entry.ra_deg,
                entry.dec_deg,
                entry.fov_arcmin,
                scale_arcsec=fits_processor.pixel_scale_arcsec(wcs) or SPHEREX_PIXEL_SCALE_ARCSEC,
                max_pixels=self._settings.max_cutout_pixels,
                extras={
                    name: plane for name, plane in (
                        ("flags", result.source_flags), ("variance", result.source_variance),
                    ) if plane is not None
                },
            )
            content = fits_processor.render_frame_png(frame.data, frame.outside)
            arrays: dict[str, Any] = {
                "data": frame.data.astype(np.float32),
                "outside": frame.outside,
                "scale": np.float64(frame.pixel_scale_arcsec),
            }
            if "flags" in frame.extras:
                arrays["flags"] = frame.extras["flags"].astype(np.int32)
            if "variance" in frame.extras:
                arrays["variance"] = frame.extras["variance"].astype(np.float32)
            if frame.center_source_xy is not None:
                arrays["center_source_xy"] = np.array(frame.center_source_xy)
            buffer = io.BytesIO()
            np.savez_compressed(buffer, **arrays)
            self._cache.set_bytes(NAMESPACE_IMAGES, f"{cache_key}.frame", buffer.getvalue())
            self._cache.set_json(NAMESPACE_IMAGES, f"{cache_key}.headers", {
                "image": result.source_header.tostring() if result.source_header is not None else None,
                "flags": result.flags_header.tostring() if result.flags_header is not None else None,
            })
            metadata.update(
                frame=FRAME_COMMON,
                frame_side_pixels=int(frame.data.shape[0]),
                frame_pixel_scale_arcsec=round(frame.pixel_scale_arcsec, 4),
                frame_coverage_fraction=round(frame.coverage_fraction, 4),
            )
        else:
            # No celestial WCS (synthetic products only): legacy rendering.
            content = fits_processor.render_png(result.data)
            metadata["frame"] = "native"

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
        self, ra_deg: float, dec_deg: float, fov_arcmin: float, margin_deg: float = 0.0
    ) -> tuple[list[dict[str, Any]], DataSource]:
        """Return the records of the archive and where they came from.

        Order: fresh cache -> archive -> expired cache (only when the archive
        is unavailable, so a demonstration survives an IRSA outage; the
        response says the data is stale and since when).
        """
        cache_key = self._query_cache_key(ra_deg, dec_deg, fov_arcmin, margin_deg)
        entry = self._cache.get_json_entry(NAMESPACE_QUERIES, cache_key)
        if entry is not None and not entry[2]:
            logger.info("Query cache hit for %s", cache_key)
            return [dict(item) for item in entry[0]], DataSource("cache", entry[1])

        try:
            records = self._client.query_by_position(
                ra_deg,
                dec_deg,
                radius_from_fov(fov_arcmin) + margin_deg,
                fov_arcmin=fov_arcmin,
            )
        except SourceUnavailableError:
            if entry is None:
                raise
            logger.warning("IRSA unavailable: serving the expired cache of %s", cache_key)
            return [dict(item) for item in entry[0]], DataSource("stale_cache", entry[1])
        self._cache.set_json(NAMESPACE_QUERIES, cache_key, records)
        return records, DataSource("live", None)

    @staticmethod
    def _query_signature(
        ra_deg: float, dec_deg: float, fov_arcmin: float, motion: ProperMotion | None
    ) -> str:
        """Identify the query, so that ids of different queries never collide."""
        text = f"{ra_deg:.6f}|{dec_deg:.6f}|{fov_arcmin:.6f}"
        if motion is not None:
            text += (
                f"|{motion.pm_ra_cosdec_masyr:.3f}|{motion.pm_dec_masyr:.3f}"
                f"|{motion.ref_epoch_jyear:.4f}"
            )
        return text

    @staticmethod
    def _filter_by_footprint(
        records: list[dict[str, Any]],
        ra_deg: float,
        dec_deg: float,
        center_of: Callable[[Mapping[str, Any]], tuple[float, float, str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Drop the products whose footprint does not contain the position.

        The SIA service returns every image that *intersects* the search cone,
        including detectors that only touch its edge; their cutout fails later
        with ``422 Arrays do not overlap`` (DECISÃO 007, item 6). The footprint
        is the ``s_region`` polygon published by the archive. A record without
        a readable polygon is kept: nothing is discarded without evidence.
        """
        kept: list[dict[str, Any]] = []
        for record in records:
            ra, dec = (ra_deg, dec_deg) if center_of is None else center_of(record)[:2]
            polygon = parse_s_region(record.get("s_region"))
            if polygon is None or polygon_contains_position(polygon, ra, dec):
                kept.append(record)
        dropped = len(records) - len(kept)
        if dropped:
            logger.info(
                "Footprint pre-filter dropped %d of %d products", dropped, len(records)
            )
        return kept

    def _query_cache_key(
        self, ra_deg: float, dec_deg: float, fov_arcmin: float, margin_deg: float = 0.0
    ) -> str:
        """Stable key of a query (disk cache)."""
        parts = [
            "query",
            f"{ra_deg:.6f}",
            f"{dec_deg:.6f}",
            f"{fov_arcmin:.6f}",
            # SIA address + collections: a new data release never reuses old results.
            self._client.query_signature,
        ]
        if margin_deg:
            parts.append(f"{margin_deg:.6f}")
        return DiskCache.make_key(*parts)

    def _image_cache_key(self, entry: ObservationEntry) -> str:
        """Stable key of a generated image (disk cache)."""
        record = entry.record
        return DiskCache.make_key(
            "image",
            str(pick(record, "product_id") or ""),
            str(pick(record, "band") or ""),
            str(extract_detector(record) or ""),
            f"{entry.ra_deg:.6f}",
            f"{entry.dec_deg:.6f}",
            f"{entry.fov_arcmin:.6f}",
            self._settings.cutout_mode,
            _IMAGE_CACHE_VERSION,
        )

    def _build_observations(
        self,
        records: list[dict[str, Any]],
        ra_deg: float,
        dec_deg: float,
        fov_arcmin: float,
        *,
        center_of: Callable[[Mapping[str, Any]], tuple[float, float, str]] | None = None,
        query_signature: str = "",
    ) -> list[_BuiltObservation]:
        """Translate the archive records into the schemas of the contract."""
        built: list[_BuiltObservation] = []
        for record in records:
            center_ra, center_dec, position_source = (
                center_of(record) if center_of is not None
                else (ra_deg, dec_deg, POSITION_REQUESTED)
            )
            product_id = _to_str(pick(record, "product_id"))
            band = _to_str(pick(record, "band"))
            detector = extract_detector(record)
            observed_at, timing_status, observed_at_source = self._extract_observed_at(record)

            metadata = ObservationMetadata(
                product_id=product_id,
                quality=_to_float(pick(record, "quality")),
                observed_at_source=observed_at_source,
                timing_status=timing_status,
                instrument=_to_str(pick(record, "instrument")),
                exposure_time_s=_to_float(pick(record, "exposure")),
                wavelength_min_nm=wavelength_to_nm(record, "em_min"),
                wavelength_max_nm=wavelength_to_nm(record, "em_max"),
                wcs=self._extract_wcs(record),
                contamination_flags=self._extract_flags(record),
                source=_to_str(pick(record, "provenance")),
                original_file_url=_to_str(pick(record, "access_url")),
                data_release=_to_str(pick(record, "data_release")),
                cutout_strategy=self._strategy_value(record),
                cutout_size_pixels=None,
                visual_normalization=VISUAL_NORMALIZATION_DESCRIPTION,
                duplicate_count=0,
                cutout_center_ra_deg=round(center_ra, 7),
                cutout_center_dec_deg=round(center_dec, 7),
                position_source=position_source,
                coverage_fraction=self._predicted_coverage(
                    record, center_ra, center_dec, fov_arcmin
                ),
                frame=FRAME_COMMON,
            )

            observation_id = self._build_observation_id(
                product_id, band, detector, query_signature
            )
            observation = Observation(
                id=observation_id,
                observed_at=observed_at,
                band=band,
                detector=detector,
                image_url=f"/api/images/{observation_id}",
                metadata=metadata,
            )
            built.append(
                _BuiltObservation(
                    observation=observation,
                    record=record,
                    center=(center_ra, center_dec),
                )
            )
        return built

    @staticmethod
    def _predicted_coverage(
        record: Mapping[str, Any], ra_deg: float, dec_deg: float, fov_arcmin: float
    ) -> float | None:
        """Fraction of the frame inside the detector footprint (``s_region``).

        ``None`` when the archive publishes no readable polygon.
        """
        polygon = parse_s_region(record.get("s_region"))
        if polygon is None:
            return None
        return round(footprint_coverage(polygon, ra_deg, dec_deg, fov_arcmin), 4)

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
        product_id: str | None,
        band: str | None,
        detector: str | None,
        query_signature: str = "",
    ) -> str:
        """Return the deterministic internal identifier of an observation.

        The query signature (centre, field of view, proper motion) is part of
        the identifier: the same product cut for two different queries is two
        different images and must not share an id.
        """
        canonical = f"{product_id or ''}|{band or ''}|{detector or ''}|{query_signature}"
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
            return _mjd_to_datetime(mjd), "mjd_observation_date", str(raw_mjd)

        # ObsCore / SIA v2 publishes ``t_min`` and ``t_max`` as MJD (unit "d").
        # The IRSA SPHEREx answer follows it (``t_min = 60800.700028``, verified
        # on 2026-11-14). An ISO string is still accepted for other sources.
        for alias, criterion in (("t_min", "observation_date"), ("t_max", "interval_start")):
            raw = pick(record, alias)
            if raw in (None, ""):
                continue
            mjd = _to_float(raw)
            if mjd is not None:
                return _mjd_to_datetime(mjd), "mjd_observation_date", str(raw)
            parsed = _parse_datetime(str(raw))
            if parsed is not None:
                return parsed, criterion, str(raw)

        # ``obs_release_date`` is the publication date of the product, NOT the
        # observation instant (DECISÃO 007, item 4). It is never used as epoch.
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
            # The cutout is centred where the target is at this exposure.
            center_ra, center_dec = item.center or (ra_deg, dec_deg)
            entry = ObservationEntry(
                observation_id=item.observation.id,
                record=dict(item.record),
                ra_deg=center_ra,
                dec_deg=center_dec,
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
        frame = metadata.get("frame")
        if frame:
            headers["X-SpherEx-Frame"] = str(frame).replace("_", "-")
        return headers


#: MJD of the Unix epoch (1970-01-01T00:00:00).
_MJD_UNIX_EPOCH = 40587.0


def _mjd_to_datetime(mjd: float) -> datetime:
    """Convert a Modified Julian Date into a UTC ``datetime``.

    The time scale of the source is not converted (UTC vs TT differ by ~69 s),
    which is negligible for ordering exposures separated by minutes or days.
    """
    return _EPOCH + timedelta(days=mjd - _MJD_UNIX_EPOCH)


#: Factor that converts one unit of the record into nanometres.
_WAVELENGTH_UNIT_TO_NM: dict[str, float] = {
    "m": 1e9,
    "um": 1e3,
    "µm": 1e3,  # micro sign U+00B5
    "μm": 1e3,  # greek mu U+03BC
    "micron": 1e3,
    "microns": 1e3,
    "nm": 1.0,
    "angstrom": 0.1,
    "angstroms": 0.1,
    "å": 0.1,
}

#: Aliases of ``em_min``/``em_max`` whose name already states nanometres.
_NM_ALIASES = frozenset({"em_min_nm", "em_max_nm", "wavelength_min_nm", "wavelength_max_nm"})


def wavelength_to_nm(record: Mapping[str, Any], key: str) -> float | None:
    """Return the wavelength bound ``key`` (``em_min``/``em_max``) in nanometres.

    Rule (``docs/decisions.md``):

    1. If the record publishes ``band_units`` (any alias), convert from that
       unit (m, um/µm/micron, nm, angstrom). An unknown unit gives ``None``:
       the value is not guessed.
    2. Without a unit, a value read from an alias whose name ends in ``_nm``
       is already in nanometres.
    3. Otherwise assume metres, the unit of ``em_min``/``em_max`` in the IVOA
       ObsCore standard (verified on the real IRSA SIA v2 answer:
       ``FIELD name="em_min" unit="m"``).
    """
    value = _to_float(pick(record, key))
    if value is None:
        return None

    unit = _to_str(pick(record, "band_units"))
    if unit is not None:
        factor = _WAVELENGTH_UNIT_TO_NM.get(unit.lower())
        if factor is None:
            logger.warning("Unknown wavelength unit %r; %s left empty", unit, key)
            return None
        return value * factor

    source_alias = next(
        (
            alias
            for alias in FIELD_ALIASES.get(key, (key,))
            if alias in record and record[alias] not in (None, "")
        ),
        None,
    )
    if source_alias in _NM_ALIASES:
        return value
    return value * _WAVELENGTH_UNIT_TO_NM["m"]


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
