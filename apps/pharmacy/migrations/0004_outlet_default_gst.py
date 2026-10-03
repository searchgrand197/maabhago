# Generated manually — global default GST % for pharmacy outlet

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0003_pharmacysupplier"),
    ]

    operations = [
        migrations.AddField(
            model_name="pharmacyoutletsettings",
            name="default_gst_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("5.00"), max_digits=5),
        ),
    ]
