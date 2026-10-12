from __future__ import annotations

import re
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Max, Q, Sum
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters import rest_framework as django_filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from apps.ambulance.models import AmbulanceCollection, AmbulanceVehicle, normalize_vehicle_number
from apps.ambulance.serializers import (
    AmbulanceCollectionSerializer,
    AmbulanceVehicleSerializer,
    VoidSerializer,
)
from apps.auditlogs.services import create_audit_log
from apps.roles_permissions.permissions import HasRequiredPermission
from apps.shared.response import success_response

ZERO = Decimal("0.00")


def _hospital_required_response():
    return Response(
        {"success": False, "errors": {"hospital": ["User is not linked to a hospital."]}},
        status=status.HTTP_400_BAD_REQUEST,
    )


class AmbulanceVehicleViewSet(viewsets.ModelViewSet):
    queryset = AmbulanceVehicle.objects.all()
    serializer_class = AmbulanceVehicleSerializer
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]
    http_method_names = ["get", "post", "patch"]
    pagination_class = None
    required_permission_map = {
        "list": "ambulance.view_collection",
        "retrieve": "ambulance.view_collection",
        "summary": "ambulance.view_collection",
        "create": "ambulance.manage_vehicle",
        "partial_update": "ambulance.manage_vehicle",
    }

    def get_permissions(self):
        self.required_permission = self.required_permission_map.get(getattr(self, "action", None))
        return super().get_permissions()

    def get_queryset(self):
        hospital_id = self.request.user.hospital_id
        if not hospital_id:
            return AmbulanceVehicle.objects.none()
        qs = AmbulanceVehicle.objects.filter(hospital_id=hospital_id)
        active = self.request.query_params.get("is_active")
        if active in {"true", "false"}:
            qs = qs.filter(is_active=active == "true")
        return qs.order_by("-is_active", "vehicle_number")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["hospital_id"] = self.request.user.hospital_id
        return ctx

    def list(self, request, *args, **kwargs):
        return success_response(data=self.get_serializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        if not request.user.hospital_id:
            return _hospital_required_response()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vehicle = serializer.save(hospital_id=request.user.hospital_id)
        create_audit_log(
            request=request,
            hospital=vehicle.hospital,
            module="ambulance",
            action="create_vehicle",
            obj=vehicle,
            after={"vehicle_number": vehicle.vehicle_number, "driver_name": vehicle.driver_name},
        )
        return success_response(data=self.get_serializer(vehicle).data, status_code=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        vehicle = self.get_object()
        serializer = self.get_serializer(vehicle, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changed = list(serializer.validated_data.keys())
        before = {k: str(getattr(vehicle, k)) for k in changed}
        vehicle = serializer.save()
        create_audit_log(
            request=request,
            hospital=vehicle.hospital,
            module="ambulance",
            action="update_vehicle",
            obj=vehicle,
            before=before,
            after={k: str(getattr(vehicle, k)) for k in changed},
        )
        return success_response(data=self.get_serializer(vehicle).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Vehicle-wise collection for a date range, used to monitor each ambulance."""
        hospital_id = request.user.hospital_id
        if not hospital_id:
            return _hospital_required_response()

        today = timezone.localdate()
        date_from = parse_date(request.query_params.get("date_from") or "") or today
        date_to = parse_date(request.query_params.get("date_to") or "") or today
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        days_in_range = (date_to - date_from).days + 1

        active_qs = AmbulanceCollection.objects.filter(
            hospital_id=hospital_id,
            is_deleted=False,
            voided=False,
            status=AmbulanceCollection.Status.SUCCESS,
        )
        range_qs = active_qs.filter(collected_at__date__gte=date_from, collected_at__date__lte=date_to)

        per_vehicle = {
            row["vehicle_id"]: row
            for row in range_qs.values("vehicle_id").annotate(
                entries=Count("id"),
                trips=Sum("trip_count"),
                total=Sum("amount"),
                cash=Sum("amount", filter=Q(payment_mode=AmbulanceCollection.PaymentMode.CASH)),
                upi=Sum("amount", filter=Q(payment_mode=AmbulanceCollection.PaymentMode.UPI)),
            )
        }
        last_seen = {
            row["vehicle_id"]: row["last"]
            for row in active_qs.values("vehicle_id").annotate(last=Max("collected_at"))
        }

        vehicles = AmbulanceVehicle.objects.filter(hospital_id=hospital_id).filter(
            Q(is_active=True) | Q(id__in=per_vehicle.keys())
        ).order_by("vehicle_number")

        rows = []
        totals = {"entries": 0, "trips": 0, "total": ZERO, "cash": ZERO, "upi": ZERO, "other": ZERO}
        for v in vehicles:
            agg = per_vehicle.get(v.id, {})
            total = agg.get("total") or ZERO
            cash = agg.get("cash") or ZERO
            upi = agg.get("upi") or ZERO
            other = total - cash - upi
            expected = (v.expected_daily_amount or ZERO) * days_in_range
            last = last_seen.get(v.id)
            days_since = (today - timezone.localtime(last).date()).days if last else None
            rows.append(
                {
                    "vehicle_id": str(v.id),
                    "vehicle_number": v.vehicle_number,
                    "label": v.label,
                    "driver_name": v.driver_name,
                    "driver_phone": v.driver_phone,
                    "is_active": v.is_active,
                    "entries": agg.get("entries") or 0,
                    "trips": agg.get("trips") or 0,
                    "total": f"{total:.2f}",
                    "cash": f"{cash:.2f}",
                    "upi": f"{upi:.2f}",
                    "other": f"{other:.2f}",
                    "expected": f"{expected:.2f}",
                    "shortfall": f"{max(expected - total, ZERO):.2f}",
                    "last_collected_at": last.isoformat() if last else None,
                    "days_since_last_collection": days_since,
                }
            )
            totals["entries"] += agg.get("entries") or 0
            totals["trips"] += agg.get("trips") or 0
            totals["total"] += total
            totals["cash"] += cash
            totals["upi"] += upi
            totals["other"] += other

        return success_response(
            data={
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "vehicles": rows,
                "totals": {
                    "entries": totals["entries"],
                    "trips": totals["trips"],
                    "total": f"{totals['total']:.2f}",
                    "cash": f"{totals['cash']:.2f}",
                    "upi": f"{totals['upi']:.2f}",
                    "other": f"{totals['other']:.2f}",
                },
            }
        )


class AmbulanceCollectionFilter(django_filters.FilterSet):
    collected_at__date__gte = django_filters.DateFilter(field_name="collected_at", lookup_expr="date__gte")
    collected_at__date__lte = django_filters.DateFilter(field_name="collected_at", lookup_expr="date__lte")
    vehicle = django_filters.UUIDFilter()
    payment_mode = django_filters.CharFilter()
    collected_by = django_filters.UUIDFilter()
    status = django_filters.CharFilter()
    voided = django_filters.BooleanFilter()

    class Meta:
        model = AmbulanceCollection
        fields = []


class AmbulanceCollectionViewSet(viewsets.ModelViewSet):
    queryset = AmbulanceCollection.objects.filter(is_deleted=False).select_related(
        "vehicle", "collected_by", "voided_by"
    )
    serializer_class = AmbulanceCollectionSerializer
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]
    filter_backends = (django_filters.DjangoFilterBackend, OrderingFilter)
    filterset_class = AmbulanceCollectionFilter
    ordering_fields = ("collected_at", "amount", "created_at")
    ordering = ("-collected_at", "-created_at")
    http_method_names = ["get", "post"]
    required_permission_map = {
        "list": "ambulance.view_collection",
        "retrieve": "ambulance.view_collection",
        "create": "ambulance.create_collection",
        "void": "ambulance.void_collection",
    }

    def get_permissions(self):
        self.required_permission = self.required_permission_map.get(getattr(self, "action", None))
        return super().get_permissions()

    def get_queryset(self):
        hospital_id = self.request.user.hospital_id
        if not hospital_id:
            return AmbulanceCollection.objects.none()
        qs = super().get_queryset().filter(hospital_id=hospital_id)
        if self.action == "list" and "voided" not in self.request.query_params:
            qs = qs.filter(voided=False)
        return qs

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        search = (self.request.query_params.get("search") or "").strip()
        if not search:
            return qs
        for term in [t for t in re.split(r"\s+", search) if t]:
            normalized = normalize_vehicle_number(term)
            term_q = (
                Q(receipt_no__icontains=term)
                | Q(driver_name__icontains=term)
                | Q(patient_name__icontains=term)
                | Q(trip_from__icontains=term)
                | Q(trip_to__icontains=term)
            )
            if normalized:
                term_q |= Q(vehicle__vehicle_number__icontains=normalized)
            qs = qs.filter(term_q)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["hospital_id"] = self.request.user.hospital_id
        return ctx

    def get_object(self):
        try:
            return super().get_object()
        except Http404 as exc:
            raise NotFound() from exc

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if not request.user.hospital_id:
            return _hospital_required_response()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = serializer.save(hospital_id=request.user.hospital_id, collected_by=request.user)
        create_audit_log(
            request=request,
            hospital=row.hospital,
            module="ambulance",
            action="create_collection",
            obj=row,
            after={
                "receipt_no": row.receipt_no,
                "vehicle_number": row.vehicle.vehicle_number,
                "amount": str(row.amount),
                "payment_mode": row.payment_mode,
            },
        )
        return success_response(data=self.get_serializer(row).data, status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def void(self, request, pk=None):
        row: AmbulanceCollection = self.get_object()
        if row.voided:
            return Response(
                {"success": False, "errors": {"void": ["This receipt is already cancelled."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = VoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row.voided = True
        row.status = AmbulanceCollection.Status.CANCELLED
        row.void_reason = serializer.validated_data["void_reason"]
        row.voided_at = timezone.now()
        row.voided_by = request.user
        row.save(update_fields=["voided", "status", "void_reason", "voided_at", "voided_by", "updated_at"])
        create_audit_log(
            request=request,
            hospital=row.hospital,
            module="ambulance",
            action="void_collection",
            obj=row,
            before={"voided": False},
            after={"voided": True, "void_reason": row.void_reason, "receipt_no": row.receipt_no},
        )
        return success_response(data=self.get_serializer(row).data)
