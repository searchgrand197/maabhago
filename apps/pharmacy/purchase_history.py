"""Purchase history list/detail helpers (Marg-style dashboard)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.inventory.models import StockLedger
from apps.pharmacy.models import PharmacyPurchaseChallan, PharmacyPurchaseChallanLine


def _supplier_label(ch: PharmacyPurchaseChallan) -> str:
    if ch.supplier_id and ch.supplier:
        return ch.supplier.name or "—"
    if ch.supplier_name_snapshot:
        return ch.supplier_name_snapshot
    return "Unknown supplier"


def _gst_type_label(ch: PharmacyPurchaseChallan) -> str:
    if not ch.gst_enabled:
        return "NON_GST"
    has_tax = ch.lines.filter(gst_amount__gt=0).exists()
    return "GST" if has_tax else "NON_GST"


def _fmt_qty(d: Decimal) -> str:
    d = (d or Decimal("0")).normalize()
    try:
        i = int(d)
        if Decimal(i) == d:
            return str(i)
    except (ValueError, OverflowError):
        pass
    s = format(d, "f").rstrip("0").rstrip(".")
    return s or "0"


def _qty_display(ch: PharmacyPurchaseChallan) -> str:
    strips = ch.total_strips or Decimal("0")
    tabs = ch.total_extra_tablets or Decimal("0")
    parts: list[str] = []
    if strips > 0:
        parts.append(f"{_fmt_qty(strips)} strips")
    if tabs > 0:
        parts.append(f"{_fmt_qty(tabs)} tablets")
    if not parts:
        b = ch.total_base_qty or Decimal("0")
        if b > 0:
            return f"{_fmt_qty(b)} units"
        return "—"
    return " + ".join(parts)


def _challan_status(ch: PharmacyPurchaseChallan, batch_ids: list[Any], today: date) -> str:
    for ln in ch.lines.all():
        b = ln.batch
        exp = (b.expiry_date if b else None) or ln.snapshot_expiry_date
        if exp and exp < today:
            return "expired"
    if not batch_ids:
        return "completed"
    if StockLedger.objects.filter(
        batch_id__in=batch_ids,
        reason=StockLedger.Reason.ADJUST,
        qty_change__lt=0,
    ).exists():
        return "partial_return"
    if StockLedger.objects.filter(
        batch_id__in=batch_ids,
        reference_type="pharmacy_purchase_return",
    ).exists():
        return "partial_return"
    return "completed"


def build_tile_dict(ch: PharmacyPurchaseChallan, today: date | None = None) -> dict[str, Any]:
    today = today or timezone.now().date()
    batch_ids = [bid for bid in ch.lines.values_list("batch_id", flat=True) if bid]
    return {
        "id": str(ch.id),
        "challan_no": ch.challan_no or "—",
        "supplier_name": _supplier_label(ch),
        "date": ch.purchase_date.isoformat(),
        "total_items": ch.total_items,
        "total_qty_strips": str(ch.total_strips),
        "total_qty_tablets": str(ch.total_extra_tablets),
        "total_qty_display": _qty_display(ch),
        "total_amount": str(ch.total_amount),
        "gst_type": _gst_type_label(ch),
        "status": _challan_status(ch, batch_ids, today),
        "payment_type": ch.payment_type or "cash",
    }


def filter_challan_queryset(
    qs,
    *,
    search: str = "",
    supplier_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    gst: str = "all",
):
    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)
    if date_from:
        qs = qs.filter(purchase_date__gte=date_from)
    if date_to:
        qs = qs.filter(purchase_date__lte=date_to)
    if gst == "gst":
        qs = qs.filter(gst_enabled=True)
    elif gst == "non":
        qs = qs.filter(gst_enabled=False)

    q = (search or "").strip()
    if q:
        qs = qs.filter(
            Q(challan_no__icontains=q)
            | Q(supplier_name_snapshot__icontains=q)
            | Q(supplier__name__icontains=q)
            | Q(lines__medicine__name__icontains=q)
            | Q(lines__batch__batch_no__icontains=q)
            | Q(lines__snapshot_batch_no__icontains=q)
        ).distinct()
    return qs


def list_purchase_history(*, hospital_id, limit: int = 20, offset: int = 0, **filters) -> tuple[list[dict], int]:
    qs = (
        PharmacyPurchaseChallan.objects.filter(hospital_id=hospital_id)
        .select_related("supplier")
        .prefetch_related("lines__batch")
        .order_by("-purchase_date", "-created_at")
    )
    qs = filter_challan_queryset(qs, **filters)
    total = qs.count()
    today = timezone.now().date()
    rows = []
    for ch in qs[offset : offset + limit]:
        rows.append(build_tile_dict(ch, today))
    return rows, total


def detail_purchase_history(*, hospital_id, pk) -> dict[str, Any] | None:
    ch = (
        PharmacyPurchaseChallan.objects.filter(hospital_id=hospital_id, pk=pk)
        .select_related("supplier")
        .prefetch_related("lines__medicine", "lines__batch")
        .first()
    )
    if not ch:
        return None

    today = timezone.now().date()
    near_expiry = today + timedelta(days=90)
    lines_out: list[dict[str, Any]] = []
    batch_ids: list[Any] = []

    for ln in ch.lines.all().order_by("created_at"):
        if ln.batch_id:
            batch_ids.append(ln.batch_id)
        b = ln.batch
        exp = (b.expiry_date if b else None) or ln.snapshot_expiry_date
        expiring_soon = bool(exp and today <= exp <= near_expiry)
        expired = bool(exp and exp < today)

        prev_line = (
            PharmacyPurchaseChallanLine.objects.filter(
                medicine_id=ln.medicine_id,
                challan__hospital_id=hospital_id,
            )
            .filter(
                Q(challan__purchase_date__lt=ch.purchase_date)
                | Q(challan__purchase_date=ch.purchase_date, challan__created_at__lt=ch.created_at)
            )
            .exclude(challan_id=ch.id)
            .select_related("challan", "challan__supplier")
            .order_by("-challan__purchase_date", "-challan__created_at", "-created_at")
            .first()
        )
        last_rate = str(prev_line.purchase_rate) if prev_line else None
        prev_supplier = None
        if prev_line and prev_line.challan:
            prev_supplier = _supplier_label(prev_line.challan)

        lines_out.append(
            {
                "id": str(ln.id),
                "medicine_id": str(ln.medicine_id),
                "medicine_name": ln.medicine.name,
                "batch_no": (ln.batch.batch_no if ln.batch_id else None) or ln.snapshot_batch_no or "—",
                "expiry_date": exp.isoformat() if exp else None,
                "expiring_within_90_days": expiring_soon,
                "expired": expired,
                "pack_quantity": str(ln.pack_quantity),
                "base_qty": str(ln.base_qty),
                "conversion": str(ln.conversion),
                "rate_type": ln.rate_type,
                "purchase_rate": str(ln.purchase_rate),
                "mrp": str(ln.mrp),
                "discount": str(ln.discount),
                "gst_type": ln.gst_type,
                "gst_percent": str(ln.gst_percent),
                "no_gst": ln.no_gst,
                "taxable_amount": str(ln.taxable_amount),
                "gst_amount": str(ln.gst_amount),
                "final_amount": str(ln.final_amount),
                "last_purchase_rate": last_rate,
                "previous_supplier_name": prev_supplier,
            }
        )

    ret_qs = StockLedger.objects.filter(batch_id__in=batch_ids).filter(
        Q(reason=StockLedger.Reason.ADJUST, qty_change__lt=0) | Q(reference_type="pharmacy_purchase_return")
    ).order_by("-created_at")[:100]
    return_movements = [
        {
            "id": str(r.id),
            "batch_id": str(r.batch_id),
            "qty_change": str(r.qty_change),
            "reason": r.reason,
            "reference_type": r.reference_type,
            "reference_id": r.reference_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in ret_qs
    ]

    return {
        **build_tile_dict(ch, today),
        "gst_enabled": ch.gst_enabled,
        "total_taxable": str(ch.total_taxable),
        "lines": lines_out,
        "return_movements": return_movements,
    }
