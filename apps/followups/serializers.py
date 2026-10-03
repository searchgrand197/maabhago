from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from apps.followups.models import FollowUp
from apps.patients.models import Patient


class FollowUpSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(read_only=True)
    patient_uhid = serializers.CharField(source="patient.uhid", read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    assigned_email = serializers.EmailField(source="assigned_to_receptionist.email", read_only=True)
    linked_appointment_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            "id",
            "hospital_id",
            "patient",
            "patient_uhid",
            "patient_name",
            "doctor",
            "doctor_name",
            "assigned_to_receptionist",
            "assigned_email",
            "next_visit_date",
            "advice",
            "followup_status",
            "reminder_status",
            "reminder_channel",
            "scheduled_reminder_at",
            "last_reminder_sent_at",
            "call_remark",
            "called_at",
            "linked_appointment",
            "linked_appointment_id",
            "missed_at",
            "internal_remarks",
            "created_at",
            "updated_at",
            "is_deleted",
        ]

    def get_patient_name(self, obj) -> str:
        first = getattr(obj.patient, "first_name", "") or ""
        last = getattr(obj.patient, "last_name", "") or ""
        name = f"{first} {last}".strip()
        return name or obj.patient_uhid


class FollowUpCreateUpdateSerializer(serializers.ModelSerializer):
    doctor = serializers.UUIDField(required=False, allow_null=True)
    assigned_to_receptionist = serializers.UUIDField(required=False, allow_null=True)
    patient = serializers.UUIDField()
    linked_appointment = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = FollowUp
        fields = [
            "patient",
            "doctor",
            "assigned_to_receptionist",
            "next_visit_date",
            "advice",
            "reminder_status",
            "reminder_channel",
            "scheduled_reminder_at",
            "internal_remarks",
            "followup_status",
            "linked_appointment",
        ]
        extra_kwargs = {
            "followup_status": {"required": False},
            "reminder_status": {"required": False},
            "reminder_channel": {"required": False},
            "scheduled_reminder_at": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        # Hospital is derived from the patient.
        patient_id = attrs.get("patient")
        patient = Patient.objects.select_related("hospital").filter(pk=patient_id).first()
        if not patient:
            raise serializers.ValidationError({"patient": ["Patient not found."]})

        hospital_id = patient.hospital_id

        doctor_id = attrs.get("doctor")
        if doctor_id:
            doctor = DoctorProfile.objects.select_related("hospital").filter(pk=doctor_id).first()
            if not doctor:
                raise serializers.ValidationError({"doctor": ["Doctor not found."]})
            if doctor.hospital_id != hospital_id:
                raise serializers.ValidationError({"doctor": ["Doctor does not belong to this hospital."]})
            attrs["doctor"] = doctor

        assigned_user_id = attrs.get("assigned_to_receptionist")
        if assigned_user_id:
            User = get_user_model()
            assigned_user = User.objects.filter(pk=assigned_user_id).first()
            if not assigned_user:
                raise serializers.ValidationError({"assigned_to_receptionist": ["User not found."]})
            # If user is not superuser, ensure same hospital.
            if getattr(assigned_user, "hospital_id", None) and assigned_user.hospital_id != hospital_id:
                raise serializers.ValidationError({"assigned_to_receptionist": ["User not in this hospital."]})

        linked_appt_id = attrs.get("linked_appointment")
        if linked_appt_id:
            appt = Appointment.objects.select_related("hospital").filter(pk=linked_appt_id).first()
            if not appt:
                raise serializers.ValidationError({"linked_appointment": ["Appointment not found."]})
            if appt.hospital_id != hospital_id:
                raise serializers.ValidationError({"linked_appointment": ["Appointment not in this hospital."]})
            attrs["linked_appointment"] = appt

        attrs["patient"] = patient
        return attrs

