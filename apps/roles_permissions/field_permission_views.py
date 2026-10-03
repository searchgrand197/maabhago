from django.db import transaction
from rest_framework import permissions
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from apps.roles_permissions.field_registry import MODULE_FIELDS, list_modules_for_api
from apps.roles_permissions.field_serializers import FieldPermissionBulkUpdateSerializer
from apps.roles_permissions.models import Role, RoleFieldPermission
from apps.shared.response import success_response


def _role_queryset_for_user(request):
    qs = Role.objects.filter(is_deleted=False, is_active=True)
    if not request.user.is_superuser:
        if request.user.hospital_id is None:
            return qs.none()
        qs = qs.filter(hospital_id=request.user.hospital_id)
    return qs.order_by("name")


def _get_role_or_404(request, role_id):
    role = _role_queryset_for_user(request).filter(pk=role_id).first()
    if not role:
        raise NotFound("Role not found or not in scope.")
    return role


def _validate_row(module_code: str, field_key: str) -> None:
    mod = MODULE_FIELDS.get(module_code)
    if not mod:
        raise ValidationError({"module_code": [f"Unknown module: {module_code}"]})
    allowed = {f["key"] for f in mod["fields"]}
    if field_key not in allowed:
        raise ValidationError(
            {"field_key": [f"Unknown field {field_key!r} for module {module_code!r}"]}
        )


class FieldPermissionSchemaView(APIView):
    """Returns all modules and field definitions (no DB state)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return success_response(data={"modules": list_modules_for_api()})


class FieldPermissionRoleListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        roles = _role_queryset_for_user(request).values("id", "name", "code")
        return success_response(data={"roles": list(roles)})


class FieldPermissionMatrixView(APIView):
    """
    GET: merged registry + stored RoleFieldPermission flags for one role.
    PATCH: replace matrix rows (validated against field_registry).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, role_id, *args, **kwargs):
        role = _get_role_or_404(request, role_id)
        stored = {
            (r.module_code, r.field_key): r
            for r in RoleFieldPermission.objects.filter(role=role).only(
                "module_code",
                "field_key",
                "can_create",
                "can_read",
                "can_update",
            )
        }
        modules_out = []
        for mod in list_modules_for_api():
            code = mod["code"]
            fields_out = []
            for f in mod["fields"]:
                key = f["key"]
                rec = stored.get((code, key))
                fields_out.append(
                    {
                        "key": key,
                        "label": f["label"],
                        "can_create": rec.can_create if rec else False,
                        "can_read": rec.can_read if rec else False,
                        "can_update": rec.can_update if rec else False,
                    }
                )
            modules_out.append({"code": code, "name": mod["name"], "fields": fields_out})

        return success_response(
            data={
                "role": {"id": role.id, "name": role.name, "code": role.code},
                "modules": modules_out,
            }
        )

    def patch(self, request, role_id, *args, **kwargs):
        role = _get_role_or_404(request, role_id)
        ser = FieldPermissionBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rows = ser.validated_data["rows"]

        for row in rows:
            _validate_row(row["module_code"], row["field_key"])

        with transaction.atomic():
            for r in rows:
                m, fkey = r["module_code"], r["field_key"]
                any_on = r["can_create"] or r["can_read"] or r["can_update"]
                qs = RoleFieldPermission.objects.filter(role=role, module_code=m, field_key=fkey)
                if not any_on:
                    qs.delete()
                else:
                    RoleFieldPermission.objects.update_or_create(
                        role=role,
                        module_code=m,
                        field_key=fkey,
                        defaults={
                            "can_create": r["can_create"],
                            "can_read": r["can_read"],
                            "can_update": r["can_update"],
                        },
                    )

        return success_response(
            message="Field permissions updated.",
            data={"role_id": role.id, "rows_applied": len(rows)},
        )
