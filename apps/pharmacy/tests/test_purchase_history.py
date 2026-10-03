from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.inventory.models import Medicine, Unit
from apps.pharmacy.models import PharmacyPurchaseChallan, PharmacySupplier
from apps.pharmacy.purchase_challan import process_purchase_challan
from apps.pharmacy.purchase_history import build_tile_dict, list_purchase_history
from apps.shared.models import Hospital

User = get_user_model()


class PurchaseHistoryTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="H2", slug="h2")
        self.unit = Unit.objects.create(hospital=self.hospital, code="TAB", name="Tablet")
        self.user = User.objects.create_user(email="h@test.com", password="x", hospital=self.hospital)
        self.med = Medicine.objects.create(
            hospital=self.hospital,
            sku="M1",
            name="Amox",
            unit=self.unit,
            pack_info="10",
        )

    def _post_one(self, batch_no="BX", invoice_no="INV-X"):
        rf = RequestFactory()
        request = rf.post("/api/v1/pharmacy/purchase-challan/")
        request.user = self.user
        line = {
            "medicine": str(self.med.id),
            "batch_no": batch_no,
            "expiry_date": timezone.now().date().replace(year=timezone.now().year + 1),
            "quantity": Decimal("2"),
            "pack_type": "strip",
            "conversion": Decimal("10"),
            "purchase_rate": Decimal("100"),
            "mrp": Decimal("150"),
            "gst_type": "exclusive",
            "gst_percent": Decimal("5"),
            "discount": Decimal("0"),
            "skip_gst": False,
        }
        return process_purchase_challan(
            request=request,
            hospital=self.hospital,
            lines=[line],
            invoice_no=invoice_no,
            gst_enabled=True,
        )

    def test_list_and_tile_after_post(self):
        self._post_one()
        rows, total = list_purchase_history(hospital_id=self.hospital.id, limit=20, offset=0)
        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_items"], 1)
        self.assertIn("strips", rows[0]["total_qty_display"].lower())

    def test_search_by_medicine_name(self):
        self._post_one()
        rows, total = list_purchase_history(
            hospital_id=self.hospital.id,
            limit=20,
            offset=0,
            search="Amox",
        )
        self.assertEqual(total, 1)

    def test_gst_filter_non(self):
        self._post_one()
        rf = RequestFactory()
        req2 = rf.post("/api/v1/pharmacy/purchase-challan/")
        req2.user = self.user
        process_purchase_challan(
            request=req2,
            hospital=self.hospital,
            lines=[
                {
                    "medicine": str(self.med.id),
                    "batch_no": "B2",
                    "expiry_date": timezone.now().date().replace(year=timezone.now().year + 1),
                    "quantity": Decimal("1"),
                    "pack_type": "strip",
                    "conversion": Decimal("10"),
                    "purchase_rate": Decimal("50"),
                    "mrp": Decimal("80"),
                    "gst_type": "exclusive",
                    "discount": Decimal("0"),
                    "skip_gst": True,
                }
            ],
            gst_enabled=False,
        )
        rows_all, t_all = list_purchase_history(hospital_id=self.hospital.id, limit=20, offset=0, gst="all")
        self.assertEqual(t_all, 2)
        rows_non, t_non = list_purchase_history(hospital_id=self.hospital.id, limit=20, offset=0, gst="non")
        self.assertEqual(t_non, 1)

    def test_unknown_supplier_snapshot(self):
        sup = PharmacySupplier.objects.create(hospital=self.hospital, name="Gone Co")
        rf = RequestFactory()
        request = rf.post("/")
        request.user = self.user
        line = {
            "medicine": str(self.med.id),
            "batch_no": "BZ",
            "expiry_date": timezone.now().date().replace(year=timezone.now().year + 1),
            "quantity": Decimal("1"),
            "pack_type": "strip",
            "conversion": Decimal("10"),
            "purchase_rate": Decimal("50"),
            "mrp": Decimal("80"),
            "gst_type": "exclusive",
            "gst_percent": Decimal("5"),
            "discount": Decimal("0"),
            "skip_gst": False,
        }
        process_purchase_challan(
            request=request,
            hospital=self.hospital,
            lines=[line],
            supplier_id=sup.id,
            invoice_no="Z1",
        )
        sup.delete()
        ch = PharmacyPurchaseChallan.objects.get(challan_no="Z1")
        tile = build_tile_dict(ch)
        self.assertEqual(tile["supplier_name"], "Gone Co")
