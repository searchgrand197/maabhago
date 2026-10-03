from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.attendance.models import (
    AttendanceRegularization,
    LeaveApplication,
    MonthlyEarnedLeaveAllocation,
    StaffDailyAttendance,
    StaffLeaveBalance,
)
from apps.staff.models import StaffProfile


def get_staff_profile_for_user(user, hospital_id=None) -> StaffProfile | None:
    qs = StaffProfile.objects.filter(user_id=user.id, is_deleted=False, employment_status=StaffProfile.EmploymentStatus.ACTIVE)
    hid = hospital_id or getattr(user, "hospital_id", None)
    if hid:
        qs = qs.filter(hospital_id=hid)
    return qs.select_related("hospital", "designation").first()


def _calendar_days_inclusive(start: date, end: date) -> int:
    return (end - start).days + 1


def compute_leave_total_days(
    start: date,
    end: date,
    *,
    is_half_day: bool,
) -> Decimal:
    if is_half_day:
        if start != end:
            raise ValueError("Half-day leave must use the same start and end date.")
        return Decimal("0.5")
    return Decimal(str(_calendar_days_inclusive(start, end)))


@transaction.atomic
def punch_check_in(*, staff: StaffProfile, attendance_date: date | None = None, notes: str = "") -> StaffDailyAttendance:
    adate = attendance_date or timezone.localdate()
    if staff.hospital_id is None:
        raise ValueError("Staff has no hospital.")
    row, created = StaffDailyAttendance.objects.select_for_update().get_or_create(
        hospital_id=staff.hospital_id,
        staff=staff,
        attendance_date=adate,
        defaults={
            "check_in_at": timezone.now(),
            "status": StaffDailyAttendance.Status.INCOMPLETE,
            "notes": notes,
        },
    )
    if not created:
        if row.check_in_at and row.status != StaffDailyAttendance.Status.PENDING_REGULARIZATION:
            raise ValueError("Already checked in for this date.")
        row.check_in_at = timezone.now()
        if notes:
            row.notes = (row.notes + "\n" + notes).strip()
        row.status = StaffDailyAttendance.Status.INCOMPLETE
        row.save(update_fields=["check_in_at", "notes", "status", "updated_at"])
    return row


@transaction.atomic
def punch_check_out(*, staff: StaffProfile, attendance_date: date | None = None, notes: str = "") -> StaffDailyAttendance:
    adate = attendance_date or timezone.localdate()
    row = (
        StaffDailyAttendance.objects.select_for_update()
        .filter(hospital_id=staff.hospital_id, staff=staff, attendance_date=adate)
        .first()
    )
    if not row:
        raise ValueError("No check-in found for this date. Check in first or use regularization.")
    if not row.check_in_at:
        raise ValueError("Cannot check out without check-in time.")
    if row.check_out_at:
        raise ValueError("Already checked out for this date.")
    row.check_out_at = timezone.now()
    if notes:
        row.notes = (row.notes + "\n" + notes).strip()
    row.status = StaffDailyAttendance.Status.PRESENT
    row.save(update_fields=["check_out_at", "notes", "status", "updated_at"])
    return row


@transaction.atomic
def approve_regularization(
    *,
    req: AttendanceRegularization,
    reviewer,
    approve: bool,
    review_notes: str = "",
) -> StaffDailyAttendance:
    if req.status != AttendanceRegularization.Status.PENDING:
        raise ValueError("Request is not pending.")
    req.reviewed_by = reviewer
    req.reviewed_at = timezone.now()
    req.review_notes = review_notes
    req.status = AttendanceRegularization.Status.APPROVED if approve else AttendanceRegularization.Status.REJECTED
    req.save()

    if not approve:
        return None  # type: ignore[return-value]

    row, _ = StaffDailyAttendance.objects.select_for_update().get_or_create(
        hospital_id=req.hospital_id,
        staff_id=req.staff_id,
        attendance_date=req.attendance_date,
        defaults={"status": StaffDailyAttendance.Status.PRESENT},
    )
    if req.requested_check_in_at:
        row.check_in_at = req.requested_check_in_at
    if req.requested_check_out_at:
        row.check_out_at = req.requested_check_out_at
    row.status = StaffDailyAttendance.Status.PRESENT
    row.notes = (row.notes + f"\n[Regularization approved] {review_notes}").strip()
    row.save()
    return row


