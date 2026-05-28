from django.contrib import admin
from .models import Tenant, DataSource, IngestionJob, EmissionRecord, AuditLog


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "source_type", "tenant", "created_at"]
    list_filter = ["source_type", "tenant"]


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = [
        "file_name",
        "status",
        "total_rows",
        "success_rows",
        "suspicious_rows",
        "duplicate_rows",
        "failed_rows",
        "created_at",
    ]
    list_filter = ["status", "source__source_type"]
    readonly_fields = ["id", "created_at", "completed_at"]


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "category",
        "scope",
        "normalized_quantity",
        "normalized_unit",
        "status",
        "activity_date",
        "is_locked",
        "created_at",
    ]
    list_filter = ["status", "scope", "category", "source__source_type", "is_locked"]
    search_fields = ["description", "location", "source_hash"]
    readonly_fields = [
        "id",
        "source_hash",
        "raw_data",
        "normalized_quantity",
        "normalized_unit",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "activity_date"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "record", "changed_by", "changed_at"]
    list_filter = ["action"]
    readonly_fields = ["id", "changed_at", "before_data", "after_data"]
