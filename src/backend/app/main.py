"""FastAPI application of the SPHEREx Explorer.

The application exposes the endpoints of ``docs/architecture/api-contract.md``
and converts every failure into the error envelope defined by the contract.

Run locally (Windows PowerShell, from the repository root)::

    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir src\\backend --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.errors import ApiError, InternalError
from app.api.observations import router as observations_router
from app.api.targets import router as targets_router
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="SPHEREx Explorer API",
    version="0.1.0",
    summary=(
        "Query the SPHEREx archive at IRSA and expose the observations and "
        "their processed images for a given sky position."
    ),
    description=(
        "Backend of the SPHEREx Explorer (NASA Space Apps Challenge 2026). "
        "The API queries the official IRSA/SPHEREx archive, organises the "
        "observations chronologically and delivers the processed images."
    ),
)

# CORS is restricted to the localhost origins of the development environment.
# The list is configurable through SPHEREX_CORS_ORIGINS and no credential is
# accepted by the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(observations_router, prefix="/api")
app.include_router(targets_router, prefix="/api")


@app.get(
    "/api/health",
    tags=["service"],
    summary="Service health check",
    description="Returns the status of the service. It carries no scientific data.",
)
def health() -> dict[str, str]:
    """Return the health status of the backend."""
    return {"status": "ok"}


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    """Publish the domain errors using the envelope of the API contract."""
    if exc.detail:
        logger.warning("%s: %s", exc.code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content=exc.payload())


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert the FastAPI validation errors into ``INVALID_PARAMETERS``."""
    logger.info("Invalid request: %s", exc.errors())
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "INVALID_PARAMETERS",
                "message": "Um ou mais parâmetros informados são inválidos.",
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Convert the HTTP errors into the envelope of the API contract."""
    code = "INVALID_PARAMETERS" if exc.status_code in (400, 404, 422) else "INTERNAL_ERROR"
    message = str(exc.detail) if exc.detail else "Erro na requisição."
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unexpected error without exposing internal information."""
    logger.exception("Unexpected error while handling %s", request.url.path)
    error = InternalError("Ocorreu um erro interno ao processar a requisição.")
    return JSONResponse(status_code=error.status_code, content=error.payload())
