from __future__ import annotations

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from apps.roles_permissions.models import UserPermissionProfile
from apps.roles_permissions.permissions import HasRequiredPermission
from apps.roles_permissions.user_permission_serializers import (
    UserPermissionProfileCreateSerializer,
    UserPermissionProfileSerializer,
    UserPermissionProfileUpdateSerializer,
)
from apps.shared.response import success_response


class UserPermissionProfileViewSet(viewsets.ModelViewSet):
    """
    REST API for **Users permissions** (same data as
    ``/admin/roles_permissions/userpermissionprofile/``).

    - List / retrieve profiles for users in your hospital (superuser: all).
    - ``POST`` / ``PATCH`` accept nested ``module_links`` (replace links on update when supplied).
    - ``GET .../me/`` returns the authenticated user's profile (or 404).
    """

    queryset = UserPermissionProfile.objects.all().select_related("user").prefetch_related(
        "module_links__module"
    )
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("user",)

    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]

    required_permission_map = {
        "list": "staff.view_staff",
        "retrieve": "staff.view_staff",
        "create": "staff.update_staff",
        "update": "staff.update_staff",
        "partial_update": "staff.update_staff",
        "destroy": "staff.update_staff",
    }

    def get_serializer_class(self):
        if self.action == "create":
            return UserPermissionProfileCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserPermissionProfileUpdateSerializer
        return UserPermissionProfileSerializer

    def get_required_permission(self) -> str | None:
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        if getattr(self, "action", None) == "me":
            return [permissions.IsAuthenticated()]
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs.order_by("-id")
        if user.hospital_id is None:
            return qs.none()
        return qs.filter(user__hospital_id=user.hospital_id).order_by("-id")

    def _ensure_user_in_scope(self, target_user):
        req = self.request.user
        if req.is_superuser:
            return
        if target_user.hospital_id != req.hospital_id:
            raise ValidationError({"user": ["User is not in your hospital."]})

    def perform_create(self, serializer):
        self._ensure_user_in_scope(serializer.validated_data["user"])
        with transaction.atomic():
            serializer.save()

    def perform_update(self, serializer):
        self._ensure_user_in_scope(serializer.instance.user)
        with transaction.atomic():
            serializer.save()

    def perform_destroy(self, instance):
        self._ensure_user_in_scope(instance.user)
        instance.delete()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ser = self.get_serializer(queryset, many=True)
        return success_response(data=ser.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(data=self.get_serializer(instance).data)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)
        out = UserPermissionProfileSerializer(ser.instance).data
        return success_response(data=out, status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        self.perform_update(ser)
        return success_response(data=UserPermissionProfileSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        pk = instance.pk
        self.perform_destroy(instance)
        return success_response(data={"id": pk}, status_code=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request, *args, **kwargs):
        """Current user's profile + module links (any authenticated user)."""
        profile = (
            UserPermissionProfile.objects.filter(user_id=request.user.id)
            .select_related("user")
            .prefetch_related("module_links__module")
            .first()
        )
        if not profile:
            return success_response(data=None, status_code=status.HTTP_404_NOT_FOUND)
        return success_response(data=UserPermissionProfileSerializer(profile).data)
