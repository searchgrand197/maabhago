from django.contrib import admin

from .models import (
    BillingInvoice,
    DailyClosingSummary,
    IPDFinalBill,
    IPDFinalBillItem,
    IPDFinalBillSequence,
    InvoiceItem,
    InvoiceNumberSequence,
)


@admin.register(InvoiceNumberSequence)
class InvoiceNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "year", "last_seq", "created_at", "updated_at")


@admin.register(IPDFinalBillSequence)
class IPDFinalBillSequenceAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "year", "last_seq", "created_at", "updated_at")
    list_filter = ("hospital", "year")
    search_fields = ("hospital__name",)


@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice_no", "patient", "encounter_type", "status", "hospital", "invoice_date", "is_deleted")
    list_filter = ("hospital", "status", "encounter_type", "is_deleted")
    search_fields = ("invoice_no", "id")


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "description", "line_total")


@admin.register(IPDFinalBillItem)
class IPDFinalBillItemAdmin(admin.ModelAdmin):
    list_display = ("id", "final_bill", "description", "amount")
    search_fields = ("final_bill__bill_no", "description")


class IPDFinalBillItemInline(admin.TabularInline):
    model = IPDFinalBillItem
    extra = 0
    fields = ("description", "category", "quantity", "rate", "amount")


@admin.register(IPDFinalBill)
class IPDFinalBillAdmin(admin.ModelAdmin):
    inlines = [IPDFinalBillItemInline]
    list_display = ("bill_no", "patient_name", "hospital", "admission", "net_amount", "amount_paid", "due_amount", "created_at")
    list_filter = ("hospital", "created_at")
    search_fields = ("bill_no", "patient_name", "patient_phone", "admission__ipd_no")
    readonly_fields = ("admission", "hospital", "patient", "created_at", "updated_at")


@admin.register(DailyClosingSummary)
class DailyClosingSummaryAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "closing_date", "total_collected", "total_outstanding")
