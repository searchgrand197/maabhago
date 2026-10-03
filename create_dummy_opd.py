import sys
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.opd.models import OPDVisit
from apps.patients.models import Patient
from apps.shared.models import Hospital
from django.contrib.auth import get_user_model

User = get_user_model()
hospital = Hospital.objects.first()
doctor = User.objects.first()

# Delete existing today's visits to reset queue
OPDVisit.objects.filter(visit_date=date.today()).delete()

# Create 3 dummy patients
patients_data = [
    ("John", "Doe", "+1234567890", "Severe headache and mild fever"),
    ("Jane", "Smith", "+1987654321", "Cough, cold, and body ache"),
    ("Robert", "Johnson", "+1122334455", "Follow up for hypertension")
]

for idx, (fname, lname, phone, reason) in enumerate(patients_data, start=1):
    patient, _ = Patient.objects.get_or_create(
        hospital=hospital,
        first_name=fname,
        last_name=lname,
        defaults={
            "uhid": f"UHID-{phone}",
            "phone": phone,
            "gender": "male" if fname != "Jane" else "female",
            "dob": "1980-05-15"
        }
    )
    
    OPDVisit.objects.create(
        hospital=hospital,
        patient=patient,
        doctor_user=doctor,
        visit_date=date.today(),
        queue_number=idx,
        visit_reason=reason,
        status="waiting"
    )

print("Successfully created 3 dummy patients and OPD visits for testing.")
