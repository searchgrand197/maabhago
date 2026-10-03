from decimal import Decimal

from django.test import SimpleTestCase

from apps.pharmacy.calculations import (
    calculate_marg_purchase_line_amounts,
    calculate_purchase_line_amounts,
    calculate_sale_gst_split,
    compute_marg_gst_on_base,
    split_gst_equally,
)


class PurchaseGstCalculationTests(SimpleTestCase):
    def test_exclusive_gst(self):
        r = calculate_purchase_line_amounts(
            qty_packs=Decimal("2"),
            purchase_rate=Decimal("100"),
            discount=Decimal("0"),
            gst_type="exclusive",
            gst_percent=Decimal("12"),
            skip_gst=False,
        )
        self.assertEqual(r["taxable_amount"], Decimal("200.00"))
        self.assertEqual(r["gst_amount"], Decimal("24.00"))
        self.assertEqual(r["final_amount"], Decimal("224.00"))

    def test_inclusive_gst(self):
        r = calculate_purchase_line_amounts(
            qty_packs=Decimal("1"),
            purchase_rate=Decimal("112"),
            discount=Decimal("0"),
            gst_type="inclusive",
            gst_percent=Decimal("12"),
            skip_gst=False,
        )
        self.assertEqual(r["final_amount"], Decimal("112.00"))
        self.assertEqual(r["taxable_amount"], Decimal("100.00"))
        self.assertEqual(r["gst_amount"], Decimal("12.00"))

    def test_skip_gst(self):
        r = calculate_purchase_line_amounts(
            qty_packs=Decimal("3"),
            purchase_rate=Decimal("50"),
            discount=Decimal("10"),
            gst_type="exclusive",
            gst_percent=Decimal("12"),
            skip_gst=True,
        )
        self.assertEqual(r["taxable_amount"], Decimal("140.00"))
        self.assertEqual(r["gst_amount"], Decimal("0.00"))
        self.assertEqual(r["final_amount"], Decimal("140.00"))


class MargPurchaseCalculationTests(SimpleTestCase):
    def test_marg_exclusive(self):
        r = calculate_marg_purchase_line_amounts(
            line_gross=Decimal("200"),
            discount=Decimal("0"),
            gst_type="exclusive",
            gst_percent=Decimal("12"),
            skip_gst=False,
        )
        self.assertEqual(r["taxable_amount"], Decimal("200.00"))
        self.assertEqual(r["gst_amount"], Decimal("24.00"))
        self.assertEqual(r["final_amount"], Decimal("224.00"))

    def test_marg_exclusive_with_discount(self):
        r = calculate_marg_purchase_line_amounts(
            line_gross=Decimal("200"),
            discount=Decimal("10"),
            gst_type="exclusive",
            gst_percent=Decimal("12"),
            skip_gst=False,
        )
        self.assertEqual(r["final_amount"], Decimal("214.00"))

    def test_marg_inclusive(self):
        r = calculate_marg_purchase_line_amounts(
            line_gross=Decimal("112"),
            discount=Decimal("0"),
            gst_type="inclusive",
            gst_percent=Decimal("12"),
            skip_gst=False,
        )
        self.assertEqual(r["taxable_amount"], Decimal("100.00"))
        self.assertEqual(r["gst_amount"], Decimal("12.00"))
        self.assertEqual(r["final_amount"], Decimal("112.00"))

    def test_marg_inclusive_discount_after_gst(self):
        r = compute_marg_gst_on_base(
            base_amount=Decimal("112"),
            discount=Decimal("10"),
            gst_type="inclusive",
            gst_percent=Decimal("12"),
            no_gst=False,
        )
        self.assertEqual(r["final_amount"], Decimal("102.00"))

    def test_marg_no_gst(self):
        r = compute_marg_gst_on_base(
            base_amount=Decimal("200"),
            discount=Decimal("0"),
            gst_type="exclusive",
            gst_percent=Decimal("12"),
            no_gst=True,
        )
        self.assertEqual(r["gst_amount"], Decimal("0.00"))
        self.assertEqual(r["final_amount"], Decimal("200.00"))

    def test_split_gst_equally(self):
        a, b = split_gst_equally(Decimal("12.00"))
        self.assertEqual(a + b, Decimal("12.00"))


class SaleGstSplitTests(SimpleTestCase):
    def test_split(self):
        cgst, sgst = calculate_sale_gst_split(
            taxable_line_total=Decimal("100"),
            cgst_rate=Decimal("6"),
            sgst_rate=Decimal("6"),
        )
        self.assertEqual(cgst, Decimal("6.00"))
        self.assertEqual(sgst, Decimal("6.00"))
