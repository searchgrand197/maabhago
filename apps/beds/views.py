from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from apps.beds.models import Bed, BedCleaningTask, BedRoom, Floor
from apps.beds.serializers import (
    BedCleaningTaskSerializer,
    BedRoomSerializer,
    BedSerializer,
    BedStatusUpdateSerializer,
    FloorBriefSerializer,
    FloorSerializer,
    FloorWithRoomsSerializer,
)
from apps.beds.services import ensure_cleaning_task_for_bed, get_on_duty_housekeeping_staff
from apps.shared.response import success_response
from apps.staff.models import StaffProfile


class FloorViewSet(viewsets.ModelViewSet):
    queryset = Floor.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]

    def get_serializer_class(self):
        if self.action in {"list"}:
            return FloorBriefSerializer
        return FloorSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(hospital=user.hospital)

    def perform_create(self, serializer):
        hospital_id = self.request.data.get("hospital_id") or self.request.user.hospital_id
        from apps.shared.models import Hospital
        hospital = Hospital.objects.get(pk=hospital_id)
        serializer.save(hospital=hospital)


class BedRoomViewSet(viewsets.ModelViewSet):
    queryset = BedRoom.objects.select_related("floor").prefetch_related("beds")
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["floor", "room_type", "is_ac", "is_active"]
    search_fields = ["name", "room_number"]

    def get_serializer_class(self):
        return BedRoomSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(hospital=user.hospital)

    def perform_create(self, serializer):
        hospital_id = self.request.data.get("hospital_id") or self.request.user.hospital_id
        from apps.shared.models import Hospital
        hospital = Hospital.objects.get(pk=hospital_id)
        serializer.save(hospital=hospital)


class BedViewSet(viewsets.ModelViewSet):
    queryset = Bed.objects.select_related("room", "room__floor")
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["room", "status", "room__floor", "room__room_type"]
    search_fields = ["bed_code", "bed_number"]

    def get_serializer_class(self):
        if self.action in {"set_status"}:
            return BedStatusUpdateSerializer
        return BedSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(hospital=user.hospital)

    def perform_create(self, serializer):
        hospital_id = self.request.data.get("hospital_id") or self.request.user.hospital_id
        from apps.shared.models import Hospital
        hospital = Hospital.objects.get(pk=hospital_id)
        serializer.save(hospital=hospital)

    @action(detail=True, methods=["patch"], url_path="set-status")
    def set_status(self, request, pk=None):
        bed = self.get_object()
        ser = BedStatusUpdateSerializer(bed, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        if bed.status == Bed.Status.CLEANING:
            ensure_cleaning_task_for_bed(
                bed_code=bed.bed_code,
                hospital_id=bed.hospital_id,
                notes=request.data.get("notes", "") or "Marked cleaning from bed management.",
            )
        return success_response(data=BedSerializer(bed).data)

    @action(detail=False, methods=["get"], url_path="housekeeping-on-duty")
    def housekeeping_on_duty(self, request):
        user = request.user
        hospital_id = user.hospital_id
        qs = get_on_duty_housekeeping_staff(hospital_id).order_by("first_name", "last_name")
        rows = [
            {
                "id": str(s.id),
                "name": f"{s.first_name} {s.last_name}".strip() or s.employee_code,
                "employee_code": s.employee_code,
            }
            for s in qs
        ]
        return success_response(data=rows)

    @action(detail=True, methods=["post"], url_path="fast-clean")
    def fast_clean(self, request, pk=None):
        bed = self.get_object()
        if bed.status != Bed.Status.CLEANING:
            return Response({"error": "Only cleaning beds can be fast-managed."}, status=400)

        staff_id = request.data.get("staff_id")
        mark_available = bool(request.data.get("mark_available", False))
        notes = request.data.get("notes", "") or ""

        assigned_staff = None
        if staff_id:
            assigned_staff = StaffProfile.objects.filter(
                id=staff_id,
                hospital_id=bed.hospital_id,
                employment_status=StaffProfile.EmploymentStatus.ACTIVE,
            ).first()
            if not assigned_staff:
                return Response({"error": "Selected staff not found in this hospital."}, status=400)

        task = ensure_cleaning_task_for_bed(
            bed_code=bed.bed_code,
            hospital_id=bed.hospital_id,
            assigned_staff=assigned_staff,
            notes=notes or "Fast-service reassignment from bed selector.",
        )

        if mark_available:
            bed.status = Bed.Status.AVAILABLE
            if notes:
                bed.notes = notes
            bed.save(update_fields=["status", "notes", "updated_at"])
            if task and task.status != BedCleaningTask.Status.COMPLETED:
                if task.status == BedCleaningTask.Status.PENDING:
                    task.started_at = timezone.now()
                task.status = BedCleaningTask.Status.COMPLETED
                task.completed_at = timezone.now()
                task.completed_by = request.user
                task.save(update_fields=["status", "started_at", "completed_at", "completed_by", "updated_at"])

        return success_response(
            data={
                "bed": BedSerializer(bed).data,
                "task": BedCleaningTaskSerializer(task).data if task else None,
            }
        )

    @action(detail=False, methods=["get"], url_path="by-floor")
    def by_floor(self, request):
        """Return all floors → rooms → beds in one call for the bed-picker UI."""
        qs = Floor.objects.filter(is_active=True)
        user = request.user
        if not user.is_superuser:
            qs = qs.filter(hospital=user.hospital)
        qs = qs.prefetch_related(
            "rooms",
            "rooms__beds",
        ).order_by("floor_number")
        return success_response(data=FloorWithRoomsSerializer(qs, many=True).data)


class BedCleaningTaskViewSet(viewsets.ModelViewSet):
    queryset = BedCleaningTask.objects.select_related("bed", "assigned_staff", "completed_by")
    serializer_class = BedCleaningTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["status", "bed", "assigned_staff"]
    search_fields = ["bed__bed_code", "assigned_staff__employee_code", "assigned_staff__first_name", "assigned_staff__last_name"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(hospital_id=user.hospital_id)
        if self.request.query_params.get("mine") in {"1", "true", "yes"}:
            qs = qs.filter(assigned_staff__user=user)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(hospital_id=user.hospital_id)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        task = self.get_object()
        if task.status == BedCleaningTask.Status.COMPLETED:
            return Response({"error": "Task already completed."}, status=400)
        if task.status == BedCleaningTask.Status.PENDING:
            task.status = BedCleaningTask.Status.IN_PROGRESS
            task.started_at = timezone.now()
            task.save(update_fields=["status", "started_at", "updated_at"])
        return success_response(data=BedCleaningTaskSerializer(task).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        task = self.get_object()
        if task.status == BedCleaningTask.Status.COMPLETED:
            return success_response(data=BedCleaningTaskSerializer(task).data)

        if task.status == BedCleaningTask.Status.PENDING:
            task.started_at = timezone.now()
        task.status = BedCleaningTask.Status.COMPLETED
        task.completed_at = timezone.now()
        task.completed_by = request.user
        task.save(update_fields=["status", "started_at", "completed_at", "completed_by", "updated_at"])

        bed = task.bed
        bed.status = Bed.Status.AVAILABLE
        bed.save(update_fields=["status", "updated_at"])
        return success_response(data=BedCleaningTaskSerializer(task).data)
