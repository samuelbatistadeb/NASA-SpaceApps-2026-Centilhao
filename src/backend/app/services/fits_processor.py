"""Processing of the scientific FITS files: metadata, cutout and PNG preview.

The module uses Astropy to open the files and ``astropy.nddata.Cutout2D`` to
produce the spatial cutout, and Matplotlib (Agg backend) to render a PNG that
can be shown in a browser.

.. warning::

   The real structure of the SPHEREx products is still **pending verification**
   (``docs/science/data-sources.md``). The code below therefore works with the
   structure that is described by the FITS standard and handles the usual
   variations (science extension, spectral cube, WCS present or absent). Every
   assumption is reported in the returned metadata so that nothing is silently
   invented.

The visual normalisation applied to the PNG is a **display aid only**. It is
never a photometric measurement (``docs/science/validation.md`` section 8).
"""

from __future__ import annotations

import io
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS

from app.api.errors import ProcessingError

logger = logging.getLogger(__name__)

#: Description of the display normalisation used for the PNG previews.
VISUAL_NORMALIZATION_DESCRIPTION = (
    "percentile stretch (1-99) applied to the finite pixels for display only; "
    "this is NOT a photometric measurement"
)

#: Header keywords that are extracted when present.
INTERESTING_KEYWORDS = (
    "DATE-OBS",
    "DATE",
    "MJD-OBS",
    "EXPTIME",
    "EXPOSURE",
    "INSTRUME",
    "DETECTOR",
    "BAND",
    "WAVELEN",
    "WAVECAL",
    "TELESCOP",
    "OBSERVER",
    "OBJECT",
    "FILTER",
    "FILENAME",
    "PRODID",
    "OBSID",
    "DATASET",
    "LEVEL",
    "RADIUS",
    "RA",
    "DEC",
    "RADESYS",
    "EQUINOX",
    "BUNIT",
    "CTYPE1",
    "CTYPE2",
    "CTYPE3",
    "CRVAL1",
    "CRVAL2",
    "CRVAL3",
    "CRPIX1",
    "CRPIX2",
    "CRPIX3",
    "CDELT1",
    "CDELT2",
    "CDELT3",
    "CUNIT1",
    "CUNIT2",
    "CUNIT3",
    "NAXIS1",
    "NAXIS2",
    "NAXIS3",
)


@dataclass
class FitsImage:
    """A 2D plane extracted from a FITS file."""

    data: np.ndarray
    header: fits.Header
    hdu_index: int
    hdu_name: str
    spectral_plane_index: int | None = None
    spectral_plane_selection: str | None = None
    n_spectral_planes: int | None = None


@dataclass
class CutoutResult:
    """Result of a spatial cutout."""

    data: np.ndarray
    header: fits.Header
    metadata: dict[str, Any] = field(default_factory=dict)



def _select_data_hdu(
    hdulist: fits.HDUList,
) -> tuple[int, fits.ImageHDU]:
    """Prefer the SPHEREx IMAGE extension when available."""

    if "IMAGE" in hdulist:
        index = hdulist.index_of("IMAGE")
        hdu = hdulist[index]

        data = getattr(hdu, "data", None)

        if data is not None and getattr(data, "ndim", 0) in (2, 3):
            return index, hdu

    for index, hdu in enumerate(hdulist):
        data = getattr(hdu, "data", None)

        if data is None:
            continue

        if getattr(data, "ndim", 0) in (2, 3):
            return index, hdu

    raise ProcessingError(
        "O arquivo FITS não contém uma extensão de imagem utilizável.",
        detail="no HDU with 2D or 3D image data",
    )



