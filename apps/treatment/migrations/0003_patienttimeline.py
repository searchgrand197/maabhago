import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0001_initial"),
        ("ipd", "0001_initial"),
        ("treatment", "0002_treatment_staff_assignment_and_notifications"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientTimeline",
            fields=[
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("plan_saved", "Treatment Plan Saved"),
                            ("treatment_done", "Treatment Done"),
                            ("treatment_skipped", "Treatment Skipped"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("timestamp", models.DateTimeField(db_index=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="patient_timeline_events_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "hospital",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="patient_timeline_events",
                        to="shared.hospital",
                    ),
                ),
                (
                    "ipd_admission",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="patient_timeline_events",
                        to="ipd.ipdadmission",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treatment_timeline_events",
                        to="patients.patient",
                    ),
                ),
                (
                    "treatment_item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="timeline_events",
                        to="treatment.treatmentplanitem",
                    ),
                ),
                (
                    "treatment_plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="timeline_events",
                        to="treatment.treatmentplan",
                    ),
                ),
                (
                    "treatment_task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="timeline_events",
                        to="treatment.treatmenttask",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp", "-created_at"],
                "indexes": [
                    models.Index(fields=["hospital", "patient", "timestamp"], name="treatment_p_hospita_abf9ec_idx"),
                    models.Index(fields=["ipd_admission", "timestamp"], name="treatment_p_ipd_ad_9e83f0_idx"),
                    models.Index(fields=["event_type", "timestamp"], name="treatment_p_event_t_f9a1d9_idx"),
                ],
            },
        ),
    ]

