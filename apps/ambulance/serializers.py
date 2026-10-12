from decimal import Decimal

from rest_framework import serializers

from apps.ambulance.models import AmbulanceCollection, AmbulanceVehicle, normalize_vehicle_number


class AmbulanceVehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceVehicle
        fields = [
            "id",
            "vehicle_number",
            "label",
            "driver_name",
            "driver_phone",
            "expected_daily_amount",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_vehicle_number(self, value):
        normalized = normalize_vehicle_number(value)
        if len(normalized) < 4:
            raise serializers.ValidationError("Enter a valid vehicle number.")
        hospital_id = self.context["hospital_id"]
        qs = AmbulanceVehicle.objects.filter(hospital_id=hospital_id, vehicle_number=normalized)
        if self.instance is not None:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("This vehicle is already registered.")
        return normalized

    def validate_expected_daily_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Cannot be negative.")
        return value


class AmbulanceCollectionSerializer(serializers.ModelSerializer):
    vehicle_number = serializers.CharField(source="vehicle.vehicle_number", read_only=True)
    vehicle_label = serializers.CharField(source="vehicle.label", read_only=True)
    collected_by_name = serializers.CharField(source="collected_by.full_name", read_only=True)
    voided_by_name = serializers.CharField(source="voided_by.full_name", read_only=True, default="")

    class Meta:
        model = AmbulanceCollection
        fields = [
            "id",
            "receipt_no",
            "vehicle",
            "vehicle_number",
            "vehicle_label",
            "collected_at",
            "driver_name",
            "driver_phone",
            "trip_count",
            "patient_name",
            "trip_from",
            "trip_to",
            "distance_km",
            "amount",
            "payment_mode",
            "remarks",
            "collected_by",
            "collected_by_name",
            "status",
            "voided",
            "void_reason",
            "voided_at",
            "voided_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "receipt_no",
            "collected_by",
            "status",
            "voided",
            "void_reason",
            "voided_at",
            "created_at",
        ]

    def validate_vehicle(self, vehicle):
        if vehicle.hospital_id != self.context["hospital_id"]:
            raise serializers.ValidationError("Vehicle not found.")
        if not vehicle.is_active:
            raise serializers.ValidationError("This vehicle is inactive.")
        return vehicle

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_trip_count(self, value):
        if value < 1:
            raise serializers.ValidationError("At least one trip is required.")
        return value

    def validate(self, attrs):
        vehicle = attrs.get("vehicle")
        if vehicle is not None:
            if not str(attrs.get("driver_name") or "").strip():
                attrs["driver_name"] = vehicle.driver_name
            if not str(attrs.get("driver_phone") or "").strip():
                attrs["driver_phone"] = vehicle.driver_phone
        for key in ("driver_name", "driver_phone", "patient_name", "trip_from", "trip_to", "remarks"):
            if key in attrs:
                attrs[key] = str(attrs[key] or "").strip()
        return attrs


class VoidSerializer(serializers.Serializer):
    void_reason = serializers.CharField(max_length=500)

    def validate_void_reason(self, value):
        cleaned = str(value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("Cancellation reason is required.")
        return cleaned
