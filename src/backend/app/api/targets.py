"""Example targets offered by the interface (``GET /api/targets``).

Every coordinate below is copied from ``docs/science/target-catalog.md``
(research of 2026-11-14). For objects with high proper motion the position
PROPAGATED to the SPHEREx epochs is used, not the catalogue epoch: WISE 0855
moved ~207" (3.5') since J2000, so the challenge coordinate would leave the
object outside a 3' cutout.

Each target also carries its proper motion and the epoch of ``ra``/``dec``:
the frontend passes them to ``/api/observations``, which cuts every exposure
at the position propagated to its own date (the targets still move up to
~2 pixels across the SPHEREx window).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["targets"])


class TargetEntry(BaseModel):
    """An example target with the position used for the SPHEREx search."""

    name: str
    ra: float = Field(..., description="Right ascension (ICRS, degrees).")
    dec: float = Field(..., description="Declination (ICRS, degrees).")
    fov: float = Field(..., description="Suggested field of view, in arcminutes.")
    position_epoch: str = Field(..., description="Epoch of the position above.")
    note: str = Field(..., description="Short explanation shown to the user.")
    source: str = Field(..., description="Where the position comes from.")
    pm_ra_cosdec_masyr: float | None = Field(
        None, description="Proper motion in RA (with cos dec), mas/yr."
    )
    pm_dec_masyr: float | None = Field(None, description="Proper motion in Dec, mas/yr.")
    ref_epoch_jyear: float | None = Field(
        None, description="Julian year of ra/dec; pass it with the proper motion."
    )


class TargetsResponse(BaseModel):
    targets: list[TargetEntry]


_CATALOG = "docs/science/target-catalog.md"

TARGETS: tuple[TargetEntry, ...] = (
    TargetEntry(
        name="WISE 0855",
        ra=133.737467,
        dec=-7.240406,
        fov=3.0,
        position_epoch="2025.35",
        note="Anã marrom muito fria e próxima, com movimento próprio de ~8″/ano. "
        "Posição propagada para a primeira observação SPHEREx (a coordenada J2000 "
        "do desafio está ~3,5′ distante).",
        source=f"{_CATALOG} §3.3 (propagação de J2000 com μ de Kirkpatrick et al. 2021, via Wikipédia)",
        pm_ra_cosdec_masyr=-8123.7,
        pm_dec_masyr=673.2,
        ref_epoch_jyear=2025.35,
    ),
    TargetEntry(
        name="Estrela de Barnard",
        ra=269.446358,
        dec=4.767053,
        fov=3.0,
        position_epoch="2025.60",
        note="Estrela com o maior movimento próprio conhecido (~10″/ano).",
        source=f"{_CATALOG} §3.1 (Gaia DR3 propagado)",
        pm_ra_cosdec_masyr=-801.551,
        pm_dec_masyr=10362.394,
        ref_epoch_jyear=2025.60,
    ),
    TargetEntry(
        name="ε Indi",
        ra=330.891121,
        dec=-56.803806,
        fov=3.0,
        position_epoch="2025.30",
        note="Sistema próximo (A + anãs marrons B). A componente B não é separada "
        "da A na resolução do SPHEREx.",
        source=f"{_CATALOG} §3.2 (Gaia DR3 propagado)",
        pm_ra_cosdec_masyr=3966.661,
        pm_dec_masyr=-2536.192,
        ref_epoch_jyear=2025.30,
    ),
    TargetEntry(
        name="RW Aurigae",
        ra=76.956081,
        dec=30.401205,
        fov=3.0,
        position_epoch="2016.0",
        note="Estrela jovem variável (componentes A e B inseparáveis no SPHEREx).",
        source=f"{_CATALOG} §3.4 (Gaia DR3)",
        pm_ra_cosdec_masyr=2.641,
        pm_dec_masyr=-27.398,
        ref_epoch_jyear=2016.0,
    ),
    TargetEntry(
        name="R Draconis",
        ra=248.167378,
        dec=66.755007,
        fov=3.0,
        position_epoch="2016.0",
        note="Variável de longo período em campo profundo do SPHEREx: muitas épocas.",
        source=f"{_CATALOG} §3.5 (Gaia DR3)",
        pm_ra_cosdec_masyr=-20.643,
        pm_dec_masyr=6.149,
        ref_epoch_jyear=2016.0,
    ),
)


@router.get(
    "/targets",
    response_model=TargetsResponse,
    summary="Example targets with positions suitable for SPHEREx searches",
)
def list_targets() -> TargetsResponse:
    """Return the example targets used by the interface."""
    return TargetsResponse(targets=list(TARGETS))
