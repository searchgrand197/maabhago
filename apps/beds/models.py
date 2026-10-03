from django.conf import settings
from django.db import models
from apps.shared.models import Hospital, TimeStampedModel, UUIDPrimaryKeyModel


class Floor(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="floors")
    floor_number = models.IntegerField(db_index=True)   # 0 = Ground, 1 = First, -1 = Basement
    name = models.CharField(max_length=100)              # "Ground Floor", "1st Floor", "ICU Block"
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("hospital", "floor_number")]
        ordering = ["floor_number"]

    def __str__(self):
        return f"{self.name} (Floor {self.floor_number})"


class BedRoom(TimeStampedModel, UUIDPrimaryKeyModel):
    class RoomType(models.TextChoices):
        WARD = "ward", "Ward"
        PERSONAL = "personal", "Personal Room"
        SHARED = "shared", "Shared Room"
        ICU = "icu", "ICU"
        EMERGENCY = "emergency", "Emergency"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="bed_rooms")
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, related_name="rooms")
    name = models.CharField(max_length=200)              # "Ward A", "VIP Room 1"
    room_number = models.CharField(max_length=50, blank=True, default="")  # "101", "A-12"
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.WARD)
    is_ac = models.BooleanField(default=False)
    daily_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_beds = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["floor", "room_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()}) – Floor {self.floor.floor_number}"

    @property
    def available_bed_count(self):
        return self.beds.filter(status=Bed.Status.AVAILABLE).count()

    @property
    def total_bed_count(self):
        return self.beds.count()


class Bed(TimeStampedModel, UUIDPrimaryKeyModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        RESERVED = "reserved", "Reserved"
        MAINTENANCE = "maintenance", "Under Maintenance"
        CLEANING = "cleaning", "Being Cleaned"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="beds")
    room = models.ForeignKey(BedRoom, on_delete=models.PROTECT, related_name="beds")
    bed_code = models.CharField(max_length=50)           # "B-101", "W-A-3"
    bed_number = models.CharField(max_length=20)         # "1", "2", "A"
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("hospital", "bed_code")]
        ordering = ["room", "bed_number"]

    def __str__(self):
        return f"{self.bed_code} ({self.get_status_display()}) – {self.room.name}"


class BedCleaningTask(TimeStampedModel, UUIDPrimaryKeyModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="bed_cleaning_tasks")
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name="cleaning_tasks")
    assigned_staff = models.ForeignKey(
        "staff.StaffProfile",
        on_delete=models.PROTECT,
        related_name="bed_cleaning_tasks",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    notes = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="completed_bed_cleaning_tasks",
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["hospital", "status", "created_at"]),
            models.Index(fields=["bed", "status"]),
        ]

    def __str__(self):
        return f"Cleaning {self.bed.bed_code} ({self.status})"
