"""Common frame, predicted coverage and composites (SYNTHETIC images).

The synthetic FITS images are written here: a rotated TAN detector with one
Gaussian "star" at a known sky position. Nothing here is SPHEREx data.
"""

from __future__ import annotations

import io
import math

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from app.api.errors import InvalidParametersError
from app.services import fits_processor
from app.services.common_frame import frame_side_pixels, project_to_frame
from app.services.observation_service import ObservationEntry
from app.services.sky_coverage import footprint_coverage

RA0, DEC0 = 150.0, 20.0
SCALE = 6.15  # arcsec/pixel


def rotated_wcs(angle_deg: float, size: int, ra=RA0, dec=DEC0) -> WCS:
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [ra, dec]
    wcs.wcs.crpix = [(size + 1) / 2, (size + 1) / 2]
    s = SCALE / 3600.0
    c, k = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    wcs.wcs.cd = [[-s * c, s * k], [s * k, s * c]]
    return wcs


def image_with_star(wcs: WCS, size: int, star_ra: float, star_dec: float, flux=1000.0) -> np.ndarray:
    x, y = wcs.all_world2pix(star_ra, star_dec, 0)
    yy, xx = np.mgrid[0:size, 0:size]
    return 10.0 + flux * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.0 ** 2))


def peak_offset_px(frame) -> float:
    data = np.where(frame.outside, -np.inf, np.nan_to_num(frame.data, nan=-np.inf))
    y, x = np.unravel_index(np.argmax(data), data.shape)
    c = (data.shape[0] - 1) / 2
    return math.hypot(x - c, y - c)


@pytest.mark.parametrize("angle", [0.0, 33.0, 90.0, 147.0])
def test_star_lands_at_the_centre_whatever_the_detector_angle(angle) -> None:
    size = 61
    wcs = rotated_wcs(angle, size)
    star = (RA0 + 20 / 3600 / math.cos(math.radians(DEC0)), DEC0 - 15 / 3600)
    data = image_with_star(wcs, size, *star)

    frame = project_to_frame(data, wcs, star[0], star[1], 3.0)

    assert frame.data.shape == (frame_side_pixels(3.0, SCALE),) * 2
    assert peak_offset_px(frame) <= 0.5
    assert frame.coverage_fraction == 1.0


def test_frame_is_north_up_east_left() -> None:
    size = 61
    wcs = rotated_wcs(57.0, size)
    north = (RA0, DEC0 + 60 / 3600)  # 1' north of the centre
    east = (RA0 + 60 / 3600 / math.cos(math.radians(DEC0)), DEC0)  # 1' east
    frame_n = project_to_frame(image_with_star(wcs, size, *north), wcs, RA0, DEC0, 4.0)
    frame_e = project_to_frame(image_with_star(wcs, size, *east), wcs, RA0, DEC0, 4.0)
    c = (frame_n.data.shape[0] - 1) / 2

    yn, xn = np.unravel_index(np.nanargmax(frame_n.data), frame_n.data.shape)
    ye, xe = np.unravel_index(np.nanargmax(frame_e.data), frame_e.data.shape)
    assert yn > c and abs(xn - c) <= 1  # north = larger row (FITS convention, row 0 south)
    assert xe < c and abs(ye - c) <= 1  # east = smaller column (east left)


def test_pixels_outside_the_source_are_flagged() -> None:
    size = 31
    wcs = rotated_wcs(0.0, size)
    data = np.ones((size, size))
    # Frame centred on the right edge of the source: the east half has data.
    edge_ra = RA0 - (size / 2) * SCALE / 3600 / math.cos(math.radians(DEC0))
    frame = project_to_frame(data, wcs, edge_ra, DEC0, 3.0)

    assert 0.4 < frame.coverage_fraction < 0.6
    assert np.isnan(frame.data[frame.outside]).all()
    assert np.isfinite(frame.data[~frame.outside]).all()


def test_predicted_coverage_from_the_footprint() -> None:
    d = 1.0  # square footprint of 2x2 degrees around (RA0, DEC0), in the tangent plane
    cosd = math.cos(math.radians(DEC0))
    square = [(RA0 - d / cosd, DEC0 - d), (RA0 + d / cosd, DEC0 - d),
              (RA0 + d / cosd, DEC0 + d), (RA0 - d / cosd, DEC0 + d)]
    assert footprint_coverage(square, RA0, DEC0, 30.0) == 1.0
    # Centre exactly on the east edge: half of the field is outside.
    on_edge = (RA0 + d / cosd, DEC0)
    assert footprint_coverage(square, *on_edge, 30.0) == pytest.approx(0.5, abs=0.06)


