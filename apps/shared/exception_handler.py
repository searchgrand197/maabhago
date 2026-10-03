from typing import Any, Dict

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db.models.deletion import ProtectedError
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response


def api_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Centralized exception handler that returns a consistent API response shape.
    """

    request = context.get("request")

    request_id = None
    if request is not None:
        request_id = request.headers.get("X-Request-ID") or request.headers.get("X_REQUEST_ID")

    def build(errors, status_code: int):
        payload: Dict[str, Any] = {"success": False, "request_id": request_id, "errors": errors}
        return Response(payload, status=status_code)

    if isinstance(exc, drf_exceptions.NotAuthenticated):
        return build({"detail": "Authentication credentials were not provided."}, 401)

    if isinstance(exc, drf_exceptions.AuthenticationFailed):
        return build({"detail": str(exc)}, 401)

    if isinstance(exc, drf_exceptions.PermissionDenied) or isinstance(exc, DjangoPermissionDenied):
        return build({"detail": "You do not have permission to perform this action."}, 403)

    if isinstance(exc, drf_exceptions.ValidationError):
        return build(getattr(exc, "detail", None) or {"detail": "Invalid request."}, 400)

    if isinstance(exc, drf_exceptions.ParseError):
        return build({"detail": "Malformed JSON or invalid payload."}, 400)

    if isinstance(exc, drf_exceptions.NotFound):
        return build({"detail": "Not found."}, 404)

    if isinstance(exc, ProtectedError):
        # e.g. DELETE department still linked by staff, doctors, or specialties (PROTECT FKs).
        return build(
            {
                "detail": "Cannot delete this record because other records still reference it. "
                "Remove or reassign those links first (e.g. staff, doctors, specialties)."
            },
            409,
        )

    # DRF's APIException subclasses have a status_code.
    if isinstance(exc, drf_exceptions.APIException):
        status_code = getattr(exc, "status_code", 500)
        return build(getattr(exc, "detail", {"detail": "Server error."}), status_code)

    # Fallback: never leak internals to clients.
    return build({"detail": "Internal server error."}, 500)

