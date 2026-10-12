from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.shared.models import Hospital, SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel


class RentShop(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="rent_shops")
    shop_name = models.CharField(max_length=150, db_index=True)
    shop_number = models.CharField(max_length=50, blank=True, default="")
    owner_name = models.CharField(max_length=150, db_index=True)
    owner_phone = models.CharField(max_length=30, blank=True, default="")
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2)
    due_day = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(28)]
    )
    rent_start_date = models.DateField()
    security_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["shop_name", "shop_number"]
        indexes = [models.Index(fields=["hospital", "is_active", "shop_name"])]

    def __str__(self) -> str:
        suffix = f" ({self.shop_number})" if self.shop_number else ""
        return f"{self.shop_name}{suffix} - {self.owner_name}"


class RentReceiptSequence(TimeStampedModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="rent_receipt_sequences")
    year = models.PositiveIntegerField()
    last_seq = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("hospital", "year")]


class RentCollection(SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel):
    class PaymentMode(models.TextChoices):
        CASH = "cash"
        CARD = "card"
        UPI = "upi"
        BANK_TRANSFER = "bank_transfer"
        CHEQUE = "cheque"
        OTHER = "other"

    class Status(models.TextChoices):
        SUCCESS = "success"
        CANCELLED = "cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="rent_collections")
    shop = models.ForeignKey(RentShop, on_delete=models.PROTECT, related_name="collections")
    receipt_no = models.CharField(max_length=40, blank=True, default="", db_index=True)
    collected_at = models.DateTimeField(default=timezone.now, db_index=True)
    rent_month = models.DateField(db_index=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_mode = models.CharField(max_length=30, choices=PaymentMode.choices, default=PaymentMode.CASH)
    paid_by = models.CharField(max_length=150, blank=True, default="")
    reference_no = models.CharField(max_length=80, blank=True, default="")
    remarks = models.CharField(max_length=500, blank=True, default="")

    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rent_collections",
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
        related_name="voided_rent_collections",
    )

    class Meta:
        ordering = ["-collected_at", "-created_at"]
        indexes = [
            models.Index(fields=["hospital", "collected_at"]),
            models.Index(fields=["hospital", "shop", "rent_month"]),
        ]

    def _generate_receipt_no(self) -> str:
        year = (self.collected_at or timezone.now()).year
        with transaction.atomic():
            seq, _ = RentReceiptSequence.objects.select_for_update().get_or_create(
                hospital_id=self.hospital_id, year=year
            )
            seq.last_seq += 1
            seq.save(update_fields=["last_seq", "updated_at"])
            return f"RENT-{year}-{seq.last_seq:04d}"

    def save(self, *args, **kwargs):
        if self.rent_month:
            self.rent_month = self.rent_month.replace(day=1)
        if not self.receipt_no and self.hospital_id:
            self.receipt_no = self._generate_receipt_no()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.receipt_no} - {self.shop_id} ({self.amount})"
