from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0007_rename_pharmacy_sup_hosp_name_idx_pharmacy_ph_hospita_8a5e91_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pharmacyinvoice",
            name="date",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
    ]
