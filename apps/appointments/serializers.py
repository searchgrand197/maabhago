from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from apps.patients.models import Patient


class AppointmentSerializer(serializers.ModelSerializer):
    patient_uhid = serializers.CharField(source="patient.uhid", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    doctor_specialty = serializers.CharField(source="doctor.specialty.name", read_only=True)
    hospital_id = serializers.UUIDField(read_only=True)
    receptionist_email = serializers.EmailField(source="receptionist_user.email", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "hospital_id",
            "patient",
            "patient_uhid",
            "doctor",
            "doctor_name",
            "doctor_specialty",
            "appointment_datetime",
            "consultation_type",
            "status",
            "queue_order",
            "receptionist_user",
            "receptionist_email",
            "symptoms",
            "reason_for_visit",
            "internal_remarks",
            "rescheduled_from",
            "created_at",
            "updated_at",
        ]


class AppointmentCreateUpdateSerializer(serializers.ModelSerializer):
    patient = serializers.UUIDField()
    doctor = serializers.UUIDField()

    class Meta:
        model = Appointment
        fields = [
            "patient",
            "doctor",
            "appointment_datetime",
            "consultation_type",
            "status",
            "symptoms",
            "reason_for_visit",
            "internal_remarks",
            "rescheduled_from",
        ]
        extra_kwargs = {
            "status": {"required": False},
        }

    def validate(self, attrs):
        appointment_datetime = attrs.get("appointment_datetime")
        doctor_id = attrs.get("doctor")
        hospital_id = None

        patient_id = attrs.get("patient")
        if patient_id:
            patient = Patient.objects.select_related("hospital").filter(pk=patient_id).first()
            if patient:
                hospital_id = patient.hospital_id

        if doctor_id and not hospital_id:
            doctor = DoctorProfile.objects.select_related("hospital").filter(pk=doctor_id).first()
            if doctor:
                hospital_id = doctor.hospital_id

        if appointment_datetime and doctor_id and hospital_id:
            # Prevent double-slot booking for the same doctor/time in same hospital.
            existing = Appointment.objects.filter(
                hospital_id=hospital_id,
                doctor_id=doctor_id,
                appointment_datetime=appointment_datetime,
            )
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exclude(status=Appointment.Status.CANCELLED).exists():
                raise serializers.ValidationError(
                    {"appointment_datetime": ["This slot is already booked for this doctor."]}
                )

        return attrs

    def create(self, validated_data):
        patient_obj = Patient.objects.get(pk=validated_data["patient"])
        doctor_obj = DoctorProfile.objects.get(pk=validated_data["doctor"])
        validated_data["patient"] = patient_obj
        validated_data["doctor"] = doctor_obj
        rest = {k: v for k, v in validated_data.items() if k not in {"patient", "doctor"}}
        # Model requires booked_at; API clients typically only send appointment_datetime.
        rest.setdefault("booked_at", rest.get("appointment_datetime") or timezone.now())
        return Appointment.objects.create(
            hospital=patient_obj.hospital,
            patient=patient_obj,
            doctor=doctor_obj,
            receptionist_user=self.context["request"].user if self.context.get("request") else None,
            **rest,
        )

