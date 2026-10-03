from django.conf import settings
from django.db import models

from apps.doctors.models import DoctorProfile
from apps.patients.models import Patient
from apps.shared.models import Hospital, SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel


class Appointment(SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel):
    class ConsultationType(models.TextChoices):
        NEW = "new"
        FOLLOWUP = "followup"
        WALK_IN = "walk_in"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled"
        WAITING = "waiting"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="appointments")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.PROTECT, related_name="appointments")

    booked_at = models.DateTimeField()
    appointment_datetime = models.DateTimeField(db_index=True)

    consultation_type = models.CharField(max_length=30, choices=ConsultationType.choices, default=ConsultationType.NEW)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    queue_order = models.PositiveIntegerField(default=0, db_index=True)

    receptionist_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="booked_appointments",
    )

    symptoms = models.TextField(blank=True, default="")
    reason_for_visit = models.TextField(blank=True, default="")
    internal_remarks = models.TextField(blank=True, default="")

    rescheduled_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reschedules"
    )

    class Meta:
        indexes = [
            models.Index(fields=["hospital", "appointment_datetime"]),
            models.Index(fields=["hospital", "doctor", "appointment_datetime"]),
            models.Index(fields=["hospital", "patient", "appointment_datetime"]),
        ]

    def __str__(self) -> str:
        return f"Appt {self.patient_id} {self.appointment_datetime}"


class AppointmentStatusHistory(TimeStampedModel, UUIDPrimaryKeyModel):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["appointment", "to_status"])]

