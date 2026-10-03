"""
Run:  python manage.py shell < scripts/seed_dummy_data.py
Creates sample data: patients, OPD visits (with tokens), IPD admission, treatment plan.
"""
from datetime import date, time
from django.utils import timezone

# ── Patients ──────────────────────────────────────────────────────────────────
from apps.patients.models import Patient
from apps.shared.models import Hospital

hospital = Hospital.objects.first()
if not hospital:
    print("❌ No hospital found. Please create one first.")
    raise SystemExit

print(f"Using hospital: {hospital.name}")

patient_data = [
    dict(first_name="Ravi",   last_name="Sharma",  gender="male",   dob=date(1985, 3, 10), phone="9876543210"),
    dict(first_name="Priya",  last_name="Mehta",   gender="female", dob=date(1990, 7, 22), phone="9876543211"),
    dict(first_name="Arjun",  last_name="Patel",   gender="male",   dob=date(1978, 11, 5), phone="9876543212"),
    dict(first_name="Sunita", last_name="Verma",   gender="female", dob=date(1995, 1, 14), phone="9876543213"),
    dict(first_name="Mohan",  last_name="Das",     gender="male",   dob=date(1965, 6, 30), phone="9876543214"),
    dict(first_name="Kavita", last_name="Joshi",   gender="female", dob=date(2000, 9, 17), phone="9876543215"),
]

patients = []
for pd in patient_data:
    full_name = f"{pd['first_name']} {pd['last_name']}"
    p, created = Patient.objects.get_or_create(
        phone=pd["phone"],
        defaults={
            "hospital": hospital,
            "first_name": pd["first_name"],
            "last_name": pd["last_name"],
            "gender": pd["gender"],
            "date_of_birth": pd["dob"],
        }
    )
    patients.append(p)
    print(f"  {'Created' if created else 'Exists'}: Patient {full_name} (UHID: {p.uhid})")

# ── OPD Visits with tokens ────────────────────────────────────────────────────
from apps.accounts.models import User
from apps.opd.models import OPDVisit

today = date.today()
doctor_user = User.objects.filter(is_superuser=True).first()

complaints = ["Fever & cold", "Headache", "Back pain", "Stomach ache", "Cough", "BP checkup"]
room_codes = ["room1", "room2", "room1", "room3", "room2", "room1"]
statuses = ["waiting", "waiting", "in_consultation", "waiting", "completed", "waiting"]

for i, (patient, complaint, room, status) in enumerate(zip(patients, complaints, room_codes, statuses)):
    token = i + 1
    visit, created = OPDVisit.objects.get_or_create(
        patient=patient,
        visit_date=today,
        defaults={
            "hospital": hospital,
            "assigned_doctor": doctor_user,
            "chief_complaint": complaint,
            "token_number": token,
            "status": status,
            "room_code": room,
        }
    )
    print(f"  {'Created' if created else 'Exists'}: OPD Token #{token} – {patient.first_name} [{room}] ({status})")

# ── IPD Admission ─────────────────────────────────────────────────────────────
from apps.ipd.models import IPDAdmission

ipd_patient = patients[2]  # Arjun Patel
admission, created = IPDAdmission.objects.get_or_create(
    patient=ipd_patient,
    admission_date=today,
    defaults={
        "hospital": hospital,
        "assigned_doctor": doctor_user,
        "ward_name": "Ward A",
        "room_name": "Room 101",
        "bed_code": "101-A",
        "admission_diagnosis": "Typhoid fever",
        "status": "admitted",
    }
)
print(f"\n  {'Created' if created else 'Exists'}: IPD Admission for {ipd_patient.first_name} – Bed {admission.bed_code}")

# ── Treatment Plan ────────────────────────────────────────────────────────────
from apps.treatment.models import TreatmentPlan, TreatmentPlanItem
from apps.treatment.services import generate_tasks_for_plan

plan, created = TreatmentPlan.objects.get_or_create(
    ipd_admission=admission,
    name="Typhoid – Day 0–3 Protocol",
    defaults={
        "hospital": hospital,
        "created_by": doctor_user,
        "start_date": today,
        "end_date": today,
        "status": "active",
    }
)
print(f"  {'Created' if created else 'Exists'}: Treatment Plan '{plan.name}'")

if created:
    orders = [
        dict(title="Give Glucose", instructions="500ml IV over 2h", category="medication", day_offset=0, time_of_day=time(8, 0), sequence=1),
        dict(title="Give Antibiotic (Ceftriaxone 1g)", instructions="IV stat once", category="medication", day_offset=0, time_of_day=time(8, 0), sequence=2),
        dict(title="Give Amoxicillin 500mg", instructions="PO after food", category="medication", day_offset=0, time_of_day=time(8, 30), sequence=3),
        dict(title="Give Painkiller (Paracetamol 1g)", instructions="IV if temp > 38°C", category="medication", day_offset=0, time_of_day=time(8, 0), sequence=4),
        dict(title="Check Vitals", instructions="BP, temp, SpO2 every 4h", category="nursing", day_offset=0, time_of_day=time(8, 0), sequence=5),
        dict(title="IV Fluid Change", instructions="NS 500ml over 6h", category="nursing", day_offset=1, time_of_day=time(6, 0), sequence=6),
        dict(title="Blood CBC", instructions="Fasting sample in morning", category="investigation", day_offset=1, time_of_day=time(7, 0), sequence=7),
        dict(title="Physiotherapy", instructions="Passive limb exercises", category="physiotherapy", day_offset=2, time_of_day=time(10, 0), sequence=8),
        dict(title="Soft Diet", instructions="No spicy food, fluids only", category="diet", day_offset=0, time_of_day=time(12, 0), sequence=9),
    ]
    for order in orders:
        TreatmentPlanItem.objects.create(plan=plan, is_active=True, **order)
    generate_tasks_for_plan(plan, today, today)
    print(f"  Created {len(orders)} plan items & generated tasks for today")

# ── Staff Shift ───────────────────────────────────────────────────────────────
from apps.staff.models import StaffProfile, Shift, StaffShiftAssignment

shift = Shift.objects.filter(hospital=hospital).first()
staff_list = StaffProfile.objects.filter(hospital=hospital, is_deleted=False)[:3]
if shift and staff_list:
    for staff in staff_list:
        assignment, created = StaffShiftAssignment.objects.get_or_create(
            hospital=hospital,
            staff=staff,
            date=today,
            defaults={
                "shift": shift,
                "status": "assigned",
                "assigned_by": doctor_user,
            }
        )
        print(f"  {'Created' if created else 'Exists'}: Shift '{shift.name}' assigned to {staff.employee_code}")

print("\n✅ Dummy data seeded successfully!")
print(f"   - {len(patients)} patients")
print(f"   - {len(patients)} OPD tokens for today across 3 rooms")
print(f"   - 1 IPD admission for {ipd_patient.first_name} {ipd_patient.last_name}")
print(f"   - 1 Treatment Plan with 9 medication/nursing orders")
