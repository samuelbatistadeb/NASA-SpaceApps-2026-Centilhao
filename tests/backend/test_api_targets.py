"""Tests of ``GET /api/targets``."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_targets_are_listed_in_the_format_used_by_the_frontend() -> None:
    response = TestClient(app).get("/api/targets")

    assert response.status_code == 200
    targets = response.json()["targets"]
    assert [t["name"] for t in targets] == [
        "WISE 0855", "Estrela de Barnard", "ε Indi", "RW Aurigae", "R Draconis",
    ]
    for target in targets:
        assert 0 <= target["ra"] < 360
        assert -90 <= target["dec"] <= 90
        assert target["fov"] > 0
        assert target["source"].startswith("docs/science/target-catalog.md")


def test_wise0855_uses_the_position_propagated_to_spherex() -> None:
    """The challenge coordinate (WISE epoch ~2010) is ~2' away from the object in 2025."""
    targets = TestClient(app).get("/api/targets").json()["targets"]
    wise = next(t for t in targets if t["name"] == "WISE 0855")

    assert wise["position_epoch"] == "2025.35"
    # SIMBAD J2000 (133.81890825, -7.247048), Kirkpatrick et al. 2021, propagated to 2025.35.
    assert (wise["ra"], wise["dec"]) == (133.761244, -7.242304)
