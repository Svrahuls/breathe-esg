from rest_framework import serializers
from .models import Tenant, DataSource, IngestionJob, EmissionRecord, AuditLog


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "created_at"]


class DataSourceSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = DataSource
        fields = ["id", "tenant", "tenant_name", "source_type", "name", "created_at"]


class IngestionJobSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    source_type = serializers.CharField(source="source.source_type", read_only=True)
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True
    )

    class Meta:
        model = IngestionJob
        fields = [
            "id", "tenant", "source", "source_name", "source_type",
            "uploaded_by", "uploaded_by_username",
            "file_name", "status",
            "total_rows", "success_rows", "failed_rows", "suspicious_rows", "duplicate_rows",
            "error_message", "created_at", "completed_at",
        ]


class EmissionRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    source_type = serializers.CharField(source="source.source_type", read_only=True)
    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username", read_only=True
    )
    job_file_name = serializers.CharField(source="job.file_name", read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            "id", "tenant", "source", "source_name", "source_type",
            "job", "job_file_name",
            "raw_data", "source_hash",
            "normalized_quantity", "normalized_unit",
            "scope", "category",
            "activity_date", "location", "description",
            "parser_flags",                         # now surfaced to analysts
            "status",
            "reviewed_by", "reviewed_by_username", "reviewed_at", "review_note",
            "is_locked",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "tenant", "source", "job",
            "raw_data", "source_hash",
            "normalized_quantity", "normalized_unit",
            "scope", "category", "parser_flags",
            "created_at", "updated_at",
        ]


class ApproveRecordSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=False, allow_blank=True, default="")


class RejectRecordSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=True, allow_blank=False)


class AuditLogSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source="changed_by.username", read_only=True
    )

    class Meta:
        model = AuditLog
        fields = [
            "id", "record", "action",
            "changed_by", "changed_by_username",
            "changed_at", "before_data", "after_data",
        ]
