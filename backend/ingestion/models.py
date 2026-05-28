import uuid
from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class DataSource(models.Model):
    SOURCE_SAP = "SAP"
    SOURCE_UTILITY = "UTILITY"
    SOURCE_TRAVEL = "TRAVEL"
    SOURCE_CHOICES = [
        (SOURCE_SAP, "SAP"),
        (SOURCE_UTILITY, "Utility"),
        (SOURCE_TRAVEL, "Travel"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} — {self.name}"

    class Meta:
        ordering = ["name"]


class IngestionJob(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_DONE = "DONE"
    STATUS_FAILED = "FAILED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="jobs")
    source = models.ForeignKey(
        DataSource, on_delete=models.SET_NULL, null=True, related_name="jobs"
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    file_name = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    total_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    suspicious_rows = models.IntegerField(default=0)
    duplicate_rows = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.file_name} [{self.status}]"

    class Meta:
        ordering = ["-created_at"]


class EmissionRecord(models.Model):
    SCOPE_1 = 1
    SCOPE_2 = 2
    SCOPE_3 = 3
    SCOPE_CHOICES = [(1, "Scope 1"), (2, "Scope 2"), (3, "Scope 3")]

    CATEGORY_FUEL = "fuel"
    CATEGORY_ELECTRICITY = "electricity"
    CATEGORY_FLIGHT = "flight"
    CATEGORY_HOTEL = "hotel"
    CATEGORY_GROUND = "ground"
    CATEGORY_CHOICES = [
        (CATEGORY_FUEL, "Fuel"),
        (CATEGORY_ELECTRICITY, "Electricity"),
        (CATEGORY_FLIGHT, "Flight"),
        (CATEGORY_HOTEL, "Hotel"),
        (CATEGORY_GROUND, "Ground Transport"),
    ]

    STATUS_PENDING = "PENDING_REVIEW"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_SUSPICIOUS = "SUSPICIOUS"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SUSPICIOUS, "Suspicious"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="records"
    )
    source = models.ForeignKey(
        DataSource, on_delete=models.SET_NULL, null=True, related_name="records"
    )
    job = models.ForeignKey(
        IngestionJob, on_delete=models.SET_NULL, null=True, related_name="records"
    )

    # Raw source-of-truth
    raw_data = models.JSONField()
    source_hash = models.CharField(max_length=32, db_index=True)

    # Normalized values
    normalized_quantity = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    normalized_unit = models.CharField(max_length=20, default="kgCO2e")

    # Classification
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Context
    activity_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    # Parser flags — stored so analysts can see exactly WHY a record is suspicious
    # e.g. ["LONG_BILLING_PERIOD", "DEFAULT_CARBON_INTENSITY"]
    parser_flags = models.JSONField(default=list, blank=True)

    # Review workflow
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_records",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    # Audit lock
    is_locked = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} | {self.normalized_quantity} {self.normalized_unit} [{self.status}]"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "scope"]),
            models.Index(fields=["source_hash"]),
            models.Index(fields=["activity_date"]),
        ]


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(
        EmissionRecord, on_delete=models.CASCADE, related_name="audit_logs"
    )
    action = models.CharField(max_length=100)
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} on {self.record_id} at {self.changed_at}"

    class Meta:
        ordering = ["-changed_at"]
