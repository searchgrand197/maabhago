from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ipd", "0002_ipdadmission_department"),
        ("pharmacy", "0008_alter_pharmacyinvoice_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="pharmacyinvoice",
            name="ipd_admission",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="pharmacy_invoices",
                to="ipd.ipdadmission",
            ),
        ),
        migrations.AddField(
            model_name="pharmacyinvoice",
            name="paid_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="pharmacyinvoice",
            name="payment_method",
            field=models.CharField(default="cash", max_length=20),
        ),
    ]
