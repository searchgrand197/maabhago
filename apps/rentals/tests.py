from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.rentals.models import RentShop
from apps.rentals.services import add_months, build_shop_ledger
from apps.shared.models import Hospital

User = get_user_model()


def _data(response):
    return response.data.get("data", response.data)


class RentLedgerTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Rent Hospital", slug="rent-hospital")
        self.shop = RentShop(
            hospital=self.hospital,
            shop_name="Medical Store",
            owner_name="Suresh",
            monthly_rent=Decimal("5000.00"),
            due_day=5,
            rent_start_date=date(2026, 7, 15),
        )

    def test_add_months_wraps_year(self):
        self.assertEqual(add_months(date(2026, 11, 1), 3), date(2027, 2, 1))

    def test_ledger_statuses_and_pending(self):
        paid = {
            date(2026, 7, 1): Decimal("5000.00"),
            date(2026, 8, 1): Decimal("2000.00"),
            date(2026, 12, 1): Decimal("5000.00"),
        }
        ledger = build_shop_ledger(self.shop, paid, as_of=date(2026, 10, 12))
        statuses = [(m["month"], m["status"], m["overdue"]) for m in ledger["months"]]
        self.assertEqual(
            statuses,
            [
                ("2026-07-01", "paid", False),
                ("2026-08-01", "partial", True),
                ("2026-09-01", "unpaid", True),
                ("2026-10-01", "unpaid", True),
                ("2026-12-01", "advance", False),
            ],
        )
        self.assertEqual(ledger["total_expected"], "20000.00")
        self.assertEqual(ledger["pending"], "13000.00")
        self.assertEqual(ledger["advance_paid"], "5000.00")
        self.assertEqual(ledger["overdue_months"], 3)
        self.assertEqual(ledger["oldest_unpaid_month"], "2026-08-01")

    def test_current_month_not_overdue_before_due_day(self):
        ledger = build_shop_ledger(self.shop, {}, as_of=date(2026, 7, 3))
        self.assertFalse(ledger["months"][0]["overdue"])


class RentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="Rent Api Hospital", slug="rent-api-hospital")
        self.other = Hospital.objects.create(name="Other Rent Hospital", slug="other-rent-hospital")
        self.user = User.objects.create_user(email="rent@test.com", password="x", hospital=self.hospital)
        self.client.force_authenticate(self.user)
        res = self.client.post(
            "/api/v1/rent/shops/",
            {
                "shop_name": "Canteen",
                "shop_number": "G-2",
                "owner_name": "Mahesh",
                "monthly_rent": "3000.00",
                "rent_start_date": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.shop_id = _data(res)["id"]

    def test_duplicate_shop_rejected(self):
        res = self.client.post(
            "/api/v1/rent/shops/",
            {
                "shop_name": "canteen",
                "shop_number": "g-2",
                "owner_name": "Other",
                "monthly_rent": "100",
                "rent_start_date": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_collect_rent_and_pending(self):
        res = self.client.post(
            "/api/v1/rent/collections/",
            {"shop": self.shop_id, "rent_month": "2026-09", "amount": "3000.00", "payment_mode": "upi"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        data = _data(res)
        self.assertEqual(data["rent_month"], "2026-09")
        self.assertEqual(data["paid_by"], "Mahesh")
        self.assertTrue(data["receipt_no"].startswith("RENT-"))

        pending = _data(self.client.get("/api/v1/rent/shops/pending/?as_of=2026-10-12"))
        row = pending["shops"][0]
        self.assertEqual(row["pending"], "3000.00")
        self.assertEqual(row["unpaid_months"], ["2026-10-01"])
        self.assertEqual(pending["totals"]["shops_with_pending"], 1)

    def test_rent_month_before_start_rejected(self):
        res = self.client.post(
            "/api/v1/rent/collections/",
            {"shop": self.shop_id, "rent_month": "2026-08", "amount": "3000.00", "payment_mode": "cash"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_other_hospital_cannot_see_shop(self):
        other_user = User.objects.create_user(email="o@test.com", password="x", hospital=self.other)
        self.client.force_authenticate(other_user)
        self.assertEqual(self.client.get(f"/api/v1/rent/shops/{self.shop_id}/ledger/").status_code, 404)
        res = self.client.post(
            "/api/v1/rent/collections/",
            {"shop": self.shop_id, "rent_month": "2026-09", "amount": "10", "payment_mode": "cash"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