def load_image(content: bytes) -> FitsImage:
    """Open a FITS file and extract the plane used for the visualisation.

    Args:
        content: Raw bytes of the FITS file.

    Returns:
        The extracted image plane together with its header.

    Raises:
        ProcessingError: The file cannot be opened or has no usable image.
    """
    try:
        with fits.open(io.BytesIO(content), memmap=False) as hdulist:
            index, hdu = _select_data_hdu(hdulist)
            header = hdu.header.copy()
            name = hdu.name or f"HDU{index}"
            data = np.array(hdu.data, dtype=float)
    except ProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001 - any astropy failure is the same
        raise ProcessingError(
            "Não foi possível abrir o arquivo FITS do produto.",
            detail=f"astropy error: {exc}",
        ) from exc

    spectral_index: int | None = None
    spectral_selection: str | None = None
    n_planes: int | None = None

    if data.ndim == 3:
        n_planes = int(data.shape[0])
        spectral_index = n_planes // 2
        spectral_selection = "middle_plane"
        data = data[spectral_index, :, :]
    elif data.ndim > 3:
        raise ProcessingError(
            "O arquivo FITS contém um número de dimensões não suportado.",
            detail=f"ndim={data.ndim}",
        )

    if data.ndim != 2:
        raise ProcessingError(
            "A extensão de imagem do FITS não é bidimensional.",
            detail=f"ndim={data.ndim}",
        )

    return FitsImage(
        data=data,
        header=header,
        hdu_index=index,
        hdu_name=name,
        spectral_plane_index=spectral_index,
        spectral_plane_selection=spectral_selection,
        n_spectral_planes=n_planes,
    )


def extract_header_metadata(header: fits.Header) -> dict[str, Any]:
    """Extract the relevant keywords of a FITS header.

    Only keywords that are really present are returned; missing ones are not
    reported with an invented value.
    """
    metadata: dict[str, Any] = {}
    for keyword in INTERESTING_KEYWORDS:
        if keyword not in header:
            continue
        value = header[keyword]
        if value is None:
            continue
        if isinstance(value, (bool, int, float, str)):
            metadata[keyword] = value
        else:
            metadata[keyword] = str(value)
    return metadata


def extract_observation_datetime(header: fits.Header) -> datetime | None:
    """Return the observation instant stored in a FITS header.

    ``DATE-OBS`` is preferred; ``MJD-OBS`` is used as a fallback. The returned
    datetime is timezone aware and expressed in UTC.
    """
    date_obs = header.get("DATE-OBS")
    if isinstance(date_obs, str) and date_obs.strip():
        parsed = _parse_iso_datetime(date_obs.strip())
        if parsed is not None:
            return parsed

    mjd = header.get("MJD-OBS")
    if mjd is not None:
        try:
            value = float(mjd)
        except (TypeError, ValueError):
            value = None
        if value is not None:
            return datetime.fromtimestamp(0, tz=timezone.utc) + _timedelta_from_mjd(value)

    return None


def _timedelta_from_mjd(mjd: float):
    """Return the timedelta between the MJD epoch and the given MJD."""
    from datetime import timedelta

    return timedelta(days=mjd - 40587.0)


def _parse_iso_datetime(text: str) -> datetime | None:
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



def extract_wcs(header: fits.Header) -> WCS | None:
    """Build the celestial WCS, preserving distortion information."""

    try:
        wcs = WCS(header)

        if not wcs.has_celestial:
            return None

        return wcs.celestial

    except Exception:
        logger.warning(
            "The FITS header does not provide a usable WCS.",
            exc_info=True,
        )
        return None


def pixel_scale_arcsec(wcs: WCS | None) -> float | None:
    """Estimate the mean projected pixel scale in arcsec/pixel."""

    if wcs is None:
        return None

    try:
        from astropy.wcs.utils import proj_plane_pixel_scales

        scales = np.asarray(
            proj_plane_pixel_scales(wcs.celestial),
            dtype=float,
        )

        if (
            scales.size != 2
            or not np.all(np.isfinite(scales))
            or np.any(scales <= 0)
        ):
            return None

        return float(np.mean(scales) * 3600.0)

    except Exception:
        logger.warning(
            "Could not determine WCS pixel scale.",
            exc_info=True,
        )
        return None




