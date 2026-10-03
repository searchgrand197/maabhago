# Generated manually for Marg-style purchase supplier master

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0002_pharmacy_erp_enhancements"),
        ("shared", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PharmacySupplier",
            fields=[
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("phone", models.CharField(blank=True, default="", max_length=40)),
                ("gst_number", models.CharField(blank=True, default="", max_length=40)),
                ("address", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "hospital",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pharmacy_suppliers",
                        to="shared.hospital",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="pharmacysupplier",
            index=models.Index(fields=["hospital", "name"], name="pharmacy_sup_hosp_name_idx"),
        ),
        migrations.AddIndex(
            model_name="pharmacysupplier",
            index=models.Index(fields=["hospital", "is_active"], name="pharmacy_sup_hosp_act_idx"),
        ),
    ]
