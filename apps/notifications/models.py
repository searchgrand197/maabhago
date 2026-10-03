from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.shared.models import Hospital, TimeStampedModel, UUIDPrimaryKeyModel


class Notification(TimeStampedModel, UUIDPrimaryKeyModel):
    class NType(models.TextChoices):
        TREATMENT_ASSIGNED = "treatment_assigned", "Treatment Assigned"
        TREATMENT_UPDATED = "treatment_updated", "Treatment Updated"
        PACKAGE_ASSIGNED = "package_assigned", "Package Assigned"
        TASK_OVERDUE = "task_overdue", "Task Overdue"
        GENERAL = "general", "General"

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="notifications")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=30, choices=NType.choices, default=NType.GENERAL, db_index=True)
    title = models.CharField(max_length=300)
    message = models.TextField(blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    reference_type = models.CharField(max_length=50, blank=True, default="")
    reference_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["hospital", "notification_type"]),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])


class WebPushSubscription(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="webpush_subscriptions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webpush_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    p256dh_key = models.CharField(max_length=255)
    auth_key = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["hospital", "is_active"]),
        ]

    def __str__(self):
        return f"WebPushSubscription<{self.user_id}>"
