from django.conf import settings
from django.db import models

from apps.doctors.models import DoctorProfile
from apps.patients.models import Patient
from apps.shared.models import Hospital, SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel


class DailyTokenCounter(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="token_counters")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.PROTECT, related_name="token_counters")
    date = models.DateField(db_index=True)
    current_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("hospital", "doctor", "date")]
        indexes = [models.Index(fields=["hospital", "date", "doctor"])]

    def __str__(self) -> str:
        return f"{self.doctor_id} {self.date}"


class Token(SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel):
    class Status(models.TextChoices):
        WAITING = "waiting"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        SKIPPED = "skipped"
        CANCELLED = "cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="tokens")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.PROTECT, related_name="tokens")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="tokens")
    date = models.DateField(db_index=True)
    token_number = models.PositiveIntegerField(db_index=True)
    queue_order = models.PositiveIntegerField(default=0, db_index=True)
    appointment = models.ForeignKey(
        "appointments.Appointment", null=True, blank=True, on_delete=models.SET_NULL, related_name="tokens"
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_tokens",
    )

    called_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="called_tokens",
    )
    called_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("hospital", "doctor", "date", "token_number")]
        indexes = [
            models.Index(fields=["hospital", "doctor", "date", "status"]),
            models.Index(fields=["hospital", "patient", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.date} - {self.doctor_id} - {self.token_number}"


class TokenStatusHistory(TimeStampedModel, UUIDPrimaryKeyModel):
    token = models.ForeignKey(Token, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["token", "to_status"])]

