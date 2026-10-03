from __future__ import annotations

from rest_framework import serializers

from apps.tokens.models import DailyTokenCounter, Token


class DailyTokenCounterSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)

    class Meta:
        model = DailyTokenCounter
        fields = ["id", "hospital_id", "doctor", "doctor_name", "date", "current_number", "created_at", "updated_at"]


class TokenSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    patient_uhid = serializers.CharField(source="patient.uhid", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    appointment_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Token
        fields = [
            "id",
            "hospital_id",
            "doctor",
            "doctor_name",
            "patient",
            "patient_uhid",
            "date",
            "token_number",
            "queue_order",
            "appointment",
            "appointment_id",
            "status",
            "status_label",
            "called_by",
            "called_at",
            "created_by",
            "created_at",
            "updated_at",
        ]


class TokenCreateSerializer(serializers.Serializer):
    doctor = serializers.UUIDField()
    patient = serializers.UUIDField()
    date = serializers.DateField(required=False)
    appointment = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("date"):
            # default handled in view
            return attrs
        return attrs

    def create(self, validated_data):
        # Token number assignment is handled in the view to keep it atomic.
        raise NotImplementedError("Use TokenViewSet.perform_create()")

