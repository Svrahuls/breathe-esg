from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="emissionrecord",
            name="parser_flags",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of flags set by the parser (e.g. LONG_BILLING_PERIOD, DEFAULT_CARBON_INTENSITY). "
                          "Stored so analysts can see exactly why a record was flagged.",
            ),
        ),
    ]
