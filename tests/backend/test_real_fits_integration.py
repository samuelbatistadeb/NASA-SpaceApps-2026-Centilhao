
"""Optional integration test using a real SPHEREx DR1 FITS file.

The discovery record is synthetic. The FITS pixels are real.
No network requests are performed.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.observations import get_observation_service
from app.main import app

from conftest import (
    FakeTransport,
    fits_response,
    votable_response,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REAL_FITS = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "spherex"
    / "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
)


@pytest.mark.skipif(
    not REAL_FITS.is_file(),
    reason="Real SPHEREx FITS file is not available locally.",
)
def test_api_processes_real_spherex_fits(
    service_factory,
    tmp_path,
) -> None:
    """The existing API must render genuine SPHEREx pixels."""

    fits_bytes = REAL_FITS.read_bytes()

    transport = FakeTransport([
        votable_response(),
        fits_response(fits_bytes),
    ])

    service = service_factory(transport)

    app.dependency_overrides[get_observation_service] = (
        lambda: service
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/observations",
                params={
                    "ra_deg": 133.795129,
                    "dec_deg": -7.245147,
                    "fov_arcmin": 4.24264,
                },
            )

            assert response.status_code == 200, response.text

            observations = response.json()["observations"]

            assert len(observations) > 0

            observation_id = observations[0]["id"]

            image = client.get(
                f"/api/images/{observation_id}"
            )

            assert image.status_code == 200, image.text
            assert image.headers["content-type"] == "image/png"

            assert image.content.startswith(
                b"\x89PNG\r\n\x1a\n"
            )

            output = tmp_path / "real_spherex_api.png"
            output.write_bytes(image.content)

            print()
            print("=== INTEGRACAO FITS REAL ===")
            print(f"Observacao de teste: {observation_id}")
            print(f"PNG gerado: {output}")
            print(f"Tamanho: {len(image.content)} bytes")
            print("Resultado: OK")

    finally:
        app.dependency_overrides.clear()
