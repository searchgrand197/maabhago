import re
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.shared.models import Hospital, SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel


def normalize_vehicle_number(value) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


class AmbulanceVehicle(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="ambulance_vehicles")
    vehicle_number = models.CharField(max_length=30, db_index=True)
    label = models.CharField(max_length=100, blank=True, default="")
    driver_name = models.CharField(max_length=120, blank=True, default="")
    driver_phone = models.CharField(max_length=30, blank=True, default="")
    expected_daily_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["vehicle_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "vehicle_number"],
                name="ambulance_vehicle_unique_hospital_number",
            ),
        ]

    def save(self, *args, **kwargs):
        self.vehicle_number = normalize_vehicle_number(self.vehicle_number)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.vehicle_number


class AmbulanceReceiptSequence(TimeStampedModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="ambulance_receipt_sequences")
    year = models.PositiveIntegerField()
    last_seq = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("hospital", "year")]


class AmbulanceCollection(SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel):
    class PaymentMode(models.TextChoices):
        CASH = "cash"
        CARD = "card"
        UPI = "upi"
        BANK_TRANSFER = "bank_transfer"
        OTHER = "other"

    class Status(models.TextChoices):
        SUCCESS = "success"
        CANCELLED = "cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="ambulance_collections")
    vehicle = models.ForeignKey(AmbulanceVehicle, on_delete=models.PROTECT, related_name="collections")
    receipt_no = models.CharField(max_length=40, blank=True, default="", db_index=True)
    collected_at = models.DateTimeField(default=timezone.now, db_index=True)

    driver_name = models.CharField(max_length=120, blank=True, default="")
    driver_phone = models.CharField(max_length=30, blank=True, default="")
    trip_count = models.PositiveIntegerField(default=1)
    patient_name = models.CharField(max_length=200, blank=True, default="")
    trip_from = models.CharField(max_length=200, blank=True, default="")
    trip_to = models.CharField(max_length=200, blank=True, default="")
    distance_km = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_mode = models.CharField(max_length=30, choices=PaymentMode.choices, default=PaymentMode.CASH)
    remarks = models.CharField(max_length=500, blank=True, default="")

    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ambulance_collections",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True)
    voided = models.BooleanField(default=False, db_index=True)
    void_reason = models.CharField(max_length=500, blank=True, default="")
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voided_ambulance_collections",
    )

    class Meta:
        ordering = ["-collected_at", "-created_at"]
        indexes = [
            models.Index(fields=["hospital", "collected_at"]),
            models.Index(fields=["hospital", "vehicle", "collected_at"]),
        ]

    def _generate_receipt_no(self) -> str:
        year = (self.collected_at or timezone.now()).year
        with transaction.atomic():
            seq, _ = AmbulanceReceiptSequence.objects.select_for_update().get_or_create(
                hospital_id=self.hospital_id, year=year
            )
            seq.last_seq += 1
            seq.save(update_fields=["last_seq", "updated_at"])
            return f"AMB-{year}-{seq.last_seq:04d}"

    def save(self, *args, **kwargs):
        if not self.receipt_no and self.hospital_id:
            self.receipt_no = self._generate_receipt_no()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.receipt_no} - {self.vehicle_id} ({self.amount})"
