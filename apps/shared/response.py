from typing import Any, Dict, Optional

from rest_framework.response import Response


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
) -> Response:
    payload: Dict[str, Any] = {"success": True, "data": data}
    # Alias for clients that expect `entity` instead of `data`.
    if data is not None:
        payload["entity"] = data
    if message:
        payload["message"] = message
    if meta is not None:
        payload["meta"] = meta
    return Response(payload, status=status_code)

