import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.shared.models import Hospital
from apps.inventory.models import Medicine, MedicineBatch, Unit
from apps.lab.models import LabTestCategory, LabTest
from apps.patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds HMS with professional dummy data for Lab and Pharmacy"

    def handle(self, *args, **options):
        # 1. Get or Create Hospital
        hospital, _ = Hospital.objects.get_or_create(
            name="Vardaan Multi-Speciality Hospital",
            defaults={"slug": "vardaan-hms"}
        )
        self.stdout.write(f"Hospital: {hospital.name}")

        # 2. Get Admin User
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write("No superuser found. Please create one first.")
            return

        # 3. Units
        unit_strip, _ = Unit.objects.get_or_create(hospital=hospital, code="STRIP", name="Strip")
        unit_vial, _ = Unit.objects.get_or_create(hospital=hospital, code="VIAL", name="Vial")
        unit_tablet, _ = Unit.objects.get_or_create(hospital=hospital, code="TAB", name="Tablet")

        # 4. Medicines (Top 10 common)
        med_list = [
            ("M001", "Paracetamol 500mg", "Tablet", "10x15", "3004.90.11"),
            ("M002", "Amoxicillin 250mg", "Capsule", "10x10", "3004.10.10"),
            ("M003", "Dexamethasone 4mg", "Injection", "2ml Vial", "3004.32.00"),
            ("M004", "Metformin 500mg", "Tablet", "15x10", "3004.90.69"),
            ("M005", "Pantoprazole 40mg", "Tablet", "10x10", "3004.90.99"),
            ("M006", "Azithromycin 500mg", "Tablet", "1x3", "3004.20.19"),
            ("M007", "Cetirizine 10mg", "Tablet", "10x10", "3004.90.39"),
            ("M008", "Omeprazole 20mg", "Capsule", "15x10", "3004.90.99"),
            ("M009", "Ciprofloxacin 500mg", "Tablet", "10x10", "3004.20.19"),
            ("M010", "Atorvastatin 10mg", "Tablet", "10x10", "3004.90.71"),
        ]

        for sku, name, form, pack, hsn in med_list:
            medicine, created = Medicine.objects.get_or_create(
                hospital=hospital,
                sku=sku,
                defaults={
                    "name": name,
                    "form": form,
                    "unit": unit_tablet if form == "Tablet" else unit_strip,
                    "pack_info": pack,
                    "hsn_code": hsn
                }
            )
            if created:
                # Create 2 Batches for each
                for i in range(1, 3):
                    MedicineBatch.objects.create(
                        hospital=hospital,
                        medicine=medicine,
                        batch_no=f"B{random.randint(1000, 9999)}",
                        expiry_date=timezone.now().date() + timezone.timedelta(days=random.randint(300, 700)),
                        unit_cost=Decimal(random.randint(20, 100)),
                        mrp=Decimal(random.randint(110, 200)),
                        sale_rate=Decimal(random.randint(105, 150))
                    )

        self.stdout.write("Medicines and Batches seeded.")

        # 5. Lab Categories
        cat_bio, _ = LabTestCategory.objects.get_or_create(hospital=hospital, name="Biochemistry")
        cat_hem, _ = LabTestCategory.objects.get_or_create(hospital=hospital, name="Hematology")
        cat_ser, _ = LabTestCategory.objects.get_or_create(hospital=hospital, name="Serology")

        # 6. Lab Tests
        tests = [
            (cat_hem, "Complete Blood Count (CBC)", "CBC01", "---", "---", 500, True),
            (cat_bio, "Blood Sugar Fasting", "BSF", "mg/dL", "70 - 110", 100, False),
            (cat_bio, "Blood Sugar Post Prandial", "BSPP", "mg/dL", "< 140", 100, False),
            (cat_bio, "Serum Creatinine", "KFT01", "mg/dL", "0.6 - 1.2", 200, False),
            (cat_hem, "Haemoglobin (Hb)", "HB", "g/dL", "Male: 13-17, Female: 12-15", 150, False),
            (cat_bio, "Liver Function Test (LFT)", "LFT", "---", "---", 800, True),
            (cat_ser, "Widal Test (Slide)", "WID", "---", "---", 300, False),
            (cat_bio, "Uric Acid", "UA", "mg/dL", "3.4 - 7.0", 150, False),
        ]

        for cat, name, code, unit, ref, price, is_group in tests:
            LabTest.objects.get_or_create(
                hospital=hospital,
                name=name,
                defaults={
                    "category": cat,
                    "code": code,
                    "unit": unit,
                    "reference_range": ref,
                    "price": price,
                    "is_group_test": is_group
                }
            )

        self.stdout.write("Lab Tests seeded.")

        # 7. Dummy Patients
        p_objs = []
        patients = [
            ("Rahul", "Sharma", "M", "1992-05-10", "9988776655"),
            ("Suman", "Verma", "F", "1996-08-15", "9988776644"),
            ("Anita", "Devi", "F", "1969-12-01", "9988776633"),
            ("Suresh", "Kumar", "M", "1980-01-20", "9876543210"),
            ("Priya", "Singh", "F", "1998-11-22", "8877665544"),
        ]

        for f, l, g, d, p in patients:
            obj, _ = Patient.objects.get_or_create(
                hospital=hospital,
                first_name=f,
                last_name=l,
                defaults={
                    "gender": g,
                    "dob": d,
                    "phone": p,
                    "uhid": f"UHID-{random.randint(10000, 99999)}"
                }
            )
            p_objs.append(obj)

        self.stdout.write("Dummy Patients seeded.")

        # 8. Dummy Lab Reports
        from apps.lab.models import LabReport, LabResult
        all_tests = list(LabTest.objects.filter(hospital=hospital))
        
        for p in p_objs:
            # Create 1-2 reports per patient
            for _ in range(random.randint(1, 2)):
                report = LabReport.objects.create(
                    hospital=hospital,
                    patient=p,
                    lab_no=f"LAB-{random.randint(100000, 999999)}",
                    collected_at=timezone.now() - timezone.timedelta(hours=random.randint(1, 72)),
                    status=random.choice(['draft', 'final', 'draft']), # Weight towards draft
                    validation_status="Pending Pathologist Verification" if random.choice([True, False]) else ""
                )
                
                # Add 2-3 tests to each report
                sample_tests = random.sample(all_tests, random.randint(1, 3))
                for t in sample_tests:
                    is_ab = random.choice([True, False, False, False])
                    LabResult.objects.create(
                        report=report,
                        test=t,
                        result_value=str(random.randint(80, 160)) if not t.is_group_test else "",
                        is_abnormal=is_ab
                    )
        
        self.stdout.write("Dummy Lab Reports & Results seeded.")

        # 9. Dummy Pharmacy Invoices
        from apps.inventory.models import PharmacyInvoice, PharmacyItem
        all_batches = list(MedicineBatch.objects.filter(hospital=hospital))

        for p in p_objs:
            # Create 1-2 invoices per patient
            for _ in range(random.randint(1, 2)):
                subtotal = Decimal(0)
                inv = PharmacyInvoice.objects.create(
                    hospital=hospital,
                    patient=p,
                    invoice_no=f"INV-{random.randint(10000, 99999)}",
                    status='finalized',
                    created_at=timezone.now() - timezone.timedelta(days=random.randint(0, 30))
                )

                # Add 2-3 items
                sample_batches = random.sample(all_batches, random.randint(1, 3))
                for b in sample_batches:
                    qty = random.randint(1, 5)
                    rate = b.sale_rate or b.unit_cost or 100
                    amt = qty * rate
                    PharmacyItem.objects.create(
                        invoice=inv,
                        medicine=b.medicine,
                        batch=b,
                        qty=qty,
                        rate=rate,
                        amount=amt
                    )
                    subtotal += amt
                
                gst = subtotal * Decimal('0.12')
                inv.subtotal = subtotal
                inv.cgst = gst / 2
                inv.sgst = gst / 2
                inv.grand_total = subtotal + gst
                inv.save()

        self.stdout.write("Dummy Pharmacy Invoices seeded.")
        self.stdout.write(self.style.SUCCESS("HMS DATA SEEDING COMPLETE!"))
