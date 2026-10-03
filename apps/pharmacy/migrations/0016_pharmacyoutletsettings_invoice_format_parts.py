from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0015_pharmacyoutletsettings_invoice_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="pharmacyoutletsettings",
            name="invoice_format_part1",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Leading segment (e.g. INV-). If both part1 and part2 are empty, legacy invoice_prefix + year format is used.",
                max_length=48,
            ),
        ),
        migrations.AddField(
            model_name="pharmacyoutletsettings",
            name="invoice_format_part2",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Middle segment before the sequence; use {year} or {YYYY} for the 4-digit calendar year.",
                max_length=48,
            ),
        ),
        migrations.AddField(
            model_name="pharmacyoutletsettings",
            name="invoice_seq_pad",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Minimum digit width for the trailing sequence (0 = no leading zeros).",
            ),
        ),
    ]