def _deduct_leave_balance(application: LeaveApplication, allow_negative: bool) -> None:
    """
    Deduct `application.total_days` from the staff's leave balance for the
    given leave type.  Creates a zero-balance record if one doesn't exist yet.
    Raises ValueError when balance would go negative and allow_negative=False.
    """
    # Unpaid leave has no balance to track — nothing to deduct.
    if application.leave_type == LeaveApplication.LeaveType.UNPAID:
        return

    bal, _ = StaffLeaveBalance.objects.select_for_update().get_or_create(
        staff_id=application.staff_id,
        leave_type=application.leave_type,
        defaults={"balance_days": Decimal("0")},
    )
    if not allow_negative and bal.balance_days < application.total_days:
        raise ValueError(
            f"Insufficient {application.leave_type} leave balance "
            f"({bal.balance_days} days available, {application.total_days} days requested)."
        )
    StaffLeaveBalance.objects.filter(pk=bal.pk).update(
        balance_days=F("balance_days") - application.total_days
    )


def _restore_leave_balance(application: LeaveApplication) -> None:
    """
    Restore `application.total_days` back to the staff's leave balance
    (used when an approved leave is cancelled or reversed).
    """
    if application.leave_type == LeaveApplication.LeaveType.UNPAID:
        return

    bal = StaffLeaveBalance.objects.select_for_update().filter(
        staff_id=application.staff_id,
        leave_type=application.leave_type,
    ).first()
    if bal:
        StaffLeaveBalance.objects.filter(pk=bal.pk).update(
            balance_days=F("balance_days") + application.total_days
        )


def _check_leave_approver(application: LeaveApplication, approver) -> None:
    """
    If the hospital has any active LeaveApprover records configured, the
    approving user must be one of them.  If no approvers are configured,
    fall back to allowing any user with the appropriate DRF permission
    (existing behaviour).
    """
    from apps.settings_management.models import LeaveApprover

    configured = LeaveApprover.objects.filter(
        hospital_id=application.hospital_id,
        is_active=True,
    ).exists()

    if not configured:
        # No approver list configured yet – allow the action (backward-compatible).
        return

    is_allowed = LeaveApprover.objects.filter(
        hospital_id=application.hospital_id,
        user_id=approver.id,
        is_active=True,
    ).exists()

    if not is_allowed:
        raise ValueError(
            f"{approver.email} is not listed as an authorised leave approver "
            "for this hospital. Please contact the administrator."
        )


@transaction.atomic
def approve_leave_application(
    *,
    application: LeaveApplication,
    approver,
    approve: bool,
    rejection_notes: str = "",
    allow_negative_balance: bool = False,
) -> None:
    if application.status != LeaveApplication.Status.PENDING:
        raise ValueError("Leave is not pending.")

    # Validate approver against hospital-configured approver list.
    _check_leave_approver(application, approver)

    if approve:
        # Deduct balance first — raises ValueError if insufficient.
        _deduct_leave_balance(application, allow_negative=allow_negative_balance)
        application.approved_by = approver
        application.approved_at = timezone.now()
        application.status = LeaveApplication.Status.APPROVED
        application.rejection_notes = ""
    else:
        application.status = LeaveApplication.Status.REJECTED
        application.rejection_notes = rejection_notes
        application.approved_by = approver
        application.approved_at = timezone.now()

    application.save()


@transaction.atomic
def cancel_leave_application(*, application: LeaveApplication, cancelled_by_staff: bool = True) -> None:
    """
    Cancel a leave application.
    - If it was already APPROVED, restore the balance.
    - Only PENDING or APPROVED leaves can be cancelled.
    """
    if application.status not in (LeaveApplication.Status.PENDING, LeaveApplication.Status.APPROVED):
        raise ValueError("Only pending or approved leave applications can be cancelled.")

    was_approved = application.status == LeaveApplication.Status.APPROVED

    application.status = LeaveApplication.Status.CANCELLED
    note = "Cancelled by staff." if cancelled_by_staff else "Cancelled by admin."
    application.rejection_notes = (application.rejection_notes + f"\n{note}").strip()
    application.save(update_fields=["status", "rejection_notes", "updated_at"])

    # Restore balance only if the leave had already been approved (i.e., balance was deducted).
    if was_approved:
        _restore_leave_balance(application)


@transaction.atomic
def apply_monthly_earned_allocation(*, allocation: MonthlyEarnedLeaveAllocation) -> int:
    if allocation.is_applied:
        raise ValueError("This allocation was already applied.")
    if allocation.designation.hospital_id != allocation.hospital_id:
        raise ValueError("Designation hospital does not match allocation hospital.")

    staff_ids = list(
        StaffProfile.objects.filter(
            hospital_id=allocation.hospital_id,
            designation_id=allocation.designation_id,
            is_deleted=False,
            employment_status=StaffProfile.EmploymentStatus.ACTIVE,
        ).values_list("id", flat=True)
    )
    days = allocation.earned_days
    for sid in staff_ids:
        bal, _ = StaffLeaveBalance.objects.select_for_update().get_or_create(
            staff_id=sid,
            leave_type=LeaveApplication.LeaveType.EARNED,
            defaults={"balance_days": Decimal("0")},
        )
        StaffLeaveBalance.objects.filter(pk=bal.pk).update(balance_days=F("balance_days") + days)

    allocation.is_applied = True
    allocation.applied_at = timezone.now()
    allocation.save(update_fields=["is_applied", "applied_at", "updated_at"])
    return len(staff_ids)


