from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ipd", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ipdadmission",
            name="department",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
