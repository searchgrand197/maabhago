from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.staff.models import StaffShiftAssignment


@transaction.atomic
def auto_cancel_expired_shift_assignments(*, today: date | None = None) -> int:
    """
    Mark shift assignments as CANCELLED once their end_date has passed.

    - If end_date is set and < today, and status is not already CANCELLED,
      flip status to CANCELLED.
    """
    if today is None:
        today = timezone.localdate()

    qs = StaffShiftAssignment.objects.select_for_update().filter(
        end_date__lt=today,
    ).exclude(status=StaffShiftAssignment.AssignmentStatus.CANCELLED)

    updated = qs.update(status=StaffShiftAssignment.AssignmentStatus.CANCELLED)
    return updated

