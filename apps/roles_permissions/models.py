from django.conf import settings
from django.db import models

from apps.shared.models import Hospital, SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel
from apps.staff.models import Designation


class Module(TimeStampedModel, UUIDPrimaryKeyModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:
        return self.code


class Permission(UUIDPrimaryKeyModel, TimeStampedModel):
    class Actions(models.TextChoices):
        VIEW = "view"
        CREATE = "create"
        UPDATE = "update"
        DELETE = "delete"
        APPROVE = "approve"
        EXPORT = "export"
        PRINT = "print"
        ACCESS = "access"

    module = models.ForeignKey(Module, on_delete=models.PROTECT, related_name="permissions")
    action = models.CharField(max_length=20, choices=Actions.choices)
    code = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["code"]), models.Index(fields=["action"])]

    def __str__(self) -> str:
        return self.code


class PermissionGroup(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="permission_groups")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("hospital", "code")]

    def __str__(self) -> str:
        return self.code


class GroupPermission(models.Model):
    group = models.ForeignKey(PermissionGroup, on_delete=models.CASCADE, related_name="group_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="group_permissions")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("group", "permission")]


class Role(SoftDeleteModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="roles")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=100)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["code"])]
        unique_together = [("hospital", "code")]

    def __str__(self) -> str:
        return self.code


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("role", "permission")]


class DesignationPermissionProfile(models.Model):
    """Pick a staff designation (dropdown), then attach RBAC modules via inlines."""

    designation = models.OneToOneField(
        Designation,
        on_delete=models.CASCADE,
        related_name="module_permission_profile",
    )

    class Meta:
        verbose_name = "Designation permission"
        verbose_name_plural = "Designation permissions"

    def __str__(self) -> str:
        return f"{self.designation}"


class DesignationModulePermission(models.Model):
    """Module links for a designation permission profile."""

    profile = models.ForeignKey(
        DesignationPermissionProfile,
        on_delete=models.CASCADE,
        related_name="module_links",
        db_index=True,
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="designation_permissions", db_index=True)
    can_add = models.BooleanField("Add", default=False)
    can_edit = models.BooleanField("Edit", default=False)
    can_delete = models.BooleanField("Delete", default=False)
    can_view = models.BooleanField("View", default=False)
    can_print = models.BooleanField("Print", default=False)
    can_download = models.BooleanField("Download", default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "module"],
                name="roles_permissions_profile_module_uniq",
            ),
        ]
        verbose_name = "Module link"
        verbose_name_plural = "Module links"

    def __str__(self) -> str:
        return f"{self.profile_id} → {self.module_id}"


class UserPermissionProfile(models.Model):
    """Pick a user, then attach RBAC modules + actions (same pattern as designation permissions)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rbac_module_profile",
    )

    class Meta:
        verbose_name = "Users permission"
        verbose_name_plural = "Users permissions"

    def __str__(self) -> str:
        return str(self.user)


class UserModulePermission(models.Model):
    """Module links for a user permission profile."""

    profile = models.ForeignKey(
        UserPermissionProfile,
        on_delete=models.CASCADE,
        related_name="module_links",
        db_index=True,
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="user_module_permissions", db_index=True
    )
    can_add = models.BooleanField("Add", default=False)
    can_edit = models.BooleanField("Edit", default=False)
    can_delete = models.BooleanField("Delete", default=False)
    can_view = models.BooleanField("View", default=False)
    can_print = models.BooleanField("Print", default=False)
    can_download = models.BooleanField("Download", default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "module"],
                name="roles_permissions_user_profile_module_uniq",
            ),
        ]
        verbose_name = "Module link"
        verbose_name_plural = "Module links"

    def __str__(self) -> str:
        return f"{self.profile_id} → {self.module_id}"


class RoleFieldPermission(models.Model):
    """
    Per-role field-level Create / Read / Update flags for a logical module field
    (see apps.roles_permissions.field_registry.MODULE_FIELDS).
    """

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="field_permissions")
    module_code = models.CharField(max_length=100, db_index=True)
    field_key = models.CharField(max_length=100)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "module_code", "field_key"],
                name="roles_permissions_role_module_field_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["role", "module_code"]),
        ]

    def __str__(self) -> str:
        return f"{self.role_id} {self.module_code}.{self.field_key}"
