"""
DRF routers with a public API root (AllowAny).

DefaultRouter registers GET /api/v1/ as ``api-root``. With global JWT auth,
that page returned 401 in the browsable API. The root only lists hyperlinks;
actual viewsets remain protected by their own permission classes.
"""

from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView, DefaultRouter


class PublicAPIRootView(APIRootView):
    permission_classes = [AllowAny]
    authentication_classes = []


class PublicApiRootRouter(DefaultRouter):
    APIRootView = PublicAPIRootView
