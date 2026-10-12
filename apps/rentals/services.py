from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Max, Sum

from apps.rentals.models import RentCollection, RentShop

ZERO = Decimal("0.00")


def month_start(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, n: int) -> date:
    index = d.month - 1 + n
    return date(d.year + index // 12, index % 12 + 1, 1)


def active_rent_collections(hospital_id):
    return RentCollection.objects.filter(
        hospital_id=hospital_id,
        is_deleted=False,
        voided=False,
        status=RentCollection.Status.SUCCESS,
    )


def paid_by_shop_month(hospital_id, shop_ids) -> dict:
    paid: dict = defaultdict(dict)
    rows = (
        active_rent_collections(hospital_id)
        .filter(shop_id__in=shop_ids)
        .values("shop_id", "rent_month")
        .annotate(total=Sum("amount"))
    )
    for row in rows:
        paid[row["shop_id"]][row["rent_month"]] = row["total"] or ZERO
    return paid


def build_shop_ledger(shop: RentShop, paid_by_month: dict, as_of: date) -> dict:
    """Month-by-month rent position from the agreement start up to ``as_of``.

    Overpayment in one month offsets shortfalls in others, so ``pending`` is the
    net balance; payments for months after ``as_of`` are reported as advance.
    """
    current = month_start(as_of)
    rent = shop.monthly_rent or ZERO
    months = []
    total_expected = ZERO
    total_paid = ZERO

    m = month_start(shop.rent_start_date)
    while m <= current:
        paid = paid_by_month.get(m, ZERO)
        balance = max(rent - paid, ZERO)
        due_date = m.replace(day=min(max(shop.due_day or 1, 1), 28))
        if balance == ZERO:
            state = "paid"
        elif paid > ZERO:
            state = "partial"
        else:
            state = "unpaid"
        months.append(
            {
                "month": m.isoformat(),
                "due_date": due_date.isoformat(),
                "expected": f"{rent:.2f}",
                "paid": f"{paid:.2f}",
                "balance": f"{balance:.2f}",
                "status": state,
                "overdue": balance > ZERO and as_of > due_date,
            }
        )
        total_expected += rent
        total_paid += paid
        m = add_months(m, 1)

    advance = ZERO
    for month, paid in sorted(paid_by_month.items()):
        if month > current:
            advance += paid
            months.append(
                {
                    "month": month.isoformat(),
                    "due_date": month.replace(day=min(max(shop.due_day or 1, 1), 28)).isoformat(),
                    "expected": f"{rent:.2f}",
                    "paid": f"{paid:.2f}",
                    "balance": f"{max(rent - paid, ZERO):.2f}",
                    "status": "advance",
                    "overdue": False,
                }
            )

    pending = max(total_expected - total_paid, ZERO)
    unpaid = [row for row in months if row["status"] in {"unpaid", "partial"}]
    return {
        "months": months,
        "total_expected": f"{total_expected:.2f}",
        "total_paid": f"{total_paid:.2f}",
        "advance_paid": f"{advance:.2f}",
        "pending": f"{pending:.2f}",
        "unpaid_months": [row["month"] for row in unpaid],
        "overdue_months": sum(1 for row in unpaid if row["overdue"]),
        "oldest_unpaid_month": unpaid[0]["month"] if unpaid else None,
        "oldest_unpaid_balance": unpaid[0]["balance"] if unpaid else "0.00",
    }


def shop_payload(shop: RentShop) -> dict:
    return {
        "id": str(shop.id),
        "shop_name": shop.shop_name,
        "shop_number": shop.shop_number,
        "owner_name": shop.owner_name,
        "owner_phone": shop.owner_phone,
        "monthly_rent": f"{shop.monthly_rent:.2f}",
        "due_day": shop.due_day,
        "rent_start_date": shop.rent_start_date.isoformat(),
        "is_active": shop.is_active,
    }


def build_pending_rent_report(hospital_id, as_of: date, shop_id=None, include_inactive=False) -> dict:
    shops = RentShop.objects.filter(hospital_id=hospital_id)
    if not include_inactive:
        shops = shops.filter(is_active=True)
    if shop_id:
        shops = shops.filter(id=shop_id)
    shops = list(shops.order_by("shop_name", "shop_number"))
    shop_ids = [s.id for s in shops]

    paid = paid_by_shop_month(hospital_id, shop_ids)
    last_payment = {
        row["shop_id"]: row["last"]
        for row in active_rent_collections(hospital_id)
        .filter(shop_id__in=shop_ids)
        .values("shop_id")
        .annotate(last=Max("collected_at"))
    }

    rows = []
    totals = {"expected": ZERO, "paid": ZERO, "pending": ZERO}
    for shop in shops:
        ledger = build_shop_ledger(shop, paid.get(shop.id, {}), as_of)
        last = last_payment.get(shop.id)
        rows.append(
            {
                **shop_payload(shop),
                **{k: v for k, v in ledger.items() if k != "months"},
                "last_paid_at": last.isoformat() if last else None,
            }
        )
        totals["expected"] += Decimal(ledger["total_expected"])
        totals["paid"] += Decimal(ledger["total_paid"])
        totals["pending"] += Decimal(ledger["pending"])

    return {
        "as_of": as_of.isoformat(),
        "shops": rows,
        "totals": {
            "shops": len(rows),
            "shops_with_pending": sum(1 for r in rows if Decimal(r["pending"]) > ZERO),
            "expected": f"{totals['expected']:.2f}",
            "paid": f"{totals['paid']:.2f}",
            "pending": f"{totals['pending']:.2f}",
        },
    }
