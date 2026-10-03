from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from apps.lab.models import LabTestCategory, LabTest, LabReport, LabTestResult
from apps.lab.serializers import LabTestCategorySerializer, LabTestSerializer, LabReportSerializer, LabTestResultSerializer
from apps.shared.response import success_response

class LabTestCategoryViewSet(viewsets.ModelViewSet):
    queryset = LabTestCategory.objects.all()
    serializer_class = LabTestCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return super().get_queryset().filter(hospital=self.request.user.hospital)
        
    def perform_create(self, serializer):
        serializer.save(hospital=self.request.user.hospital)

class LabTestViewSet(viewsets.ModelViewSet):
    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return super().get_queryset().filter(hospital=self.request.user.hospital)
        
    def perform_create(self, serializer):
        serializer.save(hospital=self.request.user.hospital)

class LabReportViewSet(viewsets.ModelViewSet):
    queryset = LabReport.objects.all().order_by("-created_at")
    serializer_class = LabReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return super().get_queryset().filter(hospital=self.request.user.hospital)
        
    def perform_create(self, serializer):
        # Generate lab no if not present
        import uuid
        lab_no = f"LAB-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(hospital=self.request.user.hospital, created_by=self.request.user, lab_no=lab_no)

class LabTestResultViewSet(viewsets.ModelViewSet):
    queryset = LabTestResult.objects.all()
    serializer_class = LabTestResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return super().get_queryset().filter(report__hospital=self.request.user.hospital)
