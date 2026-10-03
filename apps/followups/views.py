from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.auditlogs.services import create_audit_log
from apps.followups.filters import FollowUpFilterSet
from apps.followups.models import FollowUp, FollowUpStatusHistory
from apps.followups.serializers import FollowUpCreateUpdateSerializer, FollowUpSerializer
from apps.patients.models import PatientActivity
from apps.roles_permissions.permissions import HasRequiredPermission
from apps.shared.response import success_response

from apps.appointments.models import Appointment


class FollowUpViewSet(viewsets.ModelViewSet):
    queryset = (
        FollowUp.objects.all()
        .select_related("hospital", "patient", "doctor", "assigned_to_receptionist", "linked_appointment")
        .prefetch_related()
    )

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = FollowUpFilterSet
    search_fields = (
        "patient__uhid",
        "patient__phone",
        "patient__first_name",
        "patient__last_name",
        "advice",
        "call_remark",
        "internal_remarks",
    )
    ordering_fields = ("next_visit_date", "created_at", "updated_at", "followup_status")

    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]

    required_permission_map = {
        "list": "followups.view_followup",
        "retrieve": "followups.view_followup",
        "create": "followups.create_followup",
        "update": "followups.update_followup",
        "partial_update": "followups.update_followup",
        "destroy": "followups.delete_followup",
        "mark_called": "followups.mark_called",
        "mark_missed": "followups.mark_missed",
        "schedule_reminder": "followups.schedule_reminder",
        "link_appointment": "followups.link_appointment",
    }

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return FollowUpSerializer
        return FollowUpCreateUpdateSerializer

    def get_required_permission(self) -> str | None:
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(hospital_id=user.hospital_id)

    @transaction.atomic
    def perform_create(self, serializer):
        followup: FollowUp = serializer.save(hospital=serializer.validated_data["patient"].hospital)
        FollowUpStatusHistory.objects.create(
            followup=followup,
            from_status="",
            to_status=followup.followup_status,
            changed_by=self.request.user,
            notes="created",
        )
        create_audit_log(
            request=self.request,
            hospital=followup.hospital,
            module="followups",
            action="create_followup",
            obj=followup,
            after={
                "patient_uhid": followup.patient.uhid,
                "next_visit_date": str(followup.next_visit_date),
                "followup_status": followup.followup_status,
                "reminder_status": followup.reminder_status,
            },
        )
        # Add patient timeline activity.
        PatientActivity.objects.create(
            patient=followup.patient,
            actor=self.request.user,
            activity_type=PatientActivity.ActivityType.NOTE,
            content=f"Follow-up scheduled for {followup.next_visit_date}.",
            internal=True,
        )

    def perform_update(self, serializer):
        followup: FollowUp = serializer.save()

        create_audit_log(
            request=self.request,
            hospital=followup.hospital,
            module="followups",
            action="update_followup",
            obj=followup,
            after={"next_visit_date": str(followup.next_visit_date), "followup_status": followup.followup_status},
        )

    @action(detail=True, methods=["post"], url_path="mark-called")
    @transaction.atomic
    def mark_called(self, request, pk=None):
        followup: FollowUp = self.get_object()
        if followup.followup_status in {FollowUp.FollowUpStatus.CANCELLED, FollowUp.FollowUpStatus.MISSED}:
            return Response(
                {"success": False, "errors": {"detail": ["Cannot mark called in current state."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        call_remark = request.data.get("call_remark") or ""

        old_status = followup.followup_status
        followup.followup_status = FollowUp.FollowUpStatus.CALLED
        followup.called_by = request.user
        followup.called_at = timezone.now()
        followup.call_remark = call_remark
        followup.missed_at = None
        followup.save(update_fields=["followup_status", "called_by", "called_at", "call_remark", "missed_at"])

        FollowUpStatusHistory.objects.create(
            followup=followup,
            from_status=old_status,
            to_status=followup.followup_status,
            changed_by=request.user,
            notes="mark-called",
        )

        create_audit_log(
            request=request,
            hospital=followup.hospital,
            module="followups",
            action="mark_called",
            obj=followup,
            before={"followup_status": old_status},
            after={"followup_status": followup.followup_status},
        )

        PatientActivity.objects.create(
            patient=followup.patient,
            actor=request.user,
            activity_type=PatientActivity.ActivityType.REMARK,
            content=f"Follow-up called. Remark: {call_remark}" if call_remark else "Follow-up called.",
            internal=True,
        )

        return success_response(data=FollowUpSerializer(followup).data, message="Follow-up marked as called.")

    @action(detail=True, methods=["post"], url_path="mark-missed")
    @transaction.atomic
    def mark_missed(self, request, pk=None):
        followup: FollowUp = self.get_object()
        if followup.followup_status in {FollowUp.FollowUpStatus.CANCELLED, FollowUp.FollowUpStatus.COMPLETED}:
            return Response(
                {"success": False, "errors": {"detail": ["Cannot mark missed in current state."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = followup.followup_status
        followup.followup_status = FollowUp.FollowUpStatus.MISSED
        followup.missed_at = timezone.now()
        followup.save(update_fields=["followup_status", "missed_at"])

        FollowUpStatusHistory.objects.create(
            followup=followup,
            from_status=old_status,
            to_status=followup.followup_status,
            changed_by=request.user,
            notes="mark-missed",
        )

        create_audit_log(
            request=request,
            hospital=followup.hospital,
            module="followups",
            action="mark_missed",
            obj=followup,
            before={"followup_status": old_status},
            after={"followup_status": followup.followup_status},
        )

        PatientActivity.objects.create(
            patient=followup.patient,
            actor=request.user,
            activity_type=PatientActivity.ActivityType.STATUS,
            content="Follow-up missed.",
            internal=True,
        )

        return success_response(data=FollowUpSerializer(followup).data, message="Follow-up marked as missed.")

    @action(detail=True, methods=["post"], url_path="schedule-reminder")
    @transaction.atomic
    def schedule_reminder(self, request, pk=None):
        followup: FollowUp = self.get_object()

        scheduled_reminder_at = request.data.get("scheduled_reminder_at")
        reminder_channel = request.data.get("reminder_channel") or followup.reminder_channel

        if not scheduled_reminder_at:
            return Response(
                {"success": False, "errors": {"scheduled_reminder_at": ["This field is required."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parsed_dt = parse_datetime(scheduled_reminder_at) if isinstance(scheduled_reminder_at, str) else scheduled_reminder_at
        if not parsed_dt:
            return Response(
                {"success": False, "errors": {"scheduled_reminder_at": ["Invalid datetime format."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_reminder_status = followup.reminder_status
        followup.scheduled_reminder_at = parsed_dt
        followup.reminder_status = FollowUp.ReminderStatus.SCHEDULED
        followup.reminder_channel = reminder_channel
        followup.save(update_fields=["scheduled_reminder_at", "reminder_status", "reminder_channel"])

        create_audit_log(
            request=request,
            hospital=followup.hospital,
            module="followups",
            action="schedule_reminder",
            obj=followup,
            before={"reminder_status": old_reminder_status},
            after={"reminder_status": followup.reminder_status},
        )

        return success_response(data=FollowUpSerializer(followup).data, message="Reminder scheduled.")

    @action(detail=True, methods=["post"], url_path="link-appointment")
    @transaction.atomic
    def link_appointment(self, request, pk=None):
        followup: FollowUp = self.get_object()
        appointment_id = request.data.get("appointment_id")
        if not appointment_id:
            return Response(
                {"success": False, "errors": {"appointment_id": ["This field is required."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment = Appointment.objects.select_related("hospital").filter(pk=appointment_id).first()
        if not appointment:
            return Response(
                {"success": False, "errors": {"appointment_id": ["Appointment not found."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.is_superuser and appointment.hospital_id != request.user.hospital_id:
            return Response(
                {"success": False, "errors": {"detail": ["Appointment not in your hospital."]}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if appointment.hospital_id != followup.hospital_id:
            return Response(
                {"success": False, "errors": {"detail": ["Appointment/hospital mismatch."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = followup.followup_status
        followup.linked_appointment = appointment
        followup.followup_status = FollowUp.FollowUpStatus.COMPLETED
        followup.reminder_status = FollowUp.ReminderStatus.NONE
        followup.save(update_fields=["linked_appointment", "followup_status", "reminder_status"])

        FollowUpStatusHistory.objects.create(
            followup=followup,
            from_status=old_status,
            to_status=followup.followup_status,
            changed_by=request.user,
            notes="link-appointment",
        )

        create_audit_log(
            request=request,
            hospital=followup.hospital,
            module="followups",
            action="link_appointment",
            obj=followup,
            before={"followup_status": old_status},
            after={"followup_status": followup.followup_status},
        )

        return success_response(data=FollowUpSerializer(followup).data, message="Follow-up completed.")

from django.shortcuts import render

# Create your views here.
