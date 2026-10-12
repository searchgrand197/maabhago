from __future__ import annotations

import re

from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters import rest_framework as django_filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from apps.ambulance.serializers import VoidSerializer
from apps.auditlogs.services import create_audit_log
from apps.rentals.models import RentCollection, RentShop
from apps.rentals.serializers import MonthField, RentCollectionSerializer, RentShopSerializer
from apps.rentals.services import (
    build_pending_rent_report,
    build_shop_ledger,
    paid_by_shop_month,
    shop_payload,
)
from apps.roles_permissions.permissions import HasRequiredPermission
from apps.shared.response import success_response


def _hospital_required_response():
    return Response(
        {"success": False, "errors": {"hospital": ["User is not linked to a hospital."]}},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _as_of_param(request):
    return parse_date(request.query_params.get("as_of") or "") or timezone.localdate()


class RentShopViewSet(viewsets.ModelViewSet):
    queryset = RentShop.objects.all()
    serializer_class = RentShopSerializer
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]
    http_method_names = ["get", "post", "patch"]
    pagination_class = None
    required_permission_map = {
        "list": "rentals.view_collection",
        "retrieve": "rentals.view_collection",
        "ledger": "rentals.view_collection",
        "pending": "rentals.view_collection",
        "create": "rentals.manage_shop",
        "partial_update": "rentals.manage_shop",
    }

    def get_permissions(self):
        self.required_permission = self.required_permission_map.get(getattr(self, "action", None))
        return super().get_permissions()

    def get_queryset(self):
        hospital_id = self.request.user.hospital_id
        if not hospital_id:
            return RentShop.objects.none()
        qs = RentShop.objects.filter(hospital_id=hospital_id)
        active = self.request.query_params.get("is_active")
        if active in {"true", "false"}:
            qs = qs.filter(is_active=active == "true")
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(shop_name__icontains=search)
                | Q(shop_number__icontains=search)
                | Q(owner_name__icontains=search)
                | Q(owner_phone__icontains=search)
            )
        return qs.order_by("-is_active", "shop_name", "shop_number")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["hospital_id"] = self.request.user.hospital_id
        return ctx

    def get_object(self):
        try:
            return super().get_object()
        except Http404 as exc:
            raise NotFound() from exc

    def list(self, request, *args, **kwargs):
        return success_response(data=self.get_serializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        if not request.user.hospital_id:
            return _hospital_required_response()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = serializer.save(hospital_id=request.user.hospital_id)
        create_audit_log(
            request=request,
            hospital=shop.hospital,
            module="rentals",
            action="create_shop",
            obj=shop,
            after={"shop_name": shop.shop_name, "owner_name": shop.owner_name, "monthly_rent": str(shop.monthly_rent)},
        )
        return success_response(data=self.get_serializer(shop).data, status_code=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        shop = self.get_object()
        serializer = self.get_serializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changed = list(serializer.validated_data.keys())
        before = {k: str(getattr(shop, k)) for k in changed}
        shop = serializer.save()
        create_audit_log(
            request=request,
            hospital=shop.hospital,
            module="rentals",
            action="update_shop",
            obj=shop,
            before=before,
            after={k: str(getattr(shop, k)) for k in changed},
        )
        return success_response(data=self.get_serializer(shop).data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        hospital_id = request.user.hospital_id
        if not hospital_id:
            return _hospital_required_response()
        include_inactive = request.query_params.get("include_inactive") == "true"
        return success_response(
            data=build_pending_rent_report(hospital_id, _as_of_param(request), include_inactive=include_inactive)
        )

    @action(detail=True, methods=["get"])
    def ledger(self, request, pk=None):
        shop = self.get_object()
        paid = paid_by_shop_month(shop.hospital_id, [shop.id]).get(shop.id, {})
        ledger = build_shop_ledger(shop, paid, _as_of_param(request))
        return success_response(data={"shop": shop_payload(shop), **ledger})


class RentCollectionFilter(django_filters.FilterSet):
    collected_at__date__gte = django_filters.DateFilter(field_name="collected_at", lookup_expr="date__gte")
    collected_at__date__lte = django_filters.DateFilter(field_name="collected_at", lookup_expr="date__lte")
    shop = django_filters.UUIDFilter()
    rent_month = django_filters.CharFilter(method="filter_rent_month")
    payment_mode = django_filters.CharFilter()
    collected_by = django_filters.UUIDFilter()
    status = django_filters.CharFilter()
    voided = django_filters.BooleanFilter()

    class Meta:
        model = RentCollection
        fields = []

    def filter_rent_month(self, queryset, name, value):
        try:
            month = MonthField().to_internal_value(value)
        except Exception:
            return queryset.none()
        return queryset.filter(rent_month=month)


class RentCollectionViewSet(viewsets.ModelViewSet):
    queryset = RentCollection.objects.filter(is_deleted=False).select_related("shop", "collected_by", "voided_by")
    serializer_class = RentCollectionSerializer
    permission_classes = [permissions.IsAuthenticated, HasRequiredPermission]
    filter_backends = (django_filters.DjangoFilterBackend, OrderingFilter)
    filterset_class = RentCollectionFilter
    ordering_fields = ("collected_at", "amount", "rent_month", "created_at")
    ordering = ("-collected_at", "-created_at")
    http_method_names = ["get", "post"]
    required_permission_map = {
        "list": "rentals.view_collection",
        "retrieve": "rentals.view_collection",
        "create": "rentals.create_collection",
        "void": "rentals.void_collection",
    }

    def get_permissions(self):
        self.required_permission = self.required_permission_map.get(getattr(self, "action", None))
        return super().get_permissions()

    def get_queryset(self):
        hospital_id = self.request.user.hospital_id
        if not hospital_id:
            return RentCollection.objects.none()
        qs = super().get_queryset().filter(hospital_id=hospital_id)
        if self.action == "list" and "voided" not in self.request.query_params:
            qs = qs.filter(voided=False)
        return qs

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        search = (self.request.query_params.get("search") or "").strip()
        for term in [t for t in re.split(r"\s+", search) if t]:
            qs = qs.filter(
                Q(receipt_no__icontains=term)
                | Q(shop__shop_name__icontains=term)
                | Q(shop__shop_number__icontains=term)
                | Q(shop__owner_name__icontains=term)
                | Q(paid_by__icontains=term)
            )
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
            module="rentals",
            action="create_collection",
            obj=row,
            after={
                "receipt_no": row.receipt_no,
                "shop_name": row.shop.shop_name,
                "rent_month": row.rent_month.isoformat(),
                "amount": str(row.amount),
                "payment_mode": row.payment_mode,
            },
        )
        return success_response(data=self.get_serializer(row).data, status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def void(self, request, pk=None):
        row: RentCollection = self.get_object()
        if row.voided:
            return Response(
                {"success": False, "errors": {"void": ["This receipt is already cancelled."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = VoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row.voided = True
        row.status = RentCollection.Status.CANCELLED
        row.void_reason = serializer.validated_data["void_reason"]
        row.voided_at = timezone.now()
        row.voided_by = request.user
        row.save(update_fields=["voided", "status", "void_reason", "voided_at", "voided_by", "updated_at"])
        create_audit_log(
            request=request,
            hospital=row.hospital,
            module="rentals",
            action="void_collection",
            obj=row,
            before={"voided": False},
            after={"voided": True, "void_reason": row.void_reason, "receipt_no": row.receipt_no},
        )
        return success_response(data=self.get_serializer(row).data)
