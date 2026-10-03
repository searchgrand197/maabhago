from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from apps.attendance.models import (
    AttendanceRegularization,
    LeaveApplication,
    MonthlyEarnedLeaveAllocation,
    StaffDailyAttendance,
    StaffLeaveBalance,
)
from apps.attendance.serializers import (
    AttendanceRegularizationSerializer,
    LeaveApplicationSerializer,
    MonthlyEarnedLeaveAllocationSerializer,
    PunchSerializer,
    StaffDailyAttendanceSerializer,
    StaffLeaveBalanceSerializer,
)
from apps.attendance.services import (
    approve_leave_application,
    approve_regularization,
    apply_monthly_earned_allocation,
    auto_allocate_earned_leave_for_month,
    cancel_leave_application,
    get_staff_profile_for_user,
    punch_check_in,
    punch_check_out,
)
from apps.roles_permissions.effective_permissions import permission_codes_for_user
from apps.roles_permissions.permissions import HasRequiredPermission
from apps.shared.response import success_response


def _attendance_codes(request) -> set[str]:
    return set(permission_codes_for_user(request.user))


def _sees_all_hospital(request) -> bool:
    if getattr(request.user, "is_superuser", False):
        return True
    return "attendance.view_attendance" in _attendance_codes(request)


def _hospital_qs(queryset, request):
    user = request.user
    if user.is_superuser:
        hid = request.query_params.get("hospital_id")
        if hid:
            return queryset.filter(hospital_id=hid)
        return queryset
    if user.hospital_id is None:
        return queryset.none()
    return queryset.filter(hospital_id=user.hospital_id)


class StaffDailyAttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffDailyAttendance.objects.all().select_related("staff", "hospital")
    serializer_class = StaffDailyAttendanceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("staff", "attendance_date", "status")
    ordering = ("-attendance_date",)
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]

    required_permission_map = {
        "list": "attendance.view_attendance",
        "retrieve": "attendance.view_attendance",
        "check_in": "attendance.punch_attendance",
        "check_out": "attendance.punch_attendance",
    }

    def get_required_permission(self) -> str | None:
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def get_queryset(self):
        qs = _hospital_qs(super().get_queryset(), self.request)
        if _sees_all_hospital(self.request):
            return qs
        staff = get_staff_profile_for_user(self.request.user)
        if not staff:
            return qs.none()
        return qs.filter(staff_id=staff.id)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return success_response(data=ser.data)

    def retrieve(self, request, *args, **kwargs):
        inst = self.get_object()
        return success_response(data=self.get_serializer(inst).data)

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request, *args, **kwargs):
        ser = PunchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        staff_id = ser.validated_data.get("staff_id")
        if staff_id:
            from apps.staff.models import StaffProfile
            staff = StaffProfile.objects.filter(id=staff_id, hospital_id=request.user.hospital_id).first()
        else:
            staff = get_staff_profile_for_user(request.user)
            
        if not staff:
            raise ValidationError({"staff": ["Active staff profile not found."]})
        try:
            row = punch_check_in(
                staff=staff,
                attendance_date=ser.validated_data.get("attendance_date"),
                notes=ser.validated_data.get("notes") or "",
            )
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        return success_response(data=StaffDailyAttendanceSerializer(row).data, status_code=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request, *args, **kwargs):
        ser = PunchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        staff_id = ser.validated_data.get("staff_id")
        if staff_id:
            from apps.staff.models import StaffProfile
            staff = StaffProfile.objects.filter(id=staff_id, hospital_id=request.user.hospital_id).first()
        else:
            staff = get_staff_profile_for_user(request.user)
            
        if not staff:
            raise ValidationError({"staff": ["Active staff profile not found."]})
        try:
            row = punch_check_out(
                staff=staff,
                attendance_date=ser.validated_data.get("attendance_date"),
                notes=ser.validated_data.get("notes") or "",
            )
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        return success_response(data=StaffDailyAttendanceSerializer(row).data)


class AttendanceRegularizationViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRegularization.objects.all().select_related("staff", "hospital", "reviewed_by")
    serializer_class = AttendanceRegularizationSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("staff", "attendance_date", "status")
    ordering = ("-created_at",)
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]
    http_method_names = ["get", "post", "head", "options"]

    required_permission_map = {
        "list": "attendance.view_attendance",
        "retrieve": "attendance.view_attendance",
        "create": "attendance.submit_regularization",
    }

    def get_required_permission(self) -> str | None:
        if self.action in ("approve", "reject"):
            return "attendance.approve_regularization"
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def get_queryset(self):
        qs = _hospital_qs(super().get_queryset(), self.request)
        if _sees_all_hospital(self.request):
            return qs
        staff = get_staff_profile_for_user(self.request.user)
        if not staff:
            return qs.none()
        return qs.filter(staff_id=staff.id)

    def perform_create(self, serializer):
        staff = get_staff_profile_for_user(self.request.user)
        if not staff:
            raise ValidationError({"staff": ["No active staff profile for your user."]})
        serializer.save(hospital_id=staff.hospital_id, staff=staff)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        ser = self.get_serializer(qs, many=True)
        return success_response(data=ser.data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(data=self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)
        return success_response(data=ser.data, status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        approve = bool(request.data.get("approve", True))
        notes = str(request.data.get("review_notes") or "")
        req = self.get_object()
        try:
            approve_regularization(req=req, reviewer=request.user, approve=approve, review_notes=notes)
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        return success_response(data=AttendanceRegularizationSerializer(req).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        req = self.get_object()
        notes = str(request.data.get("review_notes") or "")
        try:
            approve_regularization(req=req, reviewer=request.user, approve=False, review_notes=notes)
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        return success_response(data=AttendanceRegularizationSerializer(req).data)


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all().select_related("staff", "hospital", "approved_by")
    serializer_class = LeaveApplicationSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("staff", "leave_type", "status", "start_date", "end_date")
    ordering = ("-created_at",)
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]
    http_method_names = ["get", "post", "head", "options"]

    required_permission_map = {
        "list": "attendance.view_attendance",
        "retrieve": "attendance.view_attendance",
        "create": "attendance.submit_leave",
    }

    def get_required_permission(self) -> str | None:
        if self.action in ("approve", "reject", "reject_leave"):
            return "attendance.approve_leave"
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def get_queryset(self):
        qs = _hospital_qs(super().get_queryset(), self.request)
        if _sees_all_hospital(self.request):
            return qs
        staff = get_staff_profile_for_user(self.request.user)
        if not staff:
            return qs.none()
        return qs.filter(staff_id=staff.id)

    def perform_create(self, serializer):
        staff = get_staff_profile_for_user(self.request.user)
        if not staff:
            raise ValidationError({"staff": ["No active staff profile for your user."]})
        serializer.save(hospital_id=staff.hospital_id, staff=staff)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return success_response(data=self.get_serializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(data=self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)

        # Fire-and-forget: notify all hospital leave approvers via email.
        try:
            from apps.attendance.email_utils import send_leave_approval_emails
            print(f"[leave-email] create(): about to send notifications for leave={ser.instance.id}")
            send_leave_approval_emails(ser.instance)
        except Exception as exc:
            # Never block the API response due to an email failure, but log it.
            print(f"[leave-email] create(): FAILED to trigger email for leave={getattr(ser.instance, 'id', None)}: {exc}")

        return success_response(data=ser.data, status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        approve = bool(request.data.get("approve", True))
        notes = str(request.data.get("rejection_notes") or "")
        allow_negative = bool(request.data.get("allow_negative_balance", False))
        app = self.get_object()
        try:
            approve_leave_application(
                application=app,
                approver=request.user,
                approve=approve,
                rejection_notes=notes,
                allow_negative_balance=allow_negative,
            )
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        app.refresh_from_db()
        return success_response(data=LeaveApplicationSerializer(app).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_leave(self, request, pk=None):
        app = self.get_object()
        notes = str(request.data.get("rejection_notes") or "")
        try:
            approve_leave_application(
                application=app,
                approver=request.user,
                approve=False,
                rejection_notes=notes,
            )
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        app.refresh_from_db()
        return success_response(data=LeaveApplicationSerializer(app).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Allow staff to cancel their own pending or approved leave requests.
        Restores balance automatically if the leave was already approved.
        """
        app = self.get_object()
        staff = get_staff_profile_for_user(request.user)
        if not staff or app.staff_id != staff.id:
            raise ValidationError({"detail": ["You can only cancel your own leave applications."]})
        try:
            cancel_leave_application(application=app, cancelled_by_staff=True)
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        app.refresh_from_db()
        return success_response(data=LeaveApplicationSerializer(app).data)


class MonthlyEarnedLeaveAllocationViewSet(viewsets.ModelViewSet):
    queryset = MonthlyEarnedLeaveAllocation.objects.all().select_related("hospital", "designation")
    serializer_class = MonthlyEarnedLeaveAllocationSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("year", "month", "designation", "is_applied")
    ordering = ("-year", "-month")
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]

    required_permission_map = {
        "list": "attendance.manage_earned_leave",
        "retrieve": "attendance.manage_earned_leave",
        "create": "attendance.manage_earned_leave",
        "update": "attendance.manage_earned_leave",
        "partial_update": "attendance.manage_earned_leave",
        "destroy": "attendance.manage_earned_leave",
    }

    def get_required_permission(self) -> str | None:
        if self.action == "apply":
            return "attendance.manage_earned_leave"
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def get_queryset(self):
        return _hospital_qs(super().get_queryset(), self.request)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser:
            hid = serializer.validated_data.get("hospital_id") or user.hospital_id
        else:
            hid = user.hospital_id
        if not hid:
            raise ValidationError({"hospital": ["Hospital is required."]})
        serializer.save(hospital_id=hid)

    def perform_update(self, serializer):
        if serializer.instance.is_applied:
            raise ValidationError({"is_applied": ["Cannot edit an allocation that was already applied."]})
        serializer.save()

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return success_response(data=self.get_serializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(data=self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)
        return success_response(data=ser.data, status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        inst = self.get_object()
        ser = self.get_serializer(inst, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        self.perform_update(ser)
        return success_response(data=ser.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        inst = self.get_object()
        if inst.is_applied:
            raise ValidationError({"is_applied": ["Cannot delete an applied allocation."]})
        pk = inst.pk
        inst.delete()
        return success_response(data={"id": str(pk)})

    @action(detail=True, methods=["post"], url_path="apply")
    def apply(self, request, pk=None):
        alloc = self.get_object()
        try:
            count = apply_monthly_earned_allocation(allocation=alloc)
        except ValueError as e:
            raise ValidationError({"detail": [str(e)]})
        alloc.refresh_from_db()
        return success_response(
            data={
                "allocation": MonthlyEarnedLeaveAllocationSerializer(alloc).data,
                "staff_records_credited": count,
            }
        )

    @action(detail=False, methods=["post"], url_path="auto-credit")
    def auto_credit(self, request, pk=None):
        """
        Simple helper endpoint: credit 2 earned-leave days to every active staff
        for the given month (year, month), defaulting to the current month.
        """
        from datetime import date as dt_date

        today = dt_date.today()
        year = int(request.data.get("year") or today.year)
        month = int(request.data.get("month") or today.month)
        credited = auto_allocate_earned_leave_for_month(year=year, month=month)
        return success_response(
            data={"year": year, "month": month, "staff_credited": credited},
            message=f"Credited earned leave for {credited} staff.",
        )


class StaffLeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffLeaveBalance.objects.all().select_related("staff", "staff__hospital")
    serializer_class = StaffLeaveBalanceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("staff", "leave_type")
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]
    required_permission_map = {
        "list": "attendance.view_attendance",
        "retrieve": "attendance.view_attendance",
    }

    def get_required_permission(self) -> str | None:
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def get_queryset(self):
        qs = StaffLeaveBalance.objects.all().select_related("staff")
        user = self.request.user
        if user.is_superuser:
            hid = self.request.query_params.get("hospital_id")
            if hid:
                qs = qs.filter(staff__hospital_id=hid)
        elif user.hospital_id:
            qs = qs.filter(staff__hospital_id=user.hospital_id)
        else:
            return qs.none()
        if _sees_all_hospital(self.request):
            return qs.order_by("staff_id", "leave_type")
        staff = get_staff_profile_for_user(user)
        if not staff:
            return qs.none()
        return qs.filter(staff_id=staff.id).order_by("leave_type")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return success_response(data=self.get_serializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(data=self.get_serializer(self.get_object()).data)

    @action(detail=False, methods=["get"], url_path="my-earned-this-month",
            permission_classes=[permissions.IsAuthenticated])
    def my_earned_this_month(self, request):
        """
        Returns the earned-leave days allocated to the logged-in staff's
        designation for the current month/year.  No special permission needed —
        staff can always read their own entitlement.
        """
        from datetime import date as dt_date

        staff = get_staff_profile_for_user(request.user)
        if not staff or not getattr(staff, "designation_id", None):
            return success_response(data={"earned_days": 0, "month": None, "year": None})

        today = dt_date.today()
        alloc = MonthlyEarnedLeaveAllocation.objects.filter(
            hospital_id=staff.hospital_id,
            designation_id=staff.designation_id,
            year=today.year,
            month=today.month,
        ).first()

        return success_response(data={
            "earned_days": float(alloc.earned_days) if alloc else 0,
            "month": today.month,
            "year": today.year,
            "designation": str(staff.designation_id),
        })
