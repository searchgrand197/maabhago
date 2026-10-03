from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.attendance.models import (
    AttendanceRegularization,
    LeaveApplication,
    MonthlyEarnedLeaveAllocation,
    StaffDailyAttendance,
    StaffLeaveBalance,
)
from apps.attendance.services import compute_leave_total_days


class StaffDailyAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source="staff.employee_code", read_only=True)

    class Meta:
        model = StaffDailyAttendance
        fields = (
            "id",
            "hospital",
            "staff",
            "staff_name",
            "employee_code",
            "attendance_date",
            "check_in_at",
            "check_out_at",
            "status",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "hospital", "created_at", "updated_at")

    def get_staff_name(self, obj):
        return f"{obj.staff.first_name} {obj.staff.last_name}".strip() or str(obj.staff_id)


class AttendanceRegularizationSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRegularization
        fields = (
            "id",
            "hospital",
            "staff",
            "staff_name",
            "attendance_date",
            "requested_check_in_at",
            "requested_check_out_at",
            "reason",
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "hospital",
            "staff",
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "created_at",
            "updated_at",
        )

    def get_staff_name(self, obj):
        return f"{obj.staff.first_name} {obj.staff.last_name}".strip() or str(obj.staff_id)

    def validate(self, attrs):
        inc = attrs.get("requested_check_in_at") or getattr(self.instance, "requested_check_in_at", None)
        out = attrs.get("requested_check_out_at") or getattr(self.instance, "requested_check_out_at", None)
        if not inc and not out:
            raise serializers.ValidationError("Provide requested_check_in_at and/or requested_check_out_at.")
        return attrs


class LeaveApplicationSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "hospital",
            "staff",
            "staff_name",
            "leave_type",
            "start_date",
            "end_date",
            "is_half_day",
            "first_half",
            "reason",
            "total_days",
            "status",
            "approved_by",
            "approved_at",
            "rejection_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "hospital",
            "staff",
            "total_days",
            "status",
            "approved_by",
            "approved_at",
            "rejection_notes",
            "created_at",
            "updated_at",
        )

    def get_staff_name(self, obj):
        return f"{obj.staff.first_name} {obj.staff.last_name}".strip() or str(obj.staff_id)

    def validate(self, attrs):
        start = attrs.get("start_date") or (self.instance and self.instance.start_date)
        end = attrs.get("end_date") or (self.instance and self.instance.end_date)
        is_half = attrs.get("is_half_day", getattr(self.instance, "is_half_day", False))
        if start and end and end < start:
            raise serializers.ValidationError("end_date must be on or after start_date.")
        if start and end:
            try:
                compute_leave_total_days(start, end, is_half_day=is_half)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return attrs

    def create(self, validated_data):
        total = compute_leave_total_days(
            validated_data["start_date"],
            validated_data["end_date"],
            is_half_day=validated_data.get("is_half_day", False),
        )
        validated_data["total_days"] = total
        
        l_type = validated_data.get("leave_type")
        staff = validated_data.get("staff")
        
        # Only enforce balance check for Earned Leave
        if staff and l_type == LeaveApplication.LeaveType.EARNED:
            bal, _ = StaffLeaveBalance.objects.get_or_create(staff=staff, leave_type=l_type)
            if bal.balance_days < total:
                if bal.balance_days <= 0:
                    msg = f"No {l_type} leave is left. You cannot apply for {l_type} leave at this time."
                else:
                    msg = f"Insufficient {l_type} leave balance. You are requesting {total} day(s), but only have {bal.balance_days} day(s) available."
                raise serializers.ValidationError({"detail": msg})
                
        return super().create(validated_data)


class MonthlyEarnedLeaveAllocationSerializer(serializers.ModelSerializer):
    designation_name = serializers.CharField(source="designation.name", read_only=True)
    designation_code = serializers.CharField(source="designation.code", read_only=True)

    class Meta:
        model = MonthlyEarnedLeaveAllocation
        fields = (
            "id",
            "hospital",
            "year",
            "month",
            "designation",
            "designation_name",
            "designation_code",
            "earned_days",
            "is_applied",
            "applied_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "hospital", "is_applied", "applied_at", "created_at", "updated_at")

    def validate(self, attrs):
        month = attrs.get("month", getattr(self.instance, "month", None))
        if month is not None and (month < 1 or month > 12):
            raise serializers.ValidationError({"month": "Month must be 1–12."})
        designation = attrs.get("designation") or (self.instance and self.instance.designation)
        hospital = attrs.get("hospital") or (self.instance and self.instance.hospital)
        if designation and hospital and designation.hospital_id != hospital.id:
            raise serializers.ValidationError("Designation must belong to the same hospital.")
        return attrs


class StaffLeaveBalanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source="staff.employee_code", read_only=True)

    class Meta:
        model = StaffLeaveBalance
        fields = (
            "id",
            "staff",
            "staff_name",
            "employee_code",
            "leave_type",
            "balance_days",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "staff",
            "staff_name",
            "employee_code",
            "leave_type",
            "balance_days",
            "created_at",
            "updated_at",
        )

    def get_staff_name(self, obj):
        return f"{obj.staff.first_name} {obj.staff.last_name}".strip() or str(obj.staff_id)


class PunchSerializer(serializers.Serializer):
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    attendance_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, default="")

