import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pharmacy", "0005_pharmacyinvoice_gst_enabled"),
        ("shared", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PharmacyPurchaseChallan",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("supplier_name_snapshot", models.CharField(blank=True, default="", help_text="Supplier name at posting time if supplier row is later removed.", max_length=200)),
                ("challan_no", models.CharField(blank=True, db_index=True, default="", max_length=120)),
                ("purchase_date", models.DateField(db_index=True)),
                ("payment_type", models.CharField(blank=True, default="cash", max_length=20)),
                ("gst_enabled", models.BooleanField(default=True)),
                ("total_items", models.PositiveIntegerField(default=0)),
                ("total_strips", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=14)),
                ("total_extra_tablets", models.DecimalField(decimal_places=3, default=Decimal("0"), help_text="Base-only quantity lines (tablets not counted as strips).", max_digits=14)),
                ("total_base_qty", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=14)),
                ("total_taxable", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pharmacy_purchase_challans_created", to=settings.AUTH_USER_MODEL)),
                ("hospital", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pharmacy_purchase_challans", to="shared.hospital")),
                ("supplier", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="purchase_challans", to="pharmacy.pharmacysupplier")),
            ],
            options={
                "ordering": ("-purchase_date", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="PharmacyPurchaseChallanLine",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("quantity_basis", models.CharField(default="pack", max_length=10)),
                ("pack_type", models.CharField(blank=True, default="", max_length=40)),
                ("conversion", models.DecimalField(decimal_places=3, default=Decimal("1"), max_digits=14)),
                ("pack_quantity", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=14)),
                ("base_qty", models.DecimalField(decimal_places=3, default=Decimal("0"), max_digits=14)),
                ("rate_type", models.CharField(default="STRIP", max_length=10)),
                ("purchase_rate", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("mrp", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("sale_rate", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("discount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("gst_type", models.CharField(blank=True, default="exclusive", max_length=20)),
                ("gst_percent", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5)),
                ("no_gst", models.BooleanField(default=False)),
                ("taxable_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("gst_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("final_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchase_challan_lines", to="inventory.medicinebatch")),
                ("challan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="pharmacy.pharmacypurchasechallan")),
                ("medicine", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchase_challan_lines", to="inventory.medicine")),
            ],
            options={
                "ordering": ("created_at", "id"),
            },
        ),
        migrations.AddIndex(
            model_name="pharmacypurchasechallan",
            index=models.Index(fields=["hospital", "purchase_date"], name="pharm_pc_hosp_date_idx"),
        ),
        migrations.AddIndex(
            model_name="pharmacypurchasechallan",
            index=models.Index(fields=["hospital", "supplier"], name="pharm_pc_hosp_sup_idx"),
        ),
        migrations.AddIndex(
            model_name="pharmacypurchasechallanline",
            index=models.Index(fields=["challan", "medicine"], name="pharm_pcline_ch_med_idx"),
        ),
    ]