def cutout_image(
    image: FitsImage,
    ra_deg: float,
    dec_deg: float,
    size_pixels: int,
    *,
    allow_center_fallback: bool = False,
) -> CutoutResult:
    """Generate a spatial cutout using celestial WCS."""

    if size_pixels <= 0:
        raise ProcessingError(
            "O tamanho do recorte deve ser positivo.",
            detail=f"size={size_pixels}",
        )

    wcs = extract_wcs(image.header)

    # 1. Determinar o centro do recorte.
    if wcs is None:
        if not allow_center_fallback:
            raise ProcessingError(
                "O produto FITS não possui WCS celestial utilizável.",
                detail="celestial WCS unavailable",
            )

        height, width = image.data.shape

        x = (width - 1) / 2.0
        y = (height - 1) / 2.0

        center_source = "image_center_no_wcs"

    else:
        try:
            x, y = wcs.all_world2pix(
                ra_deg,
                dec_deg,
                0,
            )
        except Exception as exc:
            raise ProcessingError(
                "Não foi possível converter as coordenadas em pixels.",
                detail=f"WCS error: {exc}",
            ) from exc

        center_source = "wcs"

    # 2. Validar as coordenadas em pixels.
    height, width = image.data.shape

    if not (
        math.isfinite(x)
        and math.isfinite(y)
        and 0 <= x < width
        and 0 <= y < height
    ):
        raise ProcessingError(
            "A posição solicitada está fora da imagem FITS.",
            detail=f"x={x}, y={y}, shape={image.data.shape}",
        )

    # 3. Gerar o recorte.
    try:
        cutout = Cutout2D(
            image.data,
            position=(x, y),
            size=size_pixels,
            wcs=wcs,
            mode="partial",
            fill_value=np.nan,
            copy=True,
        )
    except Exception as exc:
        raise ProcessingError(
            "Não foi possível gerar o recorte da imagem.",
            detail=f"Cutout2D error: {exc}",
        ) from exc

    # 4. Validar os dados científicos.
    data = np.asarray(
        cutout.data,
        dtype=float,
    )

    if not np.isfinite(data).any():
        raise ProcessingError(
            "O recorte não contém pixels válidos.",
            detail="all cutout pixels are non-finite",
        )

    # 5. Registrar a origem do recorte.
    metadata = {
        "cutout_size_pixels": int(size_pixels),
        "cutout_shape": [
            int(data.shape[0]),
            int(data.shape[1]),
        ],
        "wcs_available": wcs is not None,
        "cutout_center_px": [
            float(x),
            float(y),
        ],
        "cutout_center_source": center_source,
        "pixel_scale_arcsec": pixel_scale_arcsec(wcs),
    }

    # 6. Retornar dados e metadados.
    return CutoutResult(
        data=data,
        header=(
            cutout.wcs.to_header(relax=True)
            if cutout.wcs is not None
            else image.header
        ),
        metadata=metadata,
    )


def size_pixels_for_fov(
    fov_arcmin: float,
    *,
    arcsec_per_pixel: float | None,
    default_pixels: int,
    max_pixels: int,
) -> tuple[int, str]:
    """Return the cutout side in pixels and the criterion that produced it."""
    if arcsec_per_pixel and arcsec_per_pixel > 0:
        size_arcsec = fov_arcmin * 60.0
        pixels = int(math.ceil(size_arcsec / arcsec_per_pixel))
        pixels = max(1, min(pixels, max_pixels))
        return pixels, "fov_and_pixel_scale"
    return max(1, min(default_pixels, max_pixels)), "application_default_no_pixel_scale"


