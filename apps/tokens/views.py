from __future__ import annotations

from datetime import date as date_cls

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.auditlogs.services import create_audit_log
from apps.doctors.models import DoctorProfile
from apps.patients.models import Patient
from apps.roles_permissions.permissions import HasRequiredPermission
from apps.shared.response import success_response
from apps.tokens.models import DailyTokenCounter, Token, TokenStatusHistory
from apps.tokens.serializers import TokenCreateSerializer, TokenSerializer


class TokenViewSet(viewsets.ModelViewSet):
    queryset = Token.objects.all().select_related("doctor", "patient", "called_by", "created_by", "appointment")
    filter_backends = (DjangoFilterBackend, SearchFilter)

    search_fields = ("patient__uhid", "patient__phone", "patient__first_name", "patient__last_name", "doctor__name")

    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]

    http_method_names = ["get", "post", "patch"]

    required_permission_map = {
        "list": "tokens.view_token",
        "retrieve": "tokens.view_token",
        "create": "tokens.generate_token",
        "set_status": "tokens.update_token_status",
        "call_next": "tokens.call_next_token",
        "display": "tokens.view_token",
    }

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return TokenSerializer
        if self.action in {"display", "call_next", "set_status"}:
            return TokenSerializer
        return TokenCreateSerializer

    def get_required_permission(self):
        return self.required_permission_map.get(getattr(self, "action", None))

    def get_permissions(self):
        self.required_permission = self.get_required_permission()
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        input_serializer = TokenCreateSerializer(data=request.data, context={"request": request})
        input_serializer.is_valid(raise_exception=True)
        token = self.perform_create(input_serializer)
        return success_response(data=TokenSerializer(token).data, status_code=status.HTTP_201_CREATED)

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(hospital_id=user.hospital_id)

    @transaction.atomic
    def perform_create(self, serializer):
        date = serializer.validated_data.get("date") or timezone.now().date()
        doctor_id = serializer.validated_data["doctor"]
        patient_id = serializer.validated_data["patient"]
        appointment_id = serializer.validated_data.get("appointment")

        hospital_id = self.request.user.hospital_id
        if not self.request.user.is_superuser and hospital_id is None:
            raise permissions.PermissionDenied("User not assigned to a hospital.")

        doctor = DoctorProfile.objects.select_related("hospital").get(pk=doctor_id)
        patient = Patient.objects.select_related("hospital").get(pk=patient_id)

        if not self.request.user.is_superuser:
            if doctor.hospital_id != hospital_id or patient.hospital_id != hospital_id:
                raise permissions.PermissionDenied("Doctor/Patient not in your hospital.")

        if appointment_id:
            # Optional link validation
            from apps.appointments.models import Appointment

            appointment = Appointment.objects.get(pk=appointment_id)
            if appointment.hospital_id != doctor.hospital_id:
                raise permissions.PermissionDenied("Appointment not in the same hospital.")
        else:
            appointment = None

        counter, _ = DailyTokenCounter.objects.select_for_update().get_or_create(
            hospital_id=doctor.hospital_id,
            doctor=doctor,
            date=date,
            defaults={"current_number": 0},
        )

        from_status = Token.Status.WAITING
        counter.current_number += 1
        counter.save(update_fields=["current_number"])

        queue_order = Token.objects.filter(hospital_id=doctor.hospital_id, doctor=doctor, date=date).count() + 1

        token = Token.objects.create(
            hospital_id=doctor.hospital_id,
            doctor=doctor,
            patient=patient,
            date=date,
            token_number=counter.current_number,
            queue_order=queue_order,
            appointment=appointment,
            status=from_status,
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )

        TokenStatusHistory.objects.create(
            token=token,
            from_status=token.status,
            to_status=token.status,
            changed_by=self.request.user,
            notes="created",
        )

        create_audit_log(
            request=self.request,
            hospital=doctor.hospital,
            module="tokens",
            action="generate_token",
            obj=token,
            after={"token_number": token.token_number, "status": token.status},
        )

        return token

    def update(self, request, *args, **kwargs):
        return Response({"success": False, "errors": {"detail": ["Use set_status action."]}}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="set-status")
    @transaction.atomic
    def set_status(self, request, pk=None):
        token: Token = self.get_object()
        new_status = request.data.get("status")
        notes = request.data.get("notes") or ""
        if not new_status:
            return Response({"success": False, "errors": {"status": ["This field is required."]}}, status=400)

        if new_status not in {c for c in Token.Status.values}:
            return Response({"success": False, "errors": {"status": ["Invalid status."]}}, status=400)

        old_status = token.status
        if old_status == new_status:
            return success_response(data=TokenSerializer(token).data, message="Status unchanged.")

        token.status = new_status
        if new_status == Token.Status.IN_PROGRESS:
            token.called_by = request.user
            token.called_at = timezone.now()
        token.save(update_fields=["status", "called_by", "called_at"])

        TokenStatusHistory.objects.create(
            token=token,
            from_status=old_status,
            to_status=new_status,
            changed_by=request.user,
            notes=notes,
        )

        create_audit_log(
            request=request,
            hospital=token.hospital,
            module="tokens",
            action="update_token_status",
            obj=token,
            before={"status": old_status},
            after={"status": token.status},
        )

        return success_response(data=TokenSerializer(token).data, message="Token status updated.")

    @action(detail=False, methods=["post"], url_path="call-next")
    @transaction.atomic
    def call_next(self, request, *args, **kwargs):
        doctor_id = request.data.get("doctor")
        date_value = request.data.get("date") or timezone.now().date().isoformat()
        if isinstance(date_value, str):
            try:
                date_value = date_cls.fromisoformat(date_value)
            except Exception:
                return Response(
                    {"success": False, "errors": {"date": ["Invalid date format. Use YYYY-MM-DD."]}},
                    status=400,
                )
        date = date_value
        if not doctor_id:
            return Response({"success": False, "errors": {"doctor": ["This field is required."]}}, status=400)

        qs = Token.objects.filter(status=Token.Status.WAITING, doctor_id=doctor_id, date=date)
        if not request.user.is_superuser:
            qs = qs.filter(hospital_id=request.user.hospital_id)

        token = qs.order_by("queue_order", "token_number").first()
        if not token:
            return Response({"success": False, "errors": {"detail": ["No waiting tokens found."]}}, status=404)

        old_status = token.status
        token.status = Token.Status.IN_PROGRESS
        token.called_by = request.user
        token.called_at = timezone.now()
        token.save(update_fields=["status", "called_by", "called_at"])

        TokenStatusHistory.objects.create(
            token=token,
            from_status=old_status,
            to_status=token.status,
            changed_by=request.user,
            notes="call-next",
        )

        create_audit_log(
            request=request,
            hospital=token.hospital,
            module="tokens",
            action="call_next_token",
            obj=token,
            before={"status": old_status},
            after={"status": token.status},
        )

        return success_response(data=TokenSerializer(token).data, message="Next token called.")

    @action(detail=False, methods=["get"], url_path="display")
    def display(self, request, *args, **kwargs):
        doctor_id = request.query_params.get("doctor_id")
        date_value = request.query_params.get("date") or timezone.now().date().isoformat()
        if isinstance(date_value, str):
            try:
                date_value = date_cls.fromisoformat(date_value)
            except Exception:
                return Response(
                    {"success": False, "errors": {"date": ["Invalid date format. Use YYYY-MM-DD."]}},
                    status=400,
                )
        date = date_value
        if not doctor_id:
            return Response({"success": False, "errors": {"doctor_id": ["This field is required."]}}, status=400)

        qs = Token.objects.filter(doctor_id=doctor_id, date=date).exclude(status=Token.Status.CANCELLED)

        if not request.user.is_superuser:
            qs = qs.filter(hospital_id=request.user.hospital_id)

        qs = qs.filter(status__in=[Token.Status.WAITING, Token.Status.IN_PROGRESS]).order_by("queue_order", "token_number")
        data = [
            {
                "token_number": t.token_number,
                "queue_order": t.queue_order,
                "patient_uhid": t.patient.uhid,
                "status": t.status,
            }
            for t in qs
        ]

        waiting_qs = Token.objects.filter(doctor_id=doctor_id, date=date, status=Token.Status.WAITING).exclude(status=Token.Status.CANCELLED)
        if not request.user.is_superuser:
            waiting_qs = waiting_qs.filter(hospital_id=request.user.hospital_id)

        waiting_count = waiting_qs.count()

        return success_response(data={"doctor_id": doctor_id, "date": str(date), "queue": data, "waiting_count": waiting_count})
