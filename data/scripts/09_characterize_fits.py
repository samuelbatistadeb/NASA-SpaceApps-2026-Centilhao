"""Step 9 - Full FITS characterization of a real SPHEREx DR1 cutout.

The SPHEREx L2 "Spectral Image" MEF stores the science array in the IMAGE
extension; the PRIMARY header carries almost nothing. All observation/WCS
metadata therefore come from the IMAGE extension header (HDU 1).

Produces:
  data/processed/<tag>_fits_structure.txt   full HDU list + complete headers
  data/processed/<tag>_fits_analysis.json   machine-readable summary
  data/processed/<tag>_header_main.txt       complete IMAGE-extension header

The file under data/raw/ is opened read-only and never modified.

Usage:
    .\\.venv\\Scripts\\python.exe data\\scripts\\09_characterize_fits.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "processed"
TAG = "2026-11-14_spherex_dr1_l2b_2025W19_1B_0116_1D3"
TARGET = RAW / TAG / "cutout_wise0855_size0.02.fits"

OBS_KEYS = [
    "DATE-OBS", "DATE-BEG", "DATE-AVG", "DATE-END", "MJD-OBS", "MJD-BEG",
    "MJD-AVG", "MJD-END", "EXPSTART", "EXPEND", "OBS-TIME", "OBS-TIME-S",
    "EXPTIME", "XPOSURE", "TELAPSE", "TOTALEXP", "FILTER", "WAVELNTH",
    "WAVELEN", "BAND", "BANDNAME", "BUNIT", "DETECTOR", "DET-ID", "DETID",
    "TELESCOP", "INSTRUME", "ORIGIN", "DATE", "PIPEVER", "VERSION", "LEVEL",
    "BSCALE", "BZERO", "CALVER", "CREATOR", "OBSID", "EXPIDN", "EXTNAME",
    "EXTTYPE", "PSF_FWHM", "OMEGA_MEDIAN", "OMEGA_STDDEV", "TSAMP",
    "SPS_TARGET", "SPS_FLAGS", "NON_SURVEY", "L1DQAFLG", "L2DQAFLG",
    "PXSRCMSK", "KOVR_A", "A_ORDER", "B_ORDER", "WCSAXES", "RADESYS",
    "TIMESYS", "MJDREF", "DAXIS", "MATCH_NSTARS", "ASTRONETSOLVED",
    "CTYPE1", "CTYPE2", "CUNIT1", "CUNIT2", "CRPIX1", "CRPIX2", "CRVAL1",
    "CRVAL2", "CDELT1", "CDELT2", "PC1_1", "PC1_2", "PC2_1", "PC2_2",
    "CTYPE1W", "CTYPE2W", "CUNIT1W", "CUNIT2W", "WCSNAMEW", "WCSAXESW",
    "SNWSTRK", "NBLMSRCS", "NSNOWSRC",
]


def build_wcs(header):
    """Build a WCS from a FITS header that provides PC + CDELT but no CD.

    The SPHEREx L2 IMAGE header carries PCi_j and CDELTi (=1.0) but no CDi_j.
    The FITS convention is CDi_j = CDELTi * PCi_j, so we materialise the CD
    matrix in a *copy* of the header (the original file is never touched) and
    then let astropy parse it, which also preserves the SIP A_/B_ distortion
    coefficients referenced by CTYPE='RA---TAN-SIP'.
    """
    hdr = header.copy()
    try:
        pc = np.array([[float(hdr["PC1_1"]), float(hdr["PC1_2"])],
                       [float(hdr["PC2_1"]), float(hdr["PC2_2"])]])
        cdelt = np.array([float(hdr.get("CDELT1", 1.0)), float(hdr.get("CDELT2", 1.0))])
        cd = np.array([[pc[0, 0] * cdelt[0], pc[0, 1] * cdelt[1]],
                       [pc[1, 0] * cdelt[0], pc[1, 1] * cdelt[1]]])
        for i in range(2):
            for j in range(2):
                hdr[f"CD{i+1}_{j+1}"] = float(cd[i, j])
    except KeyError:
        pass
    return WCS(hdr, naxis=2, relax=True)


def main() -> int:
    if not TARGET.exists():
        print("MISSING:", TARGET)
        return 1

    lines: list[str] = []

    def p(s: str = "") -> None:
        lines.append(s)
        print(s)

    p("=" * 100)
    p(f"FITS CHARACTERIZATION: {TARGET}")
    p(f"analyzed_at_utc = {datetime.now(timezone.utc).isoformat()}")
    p(f"file size = {TARGET.stat().st_size} bytes ({TARGET.stat().st_size/1e6:.3f} MB)")
    p("=" * 100)

    summary: dict = {
        "file": str(TARGET),
        "analyzed_at_utc": datetime.now(timezone.utc).isoformat(),
        "file_bytes": TARGET.stat().st_size,
        "hdus": [],
    }

    with fits.open(TARGET, memmap=False, lazy_load_hdus=False) as hdul:
        p("")
        p("### 1. HDU LIST")
        p(f"{'#':>2} {'NAME':<14} {'TYPE':<16} {'SHAPE':<22} {'NAXIS':<7} {'SIZE_MB':>9}  EXTNAME")
        p("-" * 110)
        for i, h in enumerate(hdul):
            shape = str(tuple(h.shape)) if getattr(h, "shape", None) else "()"
            nbytes = (int(h.size * h.header.get("BITPIX", 8) / 8)
                      if getattr(h, "shape", None) else 0)
            p(f"{i:>2} {h.name:<14} {type(h).__name__:<16} {shape:<22} "
              f"{h.header.get('NAXIS','-'):<7} {nbytes/1e6:>9.3f}  "
              f"{h.header.get('EXTNAME','')}")
            summary["hdus"].append({
                "index": i, "name": h.name, "type": type(h).__name__,
                "shape": list(getattr(h, "shape", None) or []) or None,
                "naxis": h.header.get("NAXIS"),
                "bitpix": h.header.get("BITPIX"),
                "data_bytes": nbytes,
                "extname": h.header.get("EXTNAME"),
                "hduclas1": h.header.get("HDUCLAS1"),
                "hduclas2": h.header.get("HDUCLAS2"),
                "hduclas3": h.header.get("HDUCLAS3"),
                "hduclas4": h.header.get("HDUCLAS4"),
                "n_keywords": len(h.header),
            })

        # ---- complete header of every HDU ----
        p("")
        p("### 2. COMPLETE HEADERS (all HDUs)")
        for i, h in enumerate(hdul):
            p("")
            p(f"----- HDU {i}: name={h.name!r} type={type(h).__name__} -----")
            p(repr(h.header))
        (OUT / f"{TAG}_header_main.txt").write_text(
            repr(hdul[1].header), encoding="utf-8")

        MAIN = hdul[1]           # IMAGE extension = science array + all metadata
        hdr0 = MAIN.header

        # ---- observation keywords ----
        p("")
        p("### 3. OBSERVATION / CALIBRATION KEYWORDS IN THE IMAGE (SCIENCE) HDU")
        p(f"{'KEYWORD':<12} {'VALUE':<58} {'COMMENT'}")
        p("-" * 140)
        found: dict = {}
        for k in OBS_KEYS:
            if k in hdr0:
                v = hdr0[k]
                try:
                    c = hdr0.comments[k]
                except Exception:  # noqa: BLE001
                    c = ""
                found[k] = str(v)
                p(f"{k:<12} {str(v):<58} {c}")
        summary["primary_obs_keywords"] = found

        # ---- mask planes (defined in the FLAGS HDU header) ----
        p("")
        p("### 3b. MASK PLANE DEFINITIONS (MSKN/MSKM/MSKD) in FLAGS HDU header")
        flag_hdr = hdul[2].header
        mask_planes = []
        for key in sorted(flag_hdr.keys()):
            if key.startswith("MSKN"):
                idx = key[4:]
                try:
                    name = str(flag_hdr[key])
                except Exception:  # noqa: BLE001
                    name = None
                try:
                    bit = flag_hdr[f"MSKM{idx}"]
                except Exception:  # noqa: BLE001
                    bit = None
                try:
                    desc = flag_hdr[f"MSKD{idx}"]
                except Exception:  # noqa: BLE001
                    desc = ""
                p(f"  {idx}: name={name!r}  bitmask={bit}  desc={desc!r}")
                mask_planes.append({"index": idx, "name": name, "bitmask": bit,
                                    "description": desc})
        summary["mask_planes"] = mask_planes

        # ---- WCS ----
        p("")
        p("### 4. WCS OF THE IMAGE (SCIENCE) HDU")
        try:
            w = build_wcs(hdr0)
            p(f"  wcs.naxis   = {w.naxis}")
            for i in range(w.naxis):
                p(f"  CTYPE{i+1}    = {hdr0.get(f'CTYPE{i+1}')}")
                p(f"  CUNIT{i+1}    = {hdr0.get(f'CUNIT{i+1}')}")
                p(f"  CRPIX{i+1}    = {hdr0.get(f'CRPIX{i+1}')}")
                p(f"  CRVAL{i+1}    = {hdr0.get(f'CRVAL{i+1}')}")
                p(f"  CDELT{i+1}    = {hdr0.get(f'CDELT{i+1}')}")
            p(f"  PC matrix   = {np.array(w.wcs.pc).tolist()}")
            p(f"  CD matrix   = {np.array(w.wcs.cd).tolist()}")
            px1 = float(hdr0["PC1_1"]) * 3600.0
            px2 = float(hdr0["PC2_2"]) * 3600.0
            p(f"  => |PC1_1| = {px1:.4f} arcsec/pixel ; |PC2_2| = {px2:.4f} arcsec/pixel")
            p(f"  => PSF_FWHM = {hdr0.get('PSF_FWHM')} arcsec")
            p(f"  => OMEGA_MEDIAN (pixel solid angle) = {hdr0.get('OMEGA_MEDIAN')} arcsec^2")
            p(f"  => NAXIS1 x NAXIS2 = {hdr0['NAXIS1']} x {hdr0['NAXIS2']} pixels")
            p(f"  => cutout angular width ~= {hdr0['NAXIS1']*px1/60:.3f} arcmin "
              f"x {hdr0['NAXIS2']*px2/60:.3f} arcmin")
            summary["wcs"] = {
                "naxis": w.naxis,
                "pc": np.array(w.wcs.pc).tolist(),
                "cd": np.array(w.wcs.cd).tolist(),
                "pixscale_arcsec": [px1, px2],
                "ctype": [hdr0.get("CTYPE1"), hdr0.get("CTYPE2")],
                "crpix": [hdr0.get("CRPIX1"), hdr0.get("CRPIX2")],
                "crval": [hdr0.get("CRVAL1"), hdr0.get("CRVAL2")],
                "cunit": [hdr0.get("CUNIT1"), hdr0.get("CUNIT2")],
                "cdelt_deg": [hdr0.get("CDELT1"), hdr0.get("CDELT2")],
                "psf_fwhm_arcsec": hdr0.get("PSF_FWHM"),
                "omega_median_arcsec2": hdr0.get("OMEGA_MEDIAN"),
                "naxis_pix": [hdr0.get("NAXIS1"), hdr0.get("NAXIS2")],
            }
        except Exception as exc:  # noqa: BLE001
            p(f"  WCS parsing failed: {type(exc).__name__}: {exc}")
            summary["wcs_error"] = f"{type(exc).__name__}: {exc}"

        # ---- data / quality per HDU ----
        p("")
        p("### 5. DATA + QUALITY PER HDU")
        for i, h in enumerate(hdul):
            if not getattr(h, "shape", None):
                if getattr(h, "columns", None) is not None:
                    p("")
                    p(f"  HDU {i} ({h.name}, {type(h).__name__}) BINTABLE nrows={h.header.get('NAXIS2')}")
                    cols = list(h.columns.names)
                    p(f"    columns ({len(cols)}): {cols}")
                    p(f"    formats: {[h.columns[c].format for c in cols]}")
                    p(f"    units:   {[str(h.columns[c].unit) for c in cols]}")
                    p(f"    desc:    {[getattr(h.columns[c], 'description', None) for c in cols]}")
                    try:
                        for row in h.data[:2]:
                            p(f"    row: {tuple(row)}")
                    except Exception as exc:  # noqa: BLE001
                        p(f"    row read failed: {exc}")
                    summary.setdefault("bin_tables", {})[h.name] = {
                        "columns": cols,
                        "formats": [h.columns[c].format for c in cols],
                        "units": [str(h.columns[c].unit) for c in cols],
                        "nrows": h.header.get("NAXIS2"),
                    }
                continue
            try:
                data = h.data
            except Exception as exc:  # noqa: BLE001
                p(f"  HDU {i}: data load failed: {exc}")
                continue
            arr = np.asarray(data)
            p("")
            p(f"  HDU {i} ({h.name}, {type(h).__name__}) shape={arr.shape} dtype={arr.dtype}")
            p(f"    BUNIT={h.header.get('BUNIT')!r} BSCALE={h.header.get('BSCALE')!r} "
              f"BZERO={h.header.get('BZERO')!r}")
            if arr.dtype.kind == "f":
                fin = arr[np.isfinite(arr)]
                if fin.size:
                    p(f"    min={fin.min():.6g}  max={fin.max():.6g}  "
                      f"median={np.median(fin):.6g}  mean={fin.mean():.6g}  "
                      f"std={fin.std():.6g}")
                p(f"    n_nan={int(np.isnan(arr).sum())}  n_inf={int(np.isinf(arr).sum())}  "
                  f"n_zero={int((arr == 0).sum())}  total={arr.size}")
                summary.setdefault("stats", {})[h.name] = {
                    "shape": list(arr.shape), "dtype": str(arr.dtype),
                    "bunit": h.header.get("BUNIT"),
                    "min": float(fin.min()) if fin.size else None,
                    "max": float(fin.max()) if fin.size else None,
                    "median": float(np.median(fin)) if fin.size else None,
                    "mean": float(fin.mean()) if fin.size else None,
                    "std": float(fin.std()) if fin.size else None,
                    "n_nan": int(np.isnan(arr).sum()),
                    "n_zero": int((arr == 0).sum()),
                }
            else:
                vals, cnts = np.unique(arr, return_counts=True)
                p(f"    n_unique={len(vals)}  "
                  f"bitwise_OR={int(np.bitwise_or.reduce(arr.ravel().astype(np.int64)))}")
                if len(vals) <= 40:
                    p(f"    values={vals.tolist()}")
                    p(f"    counts={cnts.tolist()}")
                # per-bit-plane counts using the MSKN/MSKM table
                bitcounts = {}
                for mp in summary.get("mask_planes", []):
                    try:
                        bit = int(mp["bitmask"])
                    except Exception:  # noqa: BLE001
                        continue
                    n = int(((arr.ravel() & bit) != 0).sum())
                    bitcounts[mp["name"]] = n
                    p(f"    flag {mp['name']:<12} (bit {bit:>10d}): {n:>6d} px "
                      f"({100.0*n/arr.size:.2f}%)")
                summary.setdefault("flag_counts", {})[h.name] = bitcounts

        summary["main_header_repr"] = repr(hdr0)

    (OUT / f"{TAG}_fits_structure.txt").write_text("\n".join(lines), encoding="utf-8")
    (OUT / f"{TAG}_fits_analysis.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n\nSaved:\n  {OUT / f'{TAG}_fits_structure.txt'}\n  {OUT / f'{TAG}_fits_analysis.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