def normalize_for_display(data: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Apply a **visual** normalisation to the image data.

    A percentile stretch (1% to 99%) of the finite values is used. This is a
    display aid and must not be interpreted as a photometric measurement.

    Returns:
        The normalised array, the lower and the upper limit used.
    """
    array = np.asarray(data, dtype=float)
    finite = np.isfinite(array)
    if not finite.any():
        raise ProcessingError(
            "A imagem não contém valores válidos para visualização.",
            detail="all pixels are NaN or infinite",
        )

    values = array[finite]
    vmin, vmax = np.percentile(values, [1.0, 99.0])
    vmin, vmax = float(vmin), float(vmax)
    if not math.isfinite(vmin) or not math.isfinite(vmax):
        raise ProcessingError(
            "A imagem não contém valores válidos para visualização.",
            detail="non finite percentile limits",
        )
    if vmax <= vmin:
        vmin, vmax = float(values.min()), float(values.max())
    if vmax <= vmin:
        vmax = vmin + 1.0

    normalised = np.clip(np.nan_to_num(array, nan=vmin, posinf=vmax, neginf=vmin), vmin, vmax)
    return normalised, vmin, vmax


def render_png(data: np.ndarray) -> bytes:
    """Render an image array as a PNG suitable for a browser.

    The rendering uses a grayscale colormap and the visual normalisation
    described by :func:`normalize_for_display`.
    """
    import matplotlib

    matplotlib.use("Agg", force=False)

    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    normalised, vmin, vmax = normalize_for_display(data)

    figure = Figure(figsize=(6.0, 6.0), dpi=100)
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    axes.imshow(
        normalised,
        cmap="gray",
        origin="lower",
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
    )
    axes.set_axis_off()
    figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

    buffer = io.BytesIO()
    try:
        figure.savefig(buffer, format="png", transparent=False, facecolor="black")
    except Exception as exc:  # noqa: BLE001 - matplotlib raises several types
        raise ProcessingError(
            "Não foi possível gerar a imagem processada.",
            detail=f"matplotlib error: {exc}",
        ) from exc
    finally:
        figure.clear()

    return buffer.getvalue()


#: Colour (RGB) of pixels inside the detector without a valid value
#: (saturated cores, bad pixels). Distinct from "no data" (transparent).
INVALID_PIXEL_RGB = (176, 48, 96)

#: Side (pixels) of the PNG sent to the browser; small frames are enlarged
#: with nearest-neighbour so the SPHEREx pixels stay visible.
FRAME_PNG_SIDE = 600


def render_frame_png(
    data: np.ndarray,
    outside: np.ndarray,
    *,
    limits: tuple[float, float] | None = None,
    side: int = FRAME_PNG_SIDE,
) -> bytes:
    """Render a common-frame image as an RGBA PNG (north up, east left).

    * ``outside`` (no data, outside the detector) -> transparent;
    * NaN inside the detector -> :data:`INVALID_PIXEL_RGB`;
    * finite values -> grayscale with the visual normalisation (1-99%), or
      with ``limits`` when given (e.g. symmetric limits of a difference image).

    Row 0 of ``data`` is the south edge (FITS convention); it is flipped so
    that north is at the top of the PNG.
    """
    from PIL import Image

    array = np.asarray(data, dtype=float)
    valid = np.isfinite(array) & ~outside
    if limits is None:
        if not valid.any():
            raise ProcessingError(
                "A imagem não contém valores válidos para visualização.",
                detail="no finite pixel inside the detector",
            )
        vmin, vmax = (float(v) for v in np.percentile(array[valid], [1.0, 99.0]))
    else:
        vmin, vmax = limits
    if not vmax > vmin:
        vmax = vmin + 1.0

    gray = np.clip((np.nan_to_num(array, nan=vmin) - vmin) / (vmax - vmin), 0.0, 1.0)
    gray = (gray * 255.0 + 0.5).astype(np.uint8)
    rgba = np.zeros(array.shape + (4,), dtype=np.uint8)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = gray
    rgba[..., 3] = 255
    invalid = ~np.isfinite(array) & ~outside
    rgba[invalid, 0], rgba[invalid, 1], rgba[invalid, 2] = INVALID_PIXEL_RGB
    rgba[outside] = 0

    image = Image.fromarray(np.flipud(rgba), mode="RGBA")
    if image.width < side:
        image = image.resize((side, side), Image.NEAREST)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def load_auxiliary_planes(
    content: bytes, names: tuple[str, ...] = ("FLAGS", "VARIANCE")
) -> dict[str, tuple[np.ndarray, fits.Header]]:
    """Return the auxiliary 2D planes present in the FITS (e.g. FLAGS, VARIANCE).

    Missing planes are simply absent from the result (the stream may have
    stopped before them, or the product may not have them). The FLAGS plane of
    a full SPHEREx product is tile-compressed; astropy decompresses it.
    """
    planes: dict[str, tuple[np.ndarray, fits.Header]] = {}
    try:
        with fits.open(io.BytesIO(content), memmap=False) as hdul:
            for name in names:
                if name not in hdul:
                    continue
                hdu = hdul[name]
                data = getattr(hdu, "data", None)
                if data is None or getattr(data, "ndim", 0) != 2:
                    continue
                planes[name] = (np.array(data), hdu.header.copy())
    except Exception:  # noqa: BLE001 - auxiliary planes are optional
        logger.warning("Could not read auxiliary planes %s", names, exc_info=True)
    return planes
