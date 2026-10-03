from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0005_medicinecategory"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicine",
            name="company_name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="medicine",
            name="composition",
            field=models.CharField(blank=True, default="", max_length=250),
        ),
        migrations.AddField(
            model_name="medicine",
            name="default_mrp",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
    ]

