from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0010_pharmacy_batch_snapshot_set_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="pharmacyoutletsettings",
            name="default_sale_discount_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5),
        ),
    ]
