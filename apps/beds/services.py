from __future__ import annotations

from datetime import date as date_cls

from django.db.models import Q
from django.utils import timezone

from apps.beds.models import Bed, BedCleaningTask
from apps.staff.models import StaffAvailabilityOverride, StaffProfile, StaffShiftAssignment

HOUSEKEEPING_KEYWORDS = (
    "housekeeping",
    "cleaning",
    "cleaner",
    "janitor",
    "sanitation",
    "ward boy",
    "attendant",
)


def get_on_duty_housekeeping_staff(hospital_id, for_date: date_cls | None = None):
    target_date = for_date or timezone.localdate()
    role_filter = Q()
    for kw in HOUSEKEEPING_KEYWORDS:
        role_filter |= Q(department__name__icontains=kw) | Q(designation__name__icontains=kw)

    base = StaffProfile.objects.filter(
        hospital_id=hospital_id,
        employment_status=StaffProfile.EmploymentStatus.ACTIVE,
    ).filter(role_filter)

    on_shift_ids = StaffShiftAssignment.objects.filter(
        hospital_id=hospital_id,
        status__in=[
            StaffShiftAssignment.AssignmentStatus.ASSIGNED,
            StaffShiftAssignment.AssignmentStatus.REASSIGNED,
        ],
        date__lte=target_date,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=target_date)).values_list("staff_id", flat=True)

    available_false_ids = StaffAvailabilityOverride.objects.filter(
        hospital_id=hospital_id,
        date=target_date,
        is_available=False,
    ).values_list("staff_id", flat=True)

    return base.filter(id__in=on_shift_ids).exclude(id__in=available_false_ids).distinct()


def pick_housekeeping_staff(hospital_id):
    candidates = list(get_on_duty_housekeeping_staff(hospital_id))
    if not candidates:
        return None

    workloads = {
        c.id: BedCleaningTask.objects.filter(
            hospital_id=hospital_id,
            assigned_staff_id=c.id,
            status__in=[BedCleaningTask.Status.PENDING, BedCleaningTask.Status.IN_PROGRESS],
        ).count()
        for c in candidates
    }
    candidates.sort(key=lambda c: (workloads.get(c.id, 0), c.created_at))
    return candidates[0]


def ensure_cleaning_task_for_bed(*, bed_code: str, hospital_id, assigned_staff=None, notes: str = ""):
    if not bed_code:
        return None
    bed = Bed.objects.filter(bed_code=bed_code, hospital_id=hospital_id).first()
    if not bed:
        return None

    open_task = BedCleaningTask.objects.filter(
        hospital_id=hospital_id,
        bed=bed,
        status__in=[BedCleaningTask.Status.PENDING, BedCleaningTask.Status.IN_PROGRESS],
    ).order_by("-created_at").first()

    if open_task:
        if assigned_staff and open_task.assigned_staff_id != assigned_staff.id:
            open_task.assigned_staff = assigned_staff
        if notes:
            open_task.notes = notes
        open_task.save(update_fields=["assigned_staff", "notes", "updated_at"])
        return open_task

    chosen_staff = assigned_staff or pick_housekeeping_staff(hospital_id)
    return BedCleaningTask.objects.create(
        hospital_id=hospital_id,
        bed=bed,
        assigned_staff=chosen_staff,
        status=BedCleaningTask.Status.PENDING,
        notes=notes,
    )
