from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.shared.models import Hospital, TimeStampedModel, UUIDPrimaryKeyModel
from apps.staff.models import Designation, StaffProfile


class StaffDailyAttendance(TimeStampedModel, UUIDPrimaryKeyModel):
    """One row per staff per calendar day (punch + finalised times)."""

    class Status(models.TextChoices):
        INCOMPLETE = "incomplete", "Incomplete"
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        HALF_DAY = "half_day", "Half day"
        ON_LEAVE = "on_leave", "On leave"
        PENDING_REGULARIZATION = "pending_regularization", "Pending regularization"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="daily_attendance")
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="daily_attendance")
    attendance_date = models.DateField(db_index=True)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.INCOMPLETE, db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "staff", "attendance_date"],
                name="attendance_unique_staff_date_hospital",
            ),
        ]
        indexes = [
            models.Index(fields=["hospital", "attendance_date"]),
            models.Index(fields=["staff", "attendance_date"]),
        ]
        ordering = ["-attendance_date", "staff_id"]

    def __str__(self) -> str:
        return f"{self.staff_id} {self.attendance_date}"


class AttendanceRegularization(TimeStampedModel, UUIDPrimaryKeyModel):
    """Staff request to fix missed/wrong punch for a past (or today) day — needs approval."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="attendance_regularizations")
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="attendance_regularizations")
    attendance_date = models.DateField(db_index=True)
    requested_check_in_at = models.DateTimeField(null=True, blank=True)
    requested_check_out_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="regularizations_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["staff", "attendance_date"]),
        ]

    def __str__(self) -> str:
        return f"Reg {self.staff_id} {self.attendance_date} {self.status}"


class LeaveApplication(TimeStampedModel, UUIDPrimaryKeyModel):
    class LeaveType(models.TextChoices):
        EARNED = "earned", "Earned leave"
        SICK = "sick", "Sick leave"
        CASUAL = "casual", "Casual leave"
        UNPAID = "unpaid", "Unpaid leave"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="leave_applications")
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="leave_applications")
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    first_half = models.BooleanField(default=True)  # True = morning / first half
    reason = models.TextField(blank=True, default="")
    total_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_approvals",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["staff", "start_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"Leave {self.staff_id} {self.start_date}–{self.end_date}"


class MonthlyEarnedLeaveAllocation(TimeStampedModel, UUIDPrimaryKeyModel):
    """
    Admin rule: e.g. April + Receptionist designation = 2 earned days credited (after apply).
    Unique per hospital + year + month + designation.
    """

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="earned_leave_allocations")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()  # 1–12
    designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name="earned_leave_allocations")
    earned_days = models.DecimalField(max_digits=5, decimal_places=2)
    is_applied = models.BooleanField(default=False, db_index=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "year", "month", "designation"],
                name="attendance_unique_monthly_earned_allocation",
            ),
        ]
        ordering = ["-year", "-month", "designation__name"]

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d} {self.designation.code} +{self.earned_days}"


class StaffLeaveBalance(TimeStampedModel, UUIDPrimaryKeyModel):
    """Per staff, per leave type balance (updated on accrual apply + earned leave approval)."""

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.CharField(max_length=20, choices=LeaveApplication.LeaveType.choices, db_index=True)
    balance_days = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["staff", "leave_type"], name="attendance_unique_staff_leave_balance"),
        ]

    def __str__(self) -> str:
        return f"{self.staff_id} {self.leave_type}: {self.balance_days}"