def test_rgba_png_is_transparent_outside_and_marks_invalid_pixels() -> None:
    data = np.arange(25, dtype=float).reshape(5, 5)
    outside = np.zeros((5, 5), bool)
    outside[:, 0] = True  # west column without data... (column 0 = east side? no: just a mask)
    data[2, 2] = np.nan  # invalid pixel inside the detector

    png = fits_processor.render_frame_png(data, outside, side=5)
    rgba = np.array(Image.open(io.BytesIO(png)))
    flipped = np.flipud(rgba)  # back to FITS row order

    assert (flipped[:, 0, 3] == 0).all()
    assert tuple(flipped[2, 2, :3]) == fits_processor.INVALID_PIXEL_RGB
    assert (flipped[:, 1:, 3][np.isfinite(data[:, 1:])] == 255).all()


# --- composites -----------------------------------------------------------------
class FrameService:
    """Minimal stand-in exposing what ObservationService.composite needs."""


def make_entry(observation_id: str, detector: str = "D3", t_min: float = 60800.0):
    return ObservationEntry(
        observation_id=observation_id,
        record={"obs_publisher_did": f"ivo://x?{observation_id}/{detector}", "t_min": t_min},
        ra_deg=RA0, dec_deg=DEC0, fov_arcmin=3.0,
    )


@pytest.fixture
def composite_service(service_factory, monkeypatch):
    from conftest import FakeTransport

    service = service_factory(FakeTransport())
    frames: dict[str, tuple] = {}
    size = 61
    wcs = rotated_wcs(20.0, size)

    def add(observation_id, star_offset_arcsec, detector="D3", t_min=60800.0, noise_seed=0):
        star = (RA0 + star_offset_arcsec / 3600 / math.cos(math.radians(DEC0)), DEC0)
        rng = np.random.default_rng(noise_seed)
        data = image_with_star(wcs, size, *star, flux=50.0) + rng.normal(0, 5.0, (size, size))
        frame = project_to_frame(data, wcs, RA0, DEC0, 3.0)
        frames[observation_id] = (frame, make_entry(observation_id, detector, t_min))

    monkeypatch.setattr(service, "get_frame", lambda i: frames[i])
    service._test_add = add
    return service


def read_png(content: bytes) -> np.ndarray:
    return np.flipud(np.array(Image.open(io.BytesIO(content)).convert("RGBA")))


def test_mean_of_epochs_raises_signal_to_noise(composite_service) -> None:
    for i in range(16):
        composite_service._test_add(f"o{i}", 0.0, noise_seed=i)
    single = composite_service.composite("mean", ["o0"])
    stacked = composite_service.composite("mean", [f"o{i}" for i in range(16)])

    assert stacked.metadata["frames_a"] == 16
    assert stacked.metadata["max_frames_per_pixel"] == 16
    assert stacked.headers["X-SpherEx-Composite-Op"] == "mean"
    # Visual check of the stretch: the background of the stack is smoother.
    bg_single = read_png(single.content)[..., 0][:100, :100].std()
    bg_stack = read_png(stacked.content)[..., 0][:100, :100].std()
    assert bg_stack < bg_single


def test_difference_reveals_a_source_that_moved(composite_service) -> None:
    composite_service._test_add("early", -30.0, t_min=60800.0, noise_seed=1)
    composite_service._test_add("late", +30.0, t_min=61100.0, noise_seed=2)

    diff = composite_service.composite("diff", ["late"], ["early"])
    image = read_png(diff.content)[..., 0].astype(float)

    # East (left, smaller columns) = "late" star -> bright; west = "early" -> dark.
    side = image.shape[1]
    row = image[image.shape[0] // 2]
    assert row[: side // 2].max() > 200
    assert row[side // 2:].min() < 55
    assert diff.metadata["composite_op"] == "diff"
    assert diff.metadata["epoch_span_jyear"][1] > diff.metadata["epoch_span_jyear"][0]


def test_mixing_detectors_is_refused(composite_service) -> None:
    composite_service._test_add("d3", 0.0, detector="D3")
    composite_service._test_add("d6", 0.0, detector="D6")
    with pytest.raises(InvalidParametersError):
        composite_service.composite("mean", ["d3", "d6"])


def test_invalid_operations_are_refused(composite_service) -> None:
    composite_service._test_add("x", 0.0)
    with pytest.raises(InvalidParametersError):
        composite_service.composite("sum", ["x"])
    with pytest.raises(InvalidParametersError):
        composite_service.composite("diff", ["x"])
