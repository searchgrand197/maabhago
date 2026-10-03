from rest_framework import serializers


class FieldPermissionRowSerializer(serializers.Serializer):
    module_code = serializers.CharField(max_length=100)
    field_key = serializers.CharField(max_length=100)
    can_create = serializers.BooleanField()
    can_read = serializers.BooleanField()
    can_update = serializers.BooleanField()


class FieldPermissionBulkUpdateSerializer(serializers.Serializer):
    rows = FieldPermissionRowSerializer(many=True)
