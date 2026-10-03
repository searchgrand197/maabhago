import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shared", "0001_initial"),
        ("inventory", "0004_medicine_gst_percent"),
    ]

    operations = [
        migrations.CreateModel(
            name="MedicineCategory",
            fields=[
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "hospital",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medicine_categories",
                        to="shared.hospital",
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["hospital", "name"], name="inventory_m_hospita_8c771c_idx")],
                "unique_together": {("hospital", "name")},
            },
        ),
    ]

