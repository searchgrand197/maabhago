"""
Normalize mobile numbers and link patients who share the same contact phone into a PatientFamilyGroup.
"""

from __future__ import annotations

import re
from uuid import UUID

from django.db import transaction
from django.utils.crypto import get_random_string

from apps.patients.models import Patient, PatientFamilyGroup


def normalize_phone_digits(phone: str | None) -> str:
    """Digits only; for long Indian numbers keep the last 10 digits as the canonical key."""
    d = re.sub(r"\D", "", phone or "")
    if len(d) > 10:
        return d[-10:]
    return d


def patients_with_same_phone(*, hospital_id: UUID, phone: str, include_guardian_phone: bool = True):
    """
    Return all non-deleted patients in the hospital whose stored phone (and optionally guardian phone)
    matches the same normalized 10-digit key.
    """
    key = normalize_phone_digits(phone)
    if len(key) < 10:
        return []

    from apps.patients.models import PatientGuardian

    out: list[Patient] = []
    seen: set[UUID] = set()

    qs = (
        Patient.objects.filter(hospital_id=hospital_id, is_deleted=False)
        .exclude(phone="")
        .select_related("family_group")
        .filter(phone__icontains=key)
    )
    for p in qs:
        if normalize_phone_digits(p.phone) == key and p.id not in seen:
            out.append(p)
            seen.add(p.id)

    if include_guardian_phone:
        for g in (
            PatientGuardian.objects.filter(
                patient__hospital_id=hospital_id,
                patient__is_deleted=False,
            )
            .select_related("patient", "patient__family_group")
            .filter(phone__icontains=key)
        ):
            if normalize_phone_digits(g.phone) != key:
                continue
            p = g.patient
            if p.id not in seen:
                out.append(p)
                seen.add(p.id)

    out.sort(key=lambda p: ((p.last_name or "").lower(), (p.first_name or "").lower(), p.uhid or ""))
    return out


@transaction.atomic
def ensure_family_group_for_shared_phone(patient: Patient) -> PatientFamilyGroup | None:
    """
    If at least one other patient shares this phone (or guardian phone), assign everyone in that set
    to the same PatientFamilyGroup (reuse an existing group from any member if present).
    """
    hospital = patient.hospital
    key = normalize_phone_digits(patient.phone)
    if len(key) < 10:
        return None

    same = patients_with_same_phone(hospital_id=hospital.id, phone=patient.phone, include_guardian_phone=True)
    # Include the anchor patient if not already (e.g. new row with phone set)
    ids = {p.id for p in same}
    if patient.id not in ids:
        same = list(same) + [patient]

    if len(same) < 2:
        return None

    group: PatientFamilyGroup | None = None
    for p in same:
        if p.family_group_id:
            group = p.family_group
            break

    if group is None:
        base_code = f"PH-{key}"
        code = base_code[:64]
        while PatientFamilyGroup.objects.filter(code=code).exists():
            code = f"PH-{key}-{get_random_string(4)}"[:64]
        group = PatientFamilyGroup.objects.create(
            hospital=hospital,
            name=f"Family · {key}",
            code=code,
        )

    pids = [p.id for p in same]
    Patient.objects.filter(id__in=pids).update(family_group=group)
    return group
