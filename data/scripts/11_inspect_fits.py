
from pathlib import Path
from astropy.io import fits

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FITS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "spherex"
    / "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
)


def main():
    print("Arquivo:", FITS_PATH)

    if not FITS_PATH.is_file():
        print("ERRO: arquivo FITS não encontrado.")
        print("Precisamos realizar o download primeiro.")
        return

    size_mb = FITS_PATH.stat().st_size / (1024 * 1024)
    print(f"Tamanho: {size_mb:.2f} MiB")

    with fits.open(FITS_PATH, memmap=True) as hdul:
        print("\n=== EXTENSÕES FITS ===")
        hdul.info()

        print("\n=== CABEÇALHO PRINCIPAL ===")
        print(repr(hdul[0].header)[:2000])


if __name__ == "__main__":
    main()
