from rest_framework import serializers
from apps.lab.models import LabTestCategory, LabTest, LabReport, LabTestResult
from apps.patients.serializers import PatientSerializer
from apps.doctors.serializers import DoctorProfileSerializer

class LabTestCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestCategory
        fields = ("id", "name")

class LabTestSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")
    
    class Meta:
        model = LabTest
        fields = ("id", "name", "code", "category", "category_name", "unit", "reference_range", "price", "is_group_test", "procedure", "is_active")

class LabTestResultSerializer(serializers.ModelSerializer):
    test_name = serializers.ReadOnlyField(source="test.name")
    test_unit = serializers.ReadOnlyField(source="test.unit")
    test_ref = serializers.ReadOnlyField(source="test.reference_range")
    category_name = serializers.ReadOnlyField(source="test.category.name")
    
    class Meta:
        model = LabTestResult
        fields = ("id", "report", "test", "test_name", "test_unit", "test_ref", "category_name", "result_value", "is_abnormal")

class LabReportSerializer(serializers.ModelSerializer):
    patient_details = PatientSerializer(source="patient", read_only=True)
    doctor_details = DoctorProfileSerializer(source="referred_by", read_only=True)
    results = LabTestResultSerializer(many=True, read_only=True)
    
    class Meta:
        model = LabReport
        fields = (
            "id", "patient", "patient_details", "referred_by", "doctor_details", 
            "lab_no", "collected_at", "reported_at", "status", "validation_status", "notes", "results", "created_at"
        )
