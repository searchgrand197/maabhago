"""Head-wise collection summary for the accountant (CA) on the daily report.

Every rupee received in the period lands in exactly one head, so the heads add up to
gross received. Slip payments are split across their invoice lines in proportion to the
line totals, which keeps partial payments and discounts from inflating any head.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Sum

from apps.ambulance.models import AmbulanceCollection
from apps.billing.models import BillingInvoice
from apps.expenses.models import ExpenseTransaction
from apps.opd.models import OPDVisit
from apps.payments.models import PaymentTransaction
from apps.rentals.services import active_rent_collections, build_pending_rent_report
from apps.reports.doctor_revenue import UNCATEGORIZED, _build_quick_service_catalog, _resolve_item_category

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

HEAD_IOL = "iol"
HEAD_CAESAREAN = "caesarean"
HEAD_DELIVERY = "delivery"
HEAD_ROOM = "room_charges"
HEAD_LAB = "lab"
HEAD_OTHER = "other_services"

HEAD_LABELS = {
    HEAD_IOL: "IOL",
    HEAD_CAESAREAN: "Caesarean",
    HEAD_DELIVERY: "Delivery",
    HEAD_ROOM: "Room charges",
    HEAD_LAB: "Lab",
    HEAD_OTHER: "Other services",
}

# Matched against the lower-cased slip line description, in this order.
HEAD_PATTERNS: list[tuple[str, re.Pattern]] = [
    (HEAD_ROOM, re.compile(r"^\s*room\s*(charges?|rent)\b|\broom\s*rent\b")),
    (HEAD_IOL, re.compile(r"\biol\b")),
    (HEAD_CAESAREAN, re.compile(r"c(a)?esa?r|caes|\blscs\b|\bc[\s-]?section\b")),
    (HEAD_DELIVERY, re.compile(r"\bdel[a-z]{0,3}very\b|\bnvd\b")),
]
DELIVERY_EXCLUDE = re.compile(r"\btest\b")


def _d(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value))


def _money(value: Decimal) -> str:
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def _mode_bucket(mode: str | None) -> str:
    mode = (mode or "").strip().lower()
    if mode in {"cash", "upi", "card"}:
        return mode
    return "other"


def classify_line(description: str, category: str) -> str:
    desc = (description or "").strip().lower()
    cat = (category or "").strip().upper()
    for head, pattern in HEAD_PATTERNS:
        if not pattern.search(desc):
            continue
        if head == HEAD_DELIVERY and (cat == "LAB" or DELIVERY_EXCLUDE.search(desc)):
            continue
        return head
    if cat == "LAB":
        return HEAD_LAB
    return HEAD_OTHER


def allocate_payment(amount: Decimal, lines: list[tuple[str, Decimal]]) -> list[tuple[str, Decimal]]:
    """Split ``amount`` across ``(key, weight)`` lines pro-rata; the last line takes the rounding remainder."""
    weighted = [(key, weight) for key, weight in lines if weight > ZERO]
    if not weighted:
        return [(lines[0][0] if lines else HEAD_OTHER, amount)]
    total_weight = sum(weight for _, weight in weighted)
    out: list[tuple[str, Decimal]] = []
    allocated = ZERO
    for index, (key, weight) in enumerate(weighted):
        if index == len(weighted) - 1:
            share = amount - allocated
        else:
            share = (amount * weight / total_weight).quantize(CENT, rounding=ROUND_HALF_UP)
            allocated += share
        out.append((key, share))
    return out


def _in_range(qs, field: str, date_from: date | None, date_to: date | None):
    if date_from:
        qs = qs.filter(**{f"{field}__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field}__lte": date_to})
    return qs


def _new_head():
    return {"count": 0, "amount": ZERO}


def build_ca_summary(hospital_id, date_from: date | None, date_to: date | None, collected_by=None) -> dict:
    modes = defaultdict(lambda: ZERO)
    heads = {key: _new_head() for key in HEAD_LABELS}
    head_payment_ids: dict[str, set] = defaultdict(set)
    other_by_category: dict[str, dict] = defaultdict(_new_head)

    # OPD consultation fees
    opd_qs = OPDVisit.objects.filter(hospital_id=hospital_id).exclude(status=OPDVisit.Status.CANCELLED)
    opd_qs = _in_range(opd_qs, "visit_date", date_from, date_to)
    if collected_by:
        opd_qs = opd_qs.filter(created_by_id=collected_by)
    opd = {"count": 0, "amount": ZERO}
    for visit in opd_qs.only("amount", "payment_mode"):
        amount = _d(visit.amount)
        if amount == ZERO:
            continue
        opd["count"] += 1
        opd["amount"] += amount
        modes[_mode_bucket(visit.payment_mode)] += amount

    # Payment slips, IPD advances and refunds
    pay_qs = PaymentTransaction.objects.filter(
        hospital_id=hospital_id,
        status=PaymentTransaction.Status.SUCCESS,
        is_deleted=False,
        voided=False,
    )
    pay_qs = _in_range(pay_qs, "paid_at__date", date_from, date_to)
    if collected_by:
        pay_qs = pay_qs.filter(collected_by_id=collected_by)
    pay_qs = pay_qs.select_related("invoice").prefetch_related("invoice__items")

    catalog = _build_quick_service_catalog(hospital_id)
    advance = {"count": 0, "amount": ZERO}
    refunds = {"count": 0, "amount": ZERO}
    payments_raw_total = ZERO

    for payment in pay_qs:
        amount = _d(payment.amount)
        payments_raw_total += amount
        modes[_mode_bucket(payment.payment_mode)] += amount
        invoice_no = str(payment.invoice.invoice_no or "").upper()

        if "IPDREF" in invoice_no or amount < ZERO:
            refunds["count"] += 1
            refunds["amount"] += amount
            continue
        if "IPDADV" in invoice_no:
            advance["count"] += 1
            advance["amount"] += amount
            continue

        lines = []
        for item in payment.invoice.items.all():
            category = _resolve_item_category(item, catalog)
            head = classify_line(item.description, category)
            key = (head, category if head == HEAD_OTHER else "")
            lines.append((key, _d(item.line_total)))
        for (head, category), share in allocate_payment(amount, lines or [((HEAD_OTHER, UNCATEGORIZED), ZERO)]):
            heads[head]["amount"] += share
            head_payment_ids[head].add(payment.id)
            if head == HEAD_OTHER:
                bucket = other_by_category[category or UNCATEGORIZED]
                bucket["amount"] += share
                bucket["count"] += 1

    for head, ids in head_payment_ids.items():
        heads[head]["count"] = len(ids)

    # Room charges billed at discharge and settled from the IPD advance (not paid as a slip)
    room_qs = BillingInvoice.objects.filter(
        hospital_id=hospital_id,
        invoice_no__icontains="IPDROOM",
        status=BillingInvoice.Status.FINALIZED,
        is_deleted=False,
        voided=False,
    )
    room_qs = _in_range(room_qs, "invoice_date", date_from, date_to)
    room_adjusted = {"count": 0, "amount": ZERO}
    for total_amount, amount_paid in room_qs.values_list("total_amount", "amount_paid"):
        unpaid = _d(total_amount) - _d(amount_paid)
        if unpaid > ZERO:
            room_adjusted["count"] += 1
            room_adjusted["amount"] += unpaid

    # Ambulance
    amb_qs = AmbulanceCollection.objects.filter(
        hospital_id=hospital_id, is_deleted=False, voided=False, status=AmbulanceCollection.Status.SUCCESS
    )
    amb_qs = _in_range(amb_qs, "collected_at__date", date_from, date_to)
    if collected_by:
        amb_qs = amb_qs.filter(collected_by_id=collected_by)
    ambulance = {"count": 0, "amount": ZERO, "trips": 0}
    by_vehicle: dict[str, dict] = {}
    for row in amb_qs.select_related("vehicle"):
        amount = _d(row.amount)
        ambulance["count"] += 1
        ambulance["amount"] += amount
        ambulance["trips"] += row.trip_count or 0
        modes[_mode_bucket(row.payment_mode)] += amount
        key = row.vehicle.vehicle_number
        bucket = by_vehicle.setdefault(
            key, {"vehicle_number": key, "label": row.vehicle.label, "count": 0, "trips": 0, "amount": ZERO}
        )
        bucket["count"] += 1
        bucket["trips"] += row.trip_count or 0
        bucket["amount"] += amount

    # Shop rent
    rent_qs = _in_range(active_rent_collections(hospital_id), "collected_at__date", date_from, date_to)
    if collected_by:
        rent_qs = rent_qs.filter(collected_by_id=collected_by)
    rent = {"count": 0, "amount": ZERO}
    by_shop: dict[str, dict] = {}
    for row in rent_qs.select_related("shop"):
        amount = _d(row.amount)
        rent["count"] += 1
        rent["amount"] += amount
        modes[_mode_bucket(row.payment_mode)] += amount
        shop = row.shop
        bucket = by_shop.setdefault(
            str(shop.id),
            {
                "shop_name": shop.shop_name,
                "shop_number": shop.shop_number,
                "owner_name": shop.owner_name,
                "count": 0,
                "amount": ZERO,
            },
        )
        bucket["count"] += 1
        bucket["amount"] += amount

    pending_rent = ZERO
    pending_shops = 0
    if date_to:
        for shop in build_pending_rent_report(hospital_id, as_of=date_to)["shops"]:
            pending = _d(shop["pending"])
            if pending > ZERO:
                pending_rent += pending
                pending_shops += 1

    # Expenses paid out of the day's collection
    exp_qs = ExpenseTransaction.objects.filter(
        hospital_id=hospital_id,
        voided=False,
        status=ExpenseTransaction.Status.SUCCESS,
        source=ExpenseTransaction.Source.COLLECTION,
        is_deleted=False,
    )
    exp_qs = _in_range(exp_qs, "paid_at__date", date_from, date_to)
    if collected_by:
        exp_qs = exp_qs.filter(recorded_by_id=collected_by)
    exp_agg = exp_qs.aggregate(total=Sum("total_amount"), count=Count("id"))
    expenses_total = _d(exp_agg["total"])

    slip_heads_total = sum((h["amount"] for h in heads.values()), ZERO)
    gross = opd["amount"] + slip_heads_total + advance["amount"] + refunds["amount"] + ambulance["amount"] + rent["amount"]
    source_total = opd["amount"] + payments_raw_total + ambulance["amount"] + rent["amount"]
    difference = gross - source_total

    def head_row(key, label, data, **extra):
        return {"key": key, "label": label, "count": data["count"], "amount": _money(data["amount"]), **extra}

    return {
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "heads": [
            head_row(HEAD_IOL, "IOL", heads[HEAD_IOL]),
            head_row(HEAD_CAESAREAN, "Caesarean", heads[HEAD_CAESAREAN]),
            head_row(HEAD_DELIVERY, "Delivery", heads[HEAD_DELIVERY]),
            head_row(HEAD_ROOM, "Room charges (collected)", heads[HEAD_ROOM]),
            head_row("ipd_advance", "IPD advance received", advance),
            head_row("ambulance", "Ambulance", ambulance, trips=ambulance["trips"]),
            head_row("rent", "Shop rent", rent),
            head_row("opd", "OPD fees", opd),
            head_row(HEAD_LAB, "Lab", heads[HEAD_LAB]),
            head_row(HEAD_OTHER, "Other services", heads[HEAD_OTHER]),
            head_row("refunds", "Refunds", refunds),
        ],
        "ipd": {
            "advance_received": _money(advance["amount"]),
            "advance_count": advance["count"],
            "room_adjusted": _money(room_adjusted["amount"]),
            "room_adjusted_count": room_adjusted["count"],
            "room_collected": _money(heads[HEAD_ROOM]["amount"]),
            "room_total": _money(room_adjusted["amount"] + heads[HEAD_ROOM]["amount"]),
            "net_ipd": _money(advance["amount"] - room_adjusted["amount"]),
        },
        "other_services_by_category": [
            {"category": category, "count": data["count"], "amount": _money(data["amount"])}
            for category, data in sorted(other_by_category.items(), key=lambda item: -item[1]["amount"])
        ],
        "ambulance_by_vehicle": [
            {**row, "amount": _money(row["amount"])}
            for row in sorted(by_vehicle.values(), key=lambda r: -r["amount"])
        ],
        "rent_by_shop": [
            {**row, "amount": _money(row["amount"])}
            for row in sorted(by_shop.values(), key=lambda r: -r["amount"])
        ],
        "pending_rent": {"amount": _money(pending_rent), "shops": pending_shops},
        "modes": {key: _money(modes[key]) for key in ("cash", "upi", "card", "other")},
        "gross_received": _money(gross),
        "expenses_total": _money(expenses_total),
        "expenses_count": exp_agg["count"] or 0,
        "net_after_expenses": _money(gross - expenses_total),
        "reconciliation": {
            "source_total": _money(source_total),
            "difference": _money(difference),
            "reconciled": abs(difference) < CENT,
        },
    }
