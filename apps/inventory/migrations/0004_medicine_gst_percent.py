# Generated manually — Marg-style product GST default

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_pharmacy_erp_enhancements"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicine",
            name="gst_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("5.00"), max_digits=5),
        ),
    ]
