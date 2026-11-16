"""SPHEREx Level 2 FLAGS bitmask.

Source (verified on 2026-11-15): header of the FLAGS HDU of a real DR1 cutout
(``MSKNnnnn`` name, ``MSKMnnnn`` mask, ``MSKDnnnn`` description) and Table 16 of
the SPHEREx Explanatory Supplement v2.0 (2026-08-25),
https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf.

When a product header defines its own bits they win (new data releases may
change the mask); the table below is the fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class FlagBit:
    bit: int
    name: str
    description: str


#: Bits documented for DR1 Level 2 (description in Portuguese for the UI).
DEFAULT_BITS: dict[int, FlagBit] = {
    b.bit: b
    for b in (
        FlagBit(0, "TRANSIENT", "raio cósmico ou transiente"),
        FlagBit(1, "OVERFLOW", "saturação"),
        FlagBit(2, "SUR_ERROR", "erro de leitura a bordo"),
        FlagBit(6, "NONFUNC", "pixel morto"),
        FlagBit(7, "DICHROIC", "baixa eficiência (dicroico)"),
        FlagBit(9, "MISSING_DATA", "dado perdido na transmissão"),
        FlagBit(10, "HOT", "pixel quente"),
        FlagBit(11, "COLD", "pixel frio"),
        FlagBit(12, "FULLSAMPLE", "informativo (amostragem completa)"),
        FlagBit(14, "PHANMISS", "correção de pixel fantasma não aplicada"),
        FlagBit(15, "NONLINEAR", "não linearidade não confiável"),
        FlagBit(17, "PERSIST", "persistência"),
        FlagBit(19, "OUTLIER", "valor anômalo"),
        FlagBit(20, "CROSSTALK", "diafonia (crosstalk)"),
        FlagBit(21, "SOURCE", "pixel de fonte conhecida (informativo)"),
        FlagBit(22, "GHOST", "reflexo (ghost) de fonte brilhante"),
        FlagBit(23, "GHOST_FPA", "reflexo vindo de outro detector"),
        FlagBit(24, "GHOST_EXT", "reflexo de fonte fora do campo"),
        FlagBit(25, "STREAK", "rastro de satélite"),
        FlagBit(26, "BLOOM", "transbordamento de fonte (bloom)"),
        FlagBit(27, "SNOWBALL", "snowball"),
        FlagBit(28, "HALO", "halo de transiente"),
        FlagBit(29, "SATELLITE_HALO", "halo de satélite"),
    )
}

#: Not a defect: they only describe the pixel.
INFORMATIONAL_NAMES = frozenset({"SOURCE", "FULLSAMPLE"})


def bits_from_header(header: Mapping[str, object] | None) -> dict[int, FlagBit]:
    """Read ``MSKN/MSKM/MSKD`` keywords; fall back to :data:`DEFAULT_BITS`."""
    bits = dict(DEFAULT_BITS)
    if not header:
        return bits
    for key in list(header.keys()):
        if not str(key).startswith("MSKN"):
            continue
        suffix = str(key)[4:]
        name = str(header.get(key, "")).strip()
        mask = header.get(f"MSKM{suffix}")
        try:
            bit = int(mask).bit_length() - 1
        except (TypeError, ValueError):
            continue
        if bit < 0 or not name:
            continue
        description = DEFAULT_BITS[bit].description if bit in DEFAULT_BITS else str(
            header.get(f"MSKD{suffix}", name)
        ).strip()
        bits[bit] = FlagBit(bit, name, description)
    return bits


def contamination_mask(flags: np.ndarray, bits: Mapping[int, FlagBit] = DEFAULT_BITS) -> np.ndarray:
    """True where a pixel carries a non-informational flag."""
    mask_value = 0
    for bit, info in bits.items():
        if info.name not in INFORMATIONAL_NAMES:
            mask_value |= 1 << bit
    return (np.asarray(flags).astype(np.int64) & mask_value) != 0


def decode(value: int, bits: Mapping[int, FlagBit] = DEFAULT_BITS) -> list[FlagBit]:
    """Flags set in an integer value (known bits only)."""
    return [info for bit, info in sorted(bits.items()) if int(value) & (1 << bit)]


def fraction_by_flag(
    flags: np.ndarray, valid: np.ndarray, bits: Mapping[int, FlagBit] = DEFAULT_BITS
) -> dict[str, float]:
    """Fraction of the valid pixels carrying each flag (only flags present)."""
    values = np.asarray(flags).astype(np.int64)[valid]
    if values.size == 0:
        return {}
    out = {}
    for bit, info in sorted(bits.items()):
        fraction = float(((values >> bit) & 1).mean())
        if fraction > 0:
            out[info.name] = round(fraction, 4)
    return out
