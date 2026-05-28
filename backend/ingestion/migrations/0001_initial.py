from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DataSource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_type", models.CharField(choices=[("SAP", "SAP"), ("UTILITY", "Utility"), ("TRAVEL", "Travel")], max_length=20)),
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sources", to="ingestion.tenant")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="IngestionJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file_name", models.CharField(max_length=500)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("DONE", "Done"), ("FAILED", "Failed")], default="PENDING", max_length=20)),
                ("total_rows", models.IntegerField(default=0)),
                ("success_rows", models.IntegerField(default=0)),
                ("failed_rows", models.IntegerField(default=0)),
                ("suspicious_rows", models.IntegerField(default=0)),
                ("duplicate_rows", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("source", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="jobs", to="ingestion.datasource")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jobs", to="ingestion.tenant")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="auth.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="EmissionRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("raw_data", models.JSONField()),
                ("source_hash", models.CharField(db_index=True, max_length=32)),
                ("normalized_quantity", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("normalized_unit", models.CharField(default="kgCO2e", max_length=20)),
                ("scope", models.IntegerField(choices=[(1, "Scope 1"), (2, "Scope 2"), (3, "Scope 3")])),
                ("category", models.CharField(choices=[("fuel", "Fuel"), ("electricity", "Electricity"), ("flight", "Flight"), ("hotel", "Hotel"), ("ground", "Ground Transport")], max_length=20)),
                ("activity_date", models.DateField(blank=True, null=True)),
                ("location", models.CharField(blank=True, max_length=500)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("PENDING_REVIEW", "Pending Review"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("SUSPICIOUS", "Suspicious")], db_index=True, default="PENDING_REVIEW", max_length=20)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.TextField(blank=True)),
                ("is_locked", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="records", to="ingestion.ingestionjob")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_records", to="auth.user")),
                ("source", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="records", to="ingestion.datasource")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="ingestion.tenant")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="emissionrecord",
            index=models.Index(fields=["tenant", "status"], name="ingestion_e_tenant_i_status_idx"),
        ),
        migrations.AddIndex(
            model_name="emissionrecord",
            index=models.Index(fields=["tenant", "scope"], name="ingestion_e_tenant_i_scope_idx"),
        ),
        migrations.AddIndex(
            model_name="emissionrecord",
            index=models.Index(fields=["source_hash"], name="ingestion_e_source__hash_idx"),
        ),
        migrations.AddIndex(
            model_name="emissionrecord",
            index=models.Index(fields=["activity_date"], name="ingestion_e_activity_date_idx"),
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=100)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("before_data", models.JSONField(blank=True, null=True)),
                ("after_data", models.JSONField(blank=True, null=True)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="auth.user")),
                ("record", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_logs", to="ingestion.emissionrecord")),
            ],
            options={"ordering": ["-changed_at"]},
        ),
    ]
