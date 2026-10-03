from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.inventory.models import Medicine, StockLedger, Unit
from apps.pharmacy.models import PharmacyPurchaseChallan, PharmacyPurchaseChallanLine, PharmacySupplier
from apps.pharmacy.purchase_challan import process_purchase_challan
from apps.shared.models import Hospital


User = get_user_model()


class PurchaseToStockTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Test Hosp", slug="test-hosp")
        self.unit = Unit.objects.create(hospital=self.hospital, code="TAB", name="Tablet")
        self.user = User.objects.create_user(email="p@test.com", password="x", hospital=self.hospital)
        self.med = Medicine.objects.create(
            hospital=self.hospital,
            sku="T001",
            name="Test Med",
            unit=self.unit,
            pack_info="10 tabs",
        )

    def test_purchase_creates_stock(self):
        rf = RequestFactory()
        request = rf.post("/api/v1/pharmacy/purchase-challan/")
        request.user = self.user
        line = {
            "medicine": str(self.med.id),
            "batch_no": "B1",
            "expiry_date": timezone.now().date().replace(year=timezone.now().year + 1),
            "quantity": Decimal("2"),
            "pack_type": "strip",
            "conversion": Decimal("10"),
            "purchase_rate": Decimal("100"),
            "mrp": Decimal("150"),
            "gst_type": "exclusive",
            "gst_percent": Decimal("12"),
            "discount": Decimal("0"),
            "skip_gst": False,
        }
        out = process_purchase_challan(request=request, hospital=self.hospital, lines=[line])
        self.assertEqual(len(out), 1)
        batch_id = out[0]["batch_id"]
        total = StockLedger.objects.filter(batch_id=batch_id).aggregate(s=Sum("qty_change"))["s"]
        self.assertEqual(total, Decimal("20"))
        ch = PharmacyPurchaseChallan.objects.get(hospital=self.hospital)
        self.assertEqual(ch.total_items, 1)
        self.assertEqual(PharmacyPurchaseChallanLine.objects.filter(challan=ch).count(), 1)
        le = StockLedger.objects.get(batch_id=batch_id, reason=StockLedger.Reason.STOCK_IN)
        self.assertEqual(le.reference_id, str(ch.id))

    def test_purchase_base_quantity_tablets(self):
        """quantity_basis=base: qty is total tablets; conversion ignored for stock."""
        rf = RequestFactory()
        request = rf.post("/api/v1/pharmacy/purchase-challan/")
        request.user = self.user
        line = {
            "medicine": str(self.med.id),
            "batch_no": "B55",
            "expiry_date": timezone.now().date().replace(year=timezone.now().year + 1),
            "quantity": Decimal("55"),
            "quantity_basis": "base",
            "pack_type": "strip",
            "conversion": Decimal("1"),
            "purchase_rate": Decimal("2"),
            "mrp": Decimal("5"),
            "gst_type": "exclusive",
            "gst_percent": Decimal("12"),
            "discount": Decimal("0"),
            "skip_gst": False,
        }
        out = process_purchase_challan(request=request, hospital=self.hospital, lines=[line])
        self.assertEqual(len(out), 1)
        batch_id = out[0]["batch_id"]
        total = StockLedger.objects.filter(batch_id=batch_id).aggregate(s=Sum("qty_change"))["s"]
        self.assertEqual(total, Decimal("55"))

    def test_tablet_rate_matches_strip_line_gross(self):
        """2 strips × 10 @ 100/strip vs 20 tabs @ 10/tab → same taxable (200) and same stock."""
        rf = RequestFactory()
        request = rf.post("/api/v1/pharmacy/purchase-challan/")
        request.user = self.user
        exp = timezone.now().date().replace(year=timezone.now().year + 1)
        line_strip = {
            "medicine": str(self.med.id),
            "batch_no": "BS",
            "expiry_date": exp,
            "quantity": Decimal("2"),
            "pack_type": "strip",
            "conversion": Decimal("10"),
            "rate_type": "STRIP",
            "purchase_rate": Decimal("100"),
            "mrp": Decimal("150"),
            "gst_type": "exclusive",
            "gst_percent": Decimal("12"),
            "discount": Decimal("0"),
            "skip_gst": False,
        }
        line_tab = {
            **line_strip,
            "batch_no": "BT",
            "rate_type": "TABLET",
            "purchase_rate": Decimal("10"),
        }
        out_s = process_purchase_challan(request=request, hospital=self.hospital, lines=[line_strip])
        out_t = process_purchase_challan(request=request, hospital=self.hospital, lines=[line_tab])
        self.assertEqual(out_s[0]["taxable_amount"], "200.00")
        self.assertEqual(out_t[0]["taxable_amount"], "200.00")
        bid_s = out_s[0]["batch_id"]
        bid_t = out_t[0]["batch_id"]
        self.assertEqual(
            StockLedger.objects.filter(batch_id=bid_s).aggregate(s=Sum("qty_change"))["s"],
            Decimal("20"),
        )
        self.assertEqual(
            StockLedger.objects.filter(batch_id=bid_t).aggregate(s=Sum("qty_change"))["s"],
            Decimal("20"),
        )

    def test_purchase_with_supplier_header(self):
        sup = PharmacySupplier.objects.create(hospital=self.hospital, name="Acme Drugs")
        rf = RequestFactory()
        request = rf.post("/api/v1/pharmacy/purchase-challan/")
        request.user = self.user
        line = {
            "medicine": str(self.med.id),
            "batch_no": "B-SUP",
            "expiry_date": timezone.now().date().replace(year=timezone.now().year + 1),
            "quantity": Decimal("1"),
            "pack_type": "strip",
            "conversion": Decimal("10"),
            "purchase_rate": Decimal("50"),
            "mrp": Decimal("80"),
            "gst_type": "exclusive",
            "gst_percent": Decimal("12"),
            "discount": Decimal("0"),
            "skip_gst": False,
        }
        out = process_purchase_challan(
            request=request,
            hospital=self.hospital,
            lines=[line],
            supplier_id=sup.id,
            invoice_no="INV-1",
            payment_type="credit",
        )
        self.assertEqual(len(out), 1)
