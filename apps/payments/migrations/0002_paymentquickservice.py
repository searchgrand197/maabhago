from decimal import Decimal
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentQuickService",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("label", models.CharField(max_length=120)),
                ("price", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "hospital",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="payment_quick_services", to="shared.hospital"),
                ),
            ],
            options={
                "ordering": ["sort_order", "created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="paymentquickservice",
            index=models.Index(fields=["hospital", "is_active", "sort_order"], name="payments_pa_hospita_8f1f74_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentquickservice",
            index=models.Index(fields=["hospital", "label"], name="payments_pa_hospita_2dfc56_idx"),
        ),
    ]
