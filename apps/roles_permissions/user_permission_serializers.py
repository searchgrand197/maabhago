from rest_framework import serializers

from apps.roles_permissions.models import UserModulePermission, UserPermissionProfile


class UserModulePermissionSerializer(serializers.ModelSerializer):
    module_code = serializers.CharField(source="module.code", read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)

    class Meta:
        model = UserModulePermission
        fields = (
            "id",
            "module",
            "module_code",
            "module_name",
            "can_add",
            "can_edit",
            "can_delete",
            "can_view",
            "can_print",
            "can_download",
            "is_active",
        )
        read_only_fields = ("id", "module_code", "module_name")


class UserModulePermissionWriteSerializer(serializers.ModelSerializer):
    """Nested write payload (no ``profile`` — set by parent)."""

    class Meta:
        model = UserModulePermission
        fields = (
            "module",
            "can_add",
            "can_edit",
            "can_delete",
            "can_view",
            "can_print",
            "can_download",
            "is_active",
        )


class UserPermissionProfileSerializer(serializers.ModelSerializer):
    """Read: mirrors admin Users permissions + module link rows."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_first_name = serializers.CharField(source="user.first_name", read_only=True)
    user_last_name = serializers.CharField(source="user.last_name", read_only=True)
    hospital_id = serializers.UUIDField(source="user.hospital_id", read_only=True, allow_null=True)
    module_links = UserModulePermissionSerializer(many=True, read_only=True)

    class Meta:
        model = UserPermissionProfile
        fields = (
            "id",
            "user",
            "user_email",
            "user_first_name",
            "user_last_name",
            "hospital_id",
            "module_links",
        )


class UserPermissionProfileCreateSerializer(serializers.ModelSerializer):
    module_links = UserModulePermissionWriteSerializer(many=True, required=False, default=list)

    class Meta:
        model = UserPermissionProfile
        fields = ("id", "user", "module_links")
        read_only_fields = ("id",)

    def validate_user(self, value):
        if UserPermissionProfile.objects.filter(user=value).exists():
            raise serializers.ValidationError("A permission profile already exists for this user.")
        return value

    def create(self, validated_data):
        links_data = validated_data.pop("module_links", [])
        profile = UserPermissionProfile.objects.create(**validated_data)
        for row in links_data:
            UserModulePermission.objects.create(profile=profile, **row)
        return profile


class UserPermissionProfileUpdateSerializer(serializers.ModelSerializer):
    """``module_links`` replaces all links when provided (same as admin save)."""

    module_links = UserModulePermissionWriteSerializer(many=True, required=False)

    class Meta:
        model = UserPermissionProfile
        fields = ("id", "module_links")
        read_only_fields = ("id",)

    def update(self, instance, validated_data):
        links_data = validated_data.pop("module_links", serializers.empty)
        instance = super().update(instance, validated_data)
        if links_data is not serializers.empty:
            instance.module_links.all().delete()
            for row in links_data or []:
                UserModulePermission.objects.create(profile=instance, **row)
        return instance
