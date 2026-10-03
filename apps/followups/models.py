from django.conf import settings
from django.db import models

from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from apps.patients.models import Patient
from apps.shared.models import Hospital, SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel


class FollowUp(SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel):
    class ReminderChannel(models.TextChoices):
        IN_APP = "in_app"
        SMS = "sms"
        WHATSAPP = "whatsapp"
        EMAIL = "email"
        OTHER = "other"

    class ReminderStatus(models.TextChoices):
        NONE = "none"
        SCHEDULED = "scheduled"
        SENT = "sent"
        FAILED = "failed"

    class FollowUpStatus(models.TextChoices):
        PENDING = "pending"
        CALLED = "called"
        COMPLETED = "completed"
        MISSED = "missed"
        CANCELLED = "cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="followups")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="followups")
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.PROTECT, related_name="followups", null=True, blank=True
    )

    # Reception/user workflow.
    assigned_to_receptionist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_followups",
    )

    next_visit_date = models.DateField(db_index=True)
    advice = models.TextField(blank=True, default="")

    followup_status = models.CharField(
        max_length=20, choices=FollowUpStatus.choices, default=FollowUpStatus.PENDING, db_index=True
    )

    reminder_status = models.CharField(
        max_length=20, choices=ReminderStatus.choices, default=ReminderStatus.NONE, db_index=True
    )
    reminder_channel = models.CharField(max_length=30, choices=ReminderChannel.choices, default=ReminderChannel.IN_APP)
    scheduled_reminder_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True)

    call_remark = models.TextField(blank=True, default="")
    called_at = models.DateTimeField(null=True, blank=True)
    called_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="called_followups"
    )

    missed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    linked_appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="followups"
    )

    internal_remarks = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["hospital", "next_visit_date", "followup_status"])]

    def __str__(self) -> str:
        return f"{self.patient_id} next={self.next_visit_date} status={self.followup_status}"


class FollowUpStatusHistory(TimeStampedModel, UUIDPrimaryKeyModel):
    followup = models.ForeignKey(FollowUp, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="followup_status_changes")
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["followup", "to_status"])]

from django.db import models

# Create your models here.
