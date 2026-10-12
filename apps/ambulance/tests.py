from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ambulance.models import AmbulanceVehicle
from apps.shared.models import Hospital

User = get_user_model()


def _data(response):
    return response.data.get("data", response.data)


class AmbulanceCollectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="Amb Hospital", slug="amb-hospital")
        self.user = User.objects.create_user(email="amb@test.com", password="x", hospital=self.hospital)
        self.client.force_authenticate(self.user)
        self.vehicle = AmbulanceVehicle.objects.create(
            hospital=self.hospital,
            vehicle_number="hr 31 ab-1234",
            driver_name="Ramesh",
            driver_phone="9999999999",
            expected_daily_amount=Decimal("1000.00"),
        )

    def _collect(self, **overrides):
        payload = {"vehicle": str(self.vehicle.id), "amount": "700.00", "payment_mode": "cash", "trip_count": 2}
        payload.update(overrides)
        return self.client.post("/api/v1/ambulance/collections/", payload, format="json")

    def test_vehicle_number_is_normalized_and_unique(self):
        self.assertEqual(self.vehicle.vehicle_number, "HR31AB1234")
        res = self.client.post("/api/v1/ambulance/vehicles/", {"vehicle_number": "HR-31-AB 1234"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_collect_defaults_driver_and_generates_receipt(self):
        res = self._collect()
        self.assertEqual(res.status_code, 201)
        data = _data(res)
        self.assertTrue(data["receipt_no"].startswith(f"AMB-{timezone.now().year}-"))
        self.assertEqual(data["driver_name"], "Ramesh")
        self.assertEqual(data["vehicle_number"], "HR31AB1234")

    def test_rejects_non_positive_amount(self):
        self.assertEqual(self._collect(amount="0").status_code, 400)

    def test_summary_tracks_vehicle_and_excludes_voided(self):
        self._collect()
        voided = _data(self._collect(amount="200.00", payment_mode="upi"))
        void_res = self.client.post(
            f"/api/v1/ambulance/collections/{voided['id']}/void/", {"void_reason": "Wrong entry"}, format="json"
        )
        self.assertEqual(void_res.status_code, 200)

        res = self.client.get("/api/v1/ambulance/vehicles/summary/")
        self.assertEqual(res.status_code, 200)
        row = _data(res)["vehicles"][0]
        self.assertEqual(row["total"], "700.00")
        self.assertEqual(row["trips"], 2)
        self.assertEqual(row["cash"], "700.00")
        self.assertEqual(row["shortfall"], "300.00")
        self.assertEqual(row["days_since_last_collection"], 0)

    def test_collection_summary_includes_ambulance_in_net(self):
        self._collect()
        today = timezone.localdate().isoformat()
        res = self.client.get(f"/api/v1/reports/collection-summary/?date_from={today}&date_to={today}")
        payload = _data(res)
        self.assertEqual(payload["ambulance_total"], "700.00")
        self.assertEqual(Decimal(payload["net_total"]), Decimal(payload["grand_total"]) + Decimal("700.00"))

    def test_cash_in_hand_includes_ambulance_cash(self):
        self._collect()
        res = self.client.get("/api/v1/handovers/balance/")
        self.assertEqual(res.status_code, 200)
        payload = _data(res)
        self.assertEqual(Decimal(payload["collection"]["cash_total"]), Decimal("700.00"))
        self.assertTrue(any(e["entry_type"] == "ambulance" for e in payload["collection_entries"]))
