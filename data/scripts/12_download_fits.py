
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DESTINATION_DIR = PROJECT_ROOT / "data" / "raw" / "spherex"

FILENAME = (
    "level2_2025W19_1B_0116_1D3_"
    "spx_l2b-v27-2026-197.fits"
)

URL = (
    "https://irsa.ipac.caltech.edu/ibe/data/spherex/"
    "dr1/level2/2025W19_1B/"
    "l2b-v27-2026-197/3/"
    + FILENAME
)


def download_fits():
    DESTINATION_DIR.mkdir(parents=True, exist_ok=True)

    destination = DESTINATION_DIR / FILENAME
    temporary = DESTINATION_DIR / (FILENAME + ".part")

    print("=== SPHEREx FITS Downloader ===")
    print("Origem:", URL)
    print("Destino:", destination)

    if destination.exists():
        print("\nArquivo já existe.")
        print("Tamanho:", destination.stat().st_size, "bytes")
        return

    try:
        with httpx.Client(
            timeout=httpx.Timeout(180.0, connect=30.0),
            follow_redirects=True,
            trust_env=False,
        ) as client:

            with client.stream("GET", URL) as response:
                response.raise_for_status()

                content_type = response.headers.get(
                    "content-type", ""
                )

                if "fits" not in content_type.lower() and (
                    "octet-stream" not in content_type.lower()
                ):
                    raise ValueError(
                        f"Resposta inesperada: {content_type}"
                    )

                total = int(
                    response.headers.get("content-length", 0)
                )

                downloaded = 0

                with temporary.open("wb") as file:
                    for chunk in response.iter_bytes(
                        chunk_size=1024 * 1024
                    ):
                        if not chunk:
                            continue

                        file.write(chunk)
                        downloaded += len(chunk)

                        if total:
                            percentage = downloaded / total * 100
                            print(
                                f"\rDownload: {percentage:.1f}%",
                                end="",
                                flush=True,
                            )

                if total and downloaded != total:
                    raise IOError(
                        "Download incompleto: "
                        f"{downloaded} de {total} bytes"
                    )

                if downloaded == 0:
                    raise IOError("Arquivo recebido está vazio.")

        temporary.replace(destination)

        print("\n\nDownload concluído!")
        print("Arquivo:", destination)
        print(
            "Tamanho:",
            round(destination.stat().st_size / 1024**2, 2),
            "MiB",
        )

    except Exception as error:
        print("\nFalha no download:", repr(error))

        if temporary.exists():
            temporary.unlink()

        raise


if __name__ == "__main__":
    download_fits()
