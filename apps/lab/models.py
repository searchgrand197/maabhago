from django.conf import settings
from django.db import models
from apps.shared.models import Hospital, TimeStampedModel, UUIDPrimaryKeyModel
from apps.patients.models import Patient
from apps.doctors.models import DoctorProfile

class LabTestCategory(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="lab_categories")
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class LabTest(TimeStampedModel, UUIDPrimaryKeyModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="lab_tests")
    category = models.ForeignKey(LabTestCategory, on_delete=models.PROTECT, related_name="tests")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True, default="")
    unit = models.CharField(max_length=50, blank=True, default="")
    reference_range = models.CharField(max_length=200, blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_group_test = models.BooleanField(default=False) # e.g. Panel
    procedure = models.TextField(blank=True, default="") # Collection / Prep info
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.category.name})"

class LabReport(TimeStampedModel, UUIDPrimaryKeyModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINAL = "final", "Final"
        CANCELLED = "cancelled", "Cancelled"

    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="lab_reports")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="lab_reports")
    referred_by = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_referrals")
    
    lab_no = models.CharField(max_length=50, unique=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    reported_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    validation_status = models.CharField(max_length=50, blank=True, default="Pending") # e.g. Validated by Pathologist
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_lab_reports")

    def __str__(self):
        return f"Report {self.lab_no} - {self.patient.first_name}"

class LabTestResult(TimeStampedModel, UUIDPrimaryKeyModel):
    report = models.ForeignKey(LabReport, on_delete=models.CASCADE, related_name="results")
    test = models.ForeignKey(LabTest, on_delete=models.PROTECT, related_name="results")
    result_value = models.CharField(max_length=100, blank=True, default="")
    is_abnormal = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.test.name}: {self.result_value}"
