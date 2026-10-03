from __future__ import annotations

from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.auditlogs.services import create_audit_log
from apps.appointments.filters import AppointmentFilterSet
from apps.appointments.models import Appointment, AppointmentStatusHistory
from apps.appointments.serializers import AppointmentCreateUpdateSerializer, AppointmentSerializer
from apps.roles_permissions.permissions import HasRequiredPermission
from apps.shared.response import success_response


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().select_related("patient", "doctor", "receptionist_user", "doctor__specialty")

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = AppointmentFilterSet
    search_fields = ("patient__uhid", "patient__phone", "patient__first_name", "patient__last_name", "doctor__name")
    ordering_fields = ("appointment_datetime", "queue_order", "created_at", "updated_at")

    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]

    http_method_names = ["get", "post", "put", "patch"]

    required_permission_map = {
        "list": "appointments.view_appointment",
        "retrieve": "appointments.view_appointment",
        "create": "appointments.create_appointment",
        "update": "appointments.update_appointment",
        "partial_update": "appointments.update_appointment",
        "cancel": "appointments.cancel_appointment",
        "reschedule": "appointments.reschedule_appointment",
    }

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return AppointmentSerializer
        return AppointmentCreateUpdateSerializer

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
        appointment: Appointment = serializer.save()

        if not self.request.user.is_superuser:
            if appointment.hospital_id != self.request.user.hospital_id:
                raise permissions.PermissionDenied("Patient/doctor not in your hospital.")

        # Compute queue order within the day for the doctor.
        day = appointment.appointment_datetime.date()
        qs = Appointment.objects.filter(
            hospital_id=appointment.hospital_id,
            doctor_id=appointment.doctor_id,
            appointment_datetime__date=day,
        ).exclude(status=Appointment.Status.CANCELLED).exclude(pk=appointment.pk)
        queue_order = qs.count() + 1

        old_status = appointment.status
        appointment.queue_order = queue_order
        appointment.save(update_fields=["queue_order"])

        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            from_status=old_status,
            to_status=old_status,
            changed_by=self.request.user,
            notes="created",
        )

        create_audit_log(
            request=self.request,
            hospital=appointment.hospital,
            module="appointments",
            action="create_appointment",
            obj=appointment,
            after={"appointment_datetime": str(appointment.appointment_datetime), "status": appointment.status},
        )

    @transaction.atomic
    def perform_update(self, serializer):
        appointment: Appointment = serializer.instance
        old_status = appointment.status
        old_datetime = appointment.appointment_datetime
        old_queue = appointment.queue_order

        appointment = serializer.save()

        if appointment.status != old_status:
            AppointmentStatusHistory.objects.create(
                appointment=appointment,
                from_status=old_status,
                to_status=appointment.status,
                changed_by=self.request.user,
            )

            create_audit_log(
                request=self.request,
                hospital=appointment.hospital,
                module="appointments",
                action="update_status",
                obj=appointment,
                before={"status": old_status},
                after={"status": appointment.status},
            )

        # If datetime changed, recompute queue_order.
        if appointment.appointment_datetime != old_datetime:
            day = appointment.appointment_datetime.date()
            qs = Appointment.objects.filter(
                hospital_id=appointment.hospital_id,
                doctor_id=appointment.doctor_id,
                appointment_datetime__date=day,
            ).exclude(status=Appointment.Status.CANCELLED).exclude(pk=appointment.pk)
            appointment.queue_order = qs.count() + 1
            appointment.save(update_fields=["queue_order"])
            create_audit_log(
                request=self.request,
                hospital=appointment.hospital,
                module="appointments",
                action="reschedule_datetime",
                obj=appointment,
                before={"appointment_datetime": str(old_datetime), "queue_order": old_queue},
                after={"appointment_datetime": str(appointment.appointment_datetime), "queue_order": appointment.queue_order},
            )

    @action(detail=True, methods=["post"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk=None):
        appointment: Appointment = self.get_object()
        if appointment.status == Appointment.Status.CANCELLED:
            return success_response(data=AppointmentSerializer(appointment).data, message="Already cancelled.")

        from_status = appointment.status
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status"])

        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            from_status=from_status,
            to_status=appointment.status,
            changed_by=request.user,
            notes="cancel",
        )

        create_audit_log(
            request=request,
            hospital=appointment.hospital,
            module="appointments",
            action="cancel_appointment",
            obj=appointment,
            before={"status": from_status},
            after={"status": appointment.status},
        )

        return success_response(data=AppointmentSerializer(appointment).data, message="Appointment cancelled.")

    @action(detail=True, methods=["post"], url_path="reschedule")
    @transaction.atomic
    def reschedule(self, request, pk=None):
        appointment: Appointment = self.get_object()
        new_dt = request.data.get("appointment_datetime")
        if not new_dt:
            return Response(
                {"success": False, "errors": {"appointment_datetime": ["This field is required."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_datetime = appointment.appointment_datetime
        from_status = appointment.status
        appointment.appointment_datetime = new_dt
        appointment.status = Appointment.Status.SCHEDULED
        appointment.save(update_fields=["appointment_datetime", "status"])

        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            from_status=from_status,
            to_status=appointment.status,
            changed_by=request.user,
            notes="reschedule",
        )

        create_audit_log(
            request=request,
            hospital=appointment.hospital,
            module="appointments",
            action="reschedule_appointment",
            obj=appointment,
            before={"appointment_datetime": str(old_datetime), "status": from_status},
            after={"appointment_datetime": str(appointment.appointment_datetime), "status": appointment.status},
        )

        return success_response(data=AppointmentSerializer(appointment).data, message="Appointment rescheduled.")

from django.shortcuts import render

# Create your views here.
