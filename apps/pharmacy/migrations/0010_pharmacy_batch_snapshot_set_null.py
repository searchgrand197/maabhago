from django.db import migrations, models
import django.db.models.deletion


def backfill_invoice_item_snapshots(apps, schema_editor):
    Item = apps.get_model("pharmacy", "PharmacyInvoiceItem")
    Batch = apps.get_model("inventory", "MedicineBatch")
    for row in Item.objects.exclude(batch_id__isnull=True).iterator(chunk_size=300):
        try:
            b = Batch.objects.get(pk=row.batch_id)
        except Batch.DoesNotExist:
            continue
        Item.objects.filter(pk=row.pk).update(
            snapshot_batch_no=b.batch_no,
            snapshot_expiry_date=b.expiry_date,
        )


def backfill_challan_line_snapshots(apps, schema_editor):
    Line = apps.get_model("pharmacy", "PharmacyPurchaseChallanLine")
    Batch = apps.get_model("inventory", "MedicineBatch")
    for row in Line.objects.exclude(batch_id__isnull=True).iterator(chunk_size=300):
        try:
            b = Batch.objects.get(pk=row.batch_id)
        except Batch.DoesNotExist:
            continue
        Line.objects.filter(pk=row.pk).update(
            snapshot_batch_no=b.batch_no,
            snapshot_expiry_date=b.expiry_date,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacy", "0009_pharmacyinvoice_ipd_payment_fields"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pharmacyinvoiceitem",
            name="snapshot_batch_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="pharmacyinvoiceitem",
            name="snapshot_expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pharmacypurchasechallanline",
            name="snapshot_batch_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="pharmacypurchasechallanline",
            name="snapshot_expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_invoice_item_snapshots, migrations.RunPython.noop),
        migrations.RunPython(backfill_challan_line_snapshots, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="pharmacyinvoiceitem",
            name="batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pharmacy_sale_items",
                to="inventory.medicinebatch",
            ),
        ),
        migrations.AlterField(
            model_name="pharmacypurchasechallanline",
            name="batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchase_challan_lines",
                to="inventory.medicinebatch",
            ),
        ),
    ]
