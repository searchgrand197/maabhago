from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ambulance.models import AmbulanceCollection, AmbulanceVehicle
from apps.billing.models import BillingInvoice, InvoiceItem
from apps.patients.models import Patient
from apps.payments.models import PaymentSlipSequence, PaymentTransaction
from apps.reports.ca_summary import HEAD_CAESAREAN, HEAD_DELIVERY, HEAD_IOL, HEAD_LAB, HEAD_ROOM, classify_line
from apps.shared.models import Hospital

User = get_user_model()


def _data(response):
    return response.data.get("data", response.data)


class ClassifyLineTests(TestCase):
    def test_heads_by_description(self):
        self.assertEqual(classify_line("IOL", ""), HEAD_IOL)
        self.assertEqual(classify_line("CESARIAN", ""), HEAD_CAESAREAN)
        self.assertEqual(classify_line("LSCS package", ""), HEAD_CAESAREAN)
        self.assertEqual(classify_line("Normal Delivery", ""), HEAD_DELIVERY)
        self.assertEqual(classify_line("deleivery", ""), HEAD_DELIVERY)
        self.assertEqual(classify_line("Delivery Test", "LAB"), HEAD_LAB)
        self.assertEqual(classify_line("Room Charges: 21 (2 days @ ₹800.00)", ""), HEAD_ROOM)
        self.assertEqual(classify_line("ROOM RENT", ""), HEAD_ROOM)


class CaSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="CA Hospital", slug="ca-hospital")
        self.user = User.objects.create_user(email="ca@test.com", password="x", hospital=self.hospital)
        self.client.force_authenticate(self.user)
        self.patient = Patient.objects.create(hospital=self.hospital, uhid="UHID-CA-1", first_name="Asha")
        PaymentSlipSequence.objects.create(hospital=self.hospital, year=timezone.now().year, last_seq=0)
        self.today = timezone.localdate()
        self._inv_seq = 0

    def _invoice(self, prefix, items, total=None, amount_paid=Decimal("0.00")):
        self._inv_seq += 1
        line_sum = sum((Decimal(str(amount)) for _, amount, _ in items), Decimal("0.00"))
        invoice = BillingInvoice.objects.create(
            hospital=self.hospital,
            invoice_no=f"{prefix}-CA-{self._inv_seq:04d}",
            encounter_type=BillingInvoice.EncounterType.IPD,
            patient=self.patient,
            status=BillingInvoice.Status.FINALIZED,
            total_amount=total if total is not None else line_sum,
            amount_paid=amount_paid,
            invoice_date=self.today,
        )
        for description, amount, category in items:
            InvoiceItem.objects.create(
                invoice=invoice,
                description=description,
                category=category,
                unit_price=Decimal(str(amount)),
                line_total=Decimal(str(amount)),
            )
        return invoice

    def _pay(self, invoice, amount, mode="cash", **extra):
        return PaymentTransaction.objects.create(
            hospital=self.hospital,
            invoice=invoice,
            amount=Decimal(str(amount)),
            payment_mode=mode,
            collected_by=self.user,
            paid_at=timezone.now(),
            **extra,
        )

    def _summary(self):
        res = self.client.get(f"/api/v1/reports/ca-summary/?date_from={self.today}&date_to={self.today}")
        self.assertEqual(res.status_code, 200)
        return _data(res)

    @staticmethod
    def _heads(payload):
        return {row["key"]: row for row in payload["heads"]}

    def test_partial_payment_is_split_pro_rata(self):
        invoice = self._invoice("IPDSRV", [("IOL", 15000, ""), ("CESARIAN", 5000, "")])
        self._pay(invoice, 10000)
        heads = self._heads(self._summary())
        self.assertEqual(heads["iol"]["amount"], "7500.00")
        self.assertEqual(heads["caesarean"]["amount"], "2500.00")
        self.assertEqual(heads["iol"]["count"], 1)

    def test_room_invoice_is_adjusted_from_advance_not_cash(self):
        advance = self._invoice("IPDADV", [("Advance Payment", 5000, "")])
        self._pay(advance, 5000, mode="upi")
        self._invoice("IPDROOM", [("Room Charges: 21 (2 days @ ₹800.00)", 1600, "")])

        payload = self._summary()
        heads = self._heads(payload)
        self.assertEqual(heads["ipd_advance"]["amount"], "5000.00")
        self.assertEqual(heads["room_charges"]["amount"], "0.00")
        self.assertEqual(payload["ipd"]["room_adjusted"], "1600.00")
        self.assertEqual(payload["ipd"]["net_ipd"], "3400.00")
        self.assertEqual(payload["gross_received"], "5000.00")
        self.assertEqual(payload["modes"]["upi"], "5000.00")

    def test_voided_payments_excluded_and_refunds_negative(self):
        invoice = self._invoice("IPDSRV", [("Delivery", 8000, "")])
        self._pay(invoice, 8000)
        self._pay(invoice, 8000, voided=True)
        refund_inv = self._invoice("IPDREF", [("Discharge refund (ledger offset)", 0, "")])
        self._pay(refund_inv, -1000)

        payload = self._summary()
        heads = self._heads(payload)
        self.assertEqual(heads["delivery"]["amount"], "8000.00")
        self.assertEqual(heads["refunds"]["amount"], "-1000.00")
        self.assertEqual(payload["gross_received"], "7000.00")
        self.assertTrue(payload["reconciliation"]["reconciled"])

    def test_gross_and_net_match_collection_summary(self):
        self._pay(self._invoice("IPDSRV", [("IOL", 12000, ""), ("CBC", 300, "LAB")]), 12300)
        self._pay(self._invoice("IPDADV", [("Advance Payment", 2000, "")]), 2000)
        vehicle = AmbulanceVehicle.objects.create(hospital=self.hospital, vehicle_number="HR31AB1234")
        AmbulanceCollection.objects.create(
            hospital=self.hospital,
            vehicle=vehicle,
            receipt_no="AMB-T-0001",
            amount=Decimal("700.00"),
            payment_mode="cash",
            collected_by=self.user,
        )

        payload = self._summary()
        heads = self._heads(payload)
        self.assertEqual(heads["lab"]["amount"], "300.00")
        self.assertEqual(heads["ambulance"]["amount"], "700.00")
        self.assertEqual(payload["ambulance_by_vehicle"][0]["vehicle_number"], "HR31AB1234")

        res = self.client.get(f"/api/v1/reports/collection-summary/?date_from={self.today}&date_to={self.today}")
        summary = _data(res)
        expected_gross = Decimal(summary["grand_total"]) + Decimal(summary["other_income_total"])
        self.assertEqual(Decimal(payload["gross_received"]), expected_gross)
        self.assertEqual(Decimal(payload["net_after_expenses"]), Decimal(summary["net_total"]))
        self.assertTrue(payload["reconciliation"]["reconciled"])
