"""Stop reading a FITS stream once the IMAGE extension is complete.

The FITS built here is SYNTHETIC and mimics the HDU order of a SPHEREx Level 2
cutout: PRIMARY, IMAGE, FLAGS, ..., a large EPSF table last.
"""

from __future__ import annotations

import io

import numpy as np
from astropy.io import fits

from app.services import fits_processor
from app.services.irsa_client import fits_bytes_through_extension


def build_spherex_like_fits() -> tuple[bytes, np.ndarray]:
    image = np.arange(29 * 29, dtype=np.float32).reshape(29, 29)
    hdus = fits.HDUList([
        fits.PrimaryHDU(),
        fits.ImageHDU(image, name="IMAGE"),
        fits.ImageHDU(np.zeros((29, 29), dtype=np.int32), name="FLAGS"),
        fits.BinTableHDU.from_columns(
            [fits.Column(name="psf", format="1000E", array=np.zeros((451, 1000), np.float32))],
            name="EPSF",
        ),
    ])
    buffer = io.BytesIO()
    hdus.writeto(buffer)
    return buffer.getvalue(), image


def test_returns_the_end_of_the_image_extension() -> None:
    content, image = build_spherex_like_fits()

    end = fits_bytes_through_extension(content)

    assert end is not None
    assert end % 2880 == 0
    assert end < len(content) / 50  # EPSF (~1.8 MB) is skipped
    with fits.open(io.BytesIO(content[:end])) as hdus:
        assert [h.name for h in hdus] == ["PRIMARY", "IMAGE"]
        np.testing.assert_array_equal(hdus["IMAGE"].data, image)


def test_truncated_product_is_processed_like_the_full_one() -> None:
    content, image = build_spherex_like_fits()
    end = fits_bytes_through_extension(content)

    loaded = fits_processor.load_image(content[:end])

    np.testing.assert_array_equal(loaded.data, image)


def test_incomplete_buffer_asks_to_keep_reading() -> None:
    content, _ = build_spherex_like_fits()
    end = fits_bytes_through_extension(content)

    for size in (0, 100, 2880, end - 1):
        assert fits_bytes_through_extension(content[:size]) is None


def test_missing_extension_asks_to_read_everything() -> None:
    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(np.zeros((4, 4), np.float32))]).writeto(buffer)

    assert fits_bytes_through_extension(buffer.getvalue()) is None


def test_works_on_a_growing_bytearray() -> None:
    content, _ = build_spherex_like_fits()
    body = bytearray()
    result = None
    for start in range(0, len(content), 4096):
        body.extend(content[start:start + 4096])
        result = fits_bytes_through_extension(body)
        if result is not None and len(body) >= result:
            break

    assert result == fits_bytes_through_extension(content)
    assert len(body) < len(content) / 10
