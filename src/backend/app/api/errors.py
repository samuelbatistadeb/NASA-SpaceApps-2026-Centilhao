"""Domain errors and their mapping to the API contract.

``docs/architecture/api-contract.md`` section 8 defines six error codes and the
``{"error": {"code": ..., "message": ...}}`` envelope. Every failure raised by
the backend is expressed as an :class:`ApiError` subclass so that the router
and the global handlers can translate it consistently.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Base class of every error that the API is allowed to expose."""

    #: Machine readable code published to the client.
    code: str = "INTERNAL_ERROR"
    #: HTTP status that reflects the nature of the error.
    status_code: int = 500

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        #: Technical detail kept for the server log only.
        self.detail = detail

    def payload(self) -> dict[str, dict[str, str]]:
        """Return the JSON body described by the API contract section 8."""
        return {"error": {"code": self.code, "message": self.message}}


class InvalidParametersError(ApiError):
    """The request parameters are outside the accepted ranges."""

    code = "INVALID_PARAMETERS"
    status_code = 400


class NoObservationsFoundError(ApiError):
    """The archive was queried successfully but no observation matched."""

    code = "NO_OBSERVATIONS_FOUND"
    status_code = 404


class SourceUnavailableError(ApiError):
    """The scientific source (IRSA) could not be reached or did not answer."""

    code = "SOURCE_UNAVAILABLE"
    status_code = 503


class MalformedResponseError(SourceUnavailableError):
    """The source answered, but the payload could not be interpreted."""

    code = "SOURCE_UNAVAILABLE"
    status_code = 503


class ProcessingError(ApiError):
    """A scientific file could not be processed."""

    code = "PROCESSING_ERROR"
    status_code = 500


class ImageNotFoundError(ApiError):
    """No processed image is available for the requested observation."""

    code = "IMAGE_NOT_FOUND"
    status_code = 404


class InternalError(ApiError):
    """Unexpected internal failure."""

    code = "INTERNAL_ERROR"
    status_code = 500
