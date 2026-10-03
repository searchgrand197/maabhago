from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0006_medicine_product_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicinecategory",
            name="rule_type",
            field=models.CharField(
                choices=[
                    ("strip_based", "Strip-based (allow loose)"),
                    ("liquid", "Liquid (no loose)"),
                    ("flexible", "Flexible (outer + retail + base)"),
                    ("unit_only", "Unit only"),
                ],
                default="unit_only",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="medicinecategory",
            name="allow_loose_sale",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="medicinecategory",
            name="base_unit_label",
            field=models.CharField(default="unit", max_length=40),
        ),
        migrations.AddField(
            model_name="medicinecategory",
            name="retail_pack_label",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="medicinecategory",
            name="outer_pack_label",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
    ]
