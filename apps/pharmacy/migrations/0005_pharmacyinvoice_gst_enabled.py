from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0004_outlet_default_gst"),
    ]

    operations = [
        migrations.AddField(
            model_name="pharmacyinvoice",
            name="gst_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