@transaction.atomic
def auto_allocate_earned_leave_for_month(*, year: int, month: int, days_per_staff: Decimal | None = None) -> int:
    """
    Simple rule: credit a fixed number of earned leave days (default: 2.0)
    to every active staff for the given year+month.

    This bypasses designation-specific rules and ensures each staff gets the
    same monthly earned leave.
    """
    from apps.staff.models import StaffProfile

    if days_per_staff is None:
        days_per_staff = Decimal("2.0")

    # For each active staff, increment their earned leave balance by N days.
    staff_ids = list(
        StaffProfile.objects.filter(
            is_deleted=False,
            employment_status=StaffProfile.EmploymentStatus.ACTIVE,
        ).values_list("id", flat=True)
    )

    if not staff_ids:
        return 0

    credited = 0
    for sid in staff_ids:
        bal, _ = StaffLeaveBalance.objects.select_for_update().get_or_create(
            staff_id=sid,
            leave_type=LeaveApplication.LeaveType.EARNED,
            defaults={"balance_days": Decimal("0")},
        )
        StaffLeaveBalance.objects.filter(pk=bal.pk).update(balance_days=F("balance_days") + days_per_staff)
        credited += 1

    return credited


@transaction.atomic
def auto_mark_unmarked_as_pending_regularization(*, target_date: date | None = None) -> int:
    """
    For the given calendar day (default: yesterday):

    1. Staff with NO attendance row at all → create a PENDING_REGULARIZATION row.
    2. Staff with an INCOMPLETE row that has no check_in_at and no check_out_at
       → update that row to PENDING_REGULARIZATION.

    Staff who are PRESENT, ABSENT, ON_LEAVE, HALF_DAY, or already
    PENDING_REGULARIZATION are left untouched.

    Returns the total number of staff records created or updated.
    """
    from collections import defaultdict

    if target_date is None:
        # "Next day" behaviour: when this runs today, process yesterday's date.
        target_date = timezone.localdate() - timedelta(days=1)

    # Active staff with a hospital assigned.
    staff_qs = StaffProfile.objects.filter(
        is_deleted=False,
        employment_status=StaffProfile.EmploymentStatus.ACTIVE,
        hospital_id__isnull=False,
    ).values_list("id", "hospital_id")

    staff_by_hospital: dict[str, list[str]] = defaultdict(list)
    for sid, hid in staff_qs:
        staff_by_hospital[str(hid)].append(str(sid))

    if not staff_by_hospital:
        return 0

    # Load existing rows for that day keyed by (hospital_id, staff_id).
    existing_rows: dict[tuple, StaffDailyAttendance] = {
        (str(row.hospital_id), str(row.staff_id)): row
        for row in StaffDailyAttendance.objects.select_for_update().filter(
            attendance_date=target_date,
            hospital_id__in=staff_by_hospital.keys(),
        )
    }

    auto_note = "Auto-marked as pending regularization due to no attendance recorded."

    to_create: list[StaffDailyAttendance] = []
    updated_count = 0

    for hid, staff_ids in staff_by_hospital.items():
        for sid in staff_ids:
            key = (hid, sid)
            row = existing_rows.get(key)

            if row is None:
                # No attendance row at all → create one.
                to_create.append(
                    StaffDailyAttendance(
                        hospital_id=hid,
                        staff_id=sid,
                        attendance_date=target_date,
                        status=StaffDailyAttendance.Status.PENDING_REGULARIZATION,
                        notes=auto_note,
                    )
                )
            elif (
                row.status == StaffDailyAttendance.Status.INCOMPLETE
                and row.check_in_at is None
                and row.check_out_at is None
            ):
                # INCOMPLETE with no times → flip to PENDING_REGULARIZATION.
                row.status = StaffDailyAttendance.Status.PENDING_REGULARIZATION
                row.notes = (row.notes + "\n" + auto_note).strip()
                row.save(update_fields=["status", "notes", "updated_at"])
                updated_count += 1
            # Any other status (PRESENT, ABSENT, ON_LEAVE, HALF_DAY, already
            # PENDING_REGULARIZATION) is left untouched.

    if to_create:
        StaffDailyAttendance.objects.bulk_create(to_create)

    return updated_count + len(to_create)

