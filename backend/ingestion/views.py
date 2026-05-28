import logging
from datetime import datetime, timezone

from django.db import transaction
from django.db.models import Count, Sum, Q
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tenant, DataSource, IngestionJob, EmissionRecord, AuditLog
from .serializers import (
    IngestionJobSerializer,
    EmissionRecordSerializer,
    ApproveRecordSerializer,
    RejectRecordSerializer,
    AuditLogSerializer,
)
from .parsers import parse_sap_csv, parse_utility_csv, parse_travel_csv

logger = logging.getLogger("ingestion")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_default_tenant():
    tenant, _ = Tenant.objects.get_or_create(
        slug="default", defaults={"name": "Default Organisation"}
    )
    return tenant


def _get_or_create_source(tenant: Tenant, source_type: str, name: str) -> DataSource:
    source, _ = DataSource.objects.get_or_create(
        tenant=tenant, source_type=source_type, defaults={"name": name}
    )
    return source


def _get_tenant(request) -> Tenant:
    """
    Resolve the tenant for this request.
    In the prototype there is only one tenant (default).
    A real multi-tenant deployment would derive this from the JWT/session.
    """
    return _get_or_create_default_tenant()


def _ingest_records(file_content: bytes, parser_fn, source: DataSource, job: IngestionJob):
    """Run parser and bulk-create EmissionRecord rows, updating the job counters."""
    total = success = failed = suspicious = duplicates = 0

    records_to_create = []
    existing_hashes = set(
        EmissionRecord.objects.filter(tenant=source.tenant).values_list(
            "source_hash", flat=True
        )
    )

    for parsed in parser_fn(file_content):
        total += 1
        flags = parsed.pop("flags", [])
        parsed.pop("row_num", None)

        h = parsed["source_hash"]

        # Cross-file duplicate check (within tenant)
        if h in existing_hashes and parsed.get("status") != "DUPLICATE":
            parsed["status"] = "DUPLICATE"
            flags.append("CROSS_FILE_DUPLICATE")

        existing_hashes.add(h)

        if parsed["status"] == "DUPLICATE":
            duplicates += 1
            continue  # skip true duplicates

        if parsed["status"] == "SUSPICIOUS":
            suspicious += 1
        elif parsed["status"] == "PENDING_REVIEW":
            success += 1
        else:
            failed += 1

        records_to_create.append(
            EmissionRecord(
                tenant=source.tenant,
                source=source,
                job=job,
                parser_flags=flags,   # now persisted so analysts can see WHY
                **parsed,
            )
        )

    # Bulk insert in batches of 500
    for i in range(0, len(records_to_create), 500):
        EmissionRecord.objects.bulk_create(records_to_create[i : i + 500])

    job.total_rows = total
    job.success_rows = success
    job.failed_rows = failed
    job.suspicious_rows = suspicious
    job.duplicate_rows = duplicates
    job.status = IngestionJob.STATUS_DONE
    job.completed_at = datetime.now(timezone.utc)
    job.save()

    logger.info(
        "Job %s done: total=%d success=%d suspicious=%d duplicates=%d failed=%d",
        job.id, total, success, suspicious, duplicates, failed,
    )


# ---------------------------------------------------------------------------
# Ingestion endpoints  (BUG-04 FIX: added permission_classes = [IsAuthenticated])
# ---------------------------------------------------------------------------

class BaseIngestView(APIView):
    """
    DRY base for all three ingest endpoints.
    Subclasses set source_type, source_name, and parser_fn.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    source_type: str = ""
    source_name: str = ""
    parser_fn = None

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        tenant = _get_tenant(request)
        source = _get_or_create_source(tenant, self.source_type, self.source_name)
        job = IngestionJob.objects.create(
            tenant=tenant,
            source=source,
            file_name=file_obj.name,
            status=IngestionJob.STATUS_PROCESSING,
            uploaded_by=request.user,
        )

        try:
            content = file_obj.read()
            with transaction.atomic():
                _ingest_records(content, self.parser_fn, source, job)
        except Exception as exc:
            logger.exception("Ingestion failed for job %s", job.id)
            job.status = IngestionJob.STATUS_FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            job.save()
            return Response(
                {"error": str(exc), "job_id": str(job.id)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(IngestionJobSerializer(job).data, status=status.HTTP_201_CREATED)


class IngestSAPView(BaseIngestView):
    source_type = DataSource.SOURCE_SAP
    source_name = "SAP Procurement"
    parser_fn = staticmethod(parse_sap_csv)


class IngestUtilityView(BaseIngestView):
    source_type = DataSource.SOURCE_UTILITY
    source_name = "Utility Provider"
    parser_fn = staticmethod(parse_utility_csv)


class IngestTravelView(BaseIngestView):
    source_type = DataSource.SOURCE_TRAVEL
    source_name = "Concur Travel"
    parser_fn = staticmethod(parse_travel_csv)


# ---------------------------------------------------------------------------
# Records endpoints
# ---------------------------------------------------------------------------

class RecordListView(APIView):
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    def get(self, request):
        tenant = _get_tenant(request)
        # BUG-05 FIX: was EmissionRecord.objects.all() — no tenant filter.
        # All tenants' data was visible to everyone.
        qs = EmissionRecord.objects.filter(tenant=tenant).select_related(
            "source", "job", "reviewed_by"
        )

        # Filters
        record_status = request.query_params.get("status")
        if record_status:
            qs = qs.filter(status=record_status)

        scope = request.query_params.get("scope")
        if scope:
            try:
                qs = qs.filter(scope=int(scope))
            except ValueError:
                pass

        source_type = request.query_params.get("source_type")
        if source_type:
            qs = qs.filter(source__source_type=source_type)

        date_from = request.query_params.get("date_from")
        if date_from:
            try:
                qs = qs.filter(activity_date__gte=datetime.strptime(date_from, "%Y-%m-%d").date())
            except ValueError:
                pass

        date_to = request.query_params.get("date_to")
        if date_to:
            try:
                qs = qs.filter(activity_date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())
            except ValueError:
                pass

        # Pagination — BUG FIX: added try/except so bad params return 400 not 500
        try:
            page_size = max(1, min(int(request.query_params.get("page_size", 50)), 200))
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            return Response(
                {"error": "page and page_size must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        offset = (page - 1) * page_size
        total = qs.count()
        records = qs[offset : offset + page_size]

        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": EmissionRecordSerializer(records, many=True).data,
            }
        )


class ApproveRecordView(APIView):
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    def patch(self, request, pk):
        tenant = _get_tenant(request)
        try:
            # BUG-05 FIX: scope to tenant so cross-tenant approval is impossible
            record = EmissionRecord.objects.get(pk=pk, tenant=tenant)
        except EmissionRecord.DoesNotExist:
            return Response({"error": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

        if record.is_locked:
            return Response(
                {"error": "Record is locked and cannot be modified."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ApproveRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        before = {"status": record.status, "review_note": record.review_note}

        record.status = EmissionRecord.STATUS_APPROVED
        record.review_note = serializer.validated_data.get("review_note", "")
        record.reviewed_by = request.user
        record.reviewed_at = datetime.now(timezone.utc)
        record.is_locked = True
        record.save()

        AuditLog.objects.create(
            record=record,
            action="APPROVED",
            changed_by=request.user,
            before_data=before,
            after_data={"status": record.status, "review_note": record.review_note},
        )

        return Response(EmissionRecordSerializer(record).data)


class RejectRecordView(APIView):
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    def patch(self, request, pk):
        tenant = _get_tenant(request)
        try:
            # BUG-05 FIX: scope to tenant
            record = EmissionRecord.objects.get(pk=pk, tenant=tenant)
        except EmissionRecord.DoesNotExist:
            return Response({"error": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

        if record.is_locked:
            return Response(
                {"error": "Record is locked and cannot be modified."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = RejectRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        before = {"status": record.status, "review_note": record.review_note}

        record.status = EmissionRecord.STATUS_REJECTED
        record.review_note = serializer.validated_data["review_note"]
        record.reviewed_by = request.user
        record.reviewed_at = datetime.now(timezone.utc)
        # BUG-02 FIX: rejection was not locking the record. A rejected record
        # could be silently re-approved, breaking the audit trail contract.
        record.is_locked = True
        record.save()

        AuditLog.objects.create(
            record=record,
            action="REJECTED",
            changed_by=request.user,
            before_data=before,
            after_data={"status": record.status, "review_note": record.review_note},
        )

        return Response(EmissionRecordSerializer(record).data)


class BulkApproveView(APIView):
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    def post(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"error": "No IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        tenant = _get_tenant(request)
        # BUG-05 FIX: scope to tenant + BUG FIX: evaluate queryset to list ONCE
        # so it isn't re-queried inside bulk_update.
        records = list(
            EmissionRecord.objects.filter(pk__in=ids, tenant=tenant, is_locked=False)
        )
        now = datetime.now(timezone.utc)
        user = request.user

        audit_logs = []
        for record in records:
            before = {"status": record.status}
            record.status = EmissionRecord.STATUS_APPROVED
            record.reviewed_by = user
            record.reviewed_at = now
            record.is_locked = True
            audit_logs.append(
                AuditLog(
                    record=record,
                    action="BULK_APPROVED",
                    changed_by=user,
                    before_data=before,
                    after_data={"status": EmissionRecord.STATUS_APPROVED},
                )
            )

        EmissionRecord.objects.bulk_update(
            records, ["status", "reviewed_by", "reviewed_at", "is_locked"]
        )
        AuditLog.objects.bulk_create(audit_logs)

        return Response({"approved": len(audit_logs)})


# ---------------------------------------------------------------------------
# Audit log endpoint  (BUG-06 FIX: was modelled + serialised but never exposed)
# ---------------------------------------------------------------------------

class RecordAuditLogView(APIView):
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    def get(self, request, pk):
        tenant = _get_tenant(request)
        # Verify the record belongs to this tenant before exposing its log
        try:
            record = EmissionRecord.objects.get(pk=pk, tenant=tenant)
        except EmissionRecord.DoesNotExist:
            return Response({"error": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

        logs = AuditLog.objects.filter(record=record).select_related("changed_by")
        return Response(AuditLogSerializer(logs, many=True).data)


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    def get(self, request):
        tenant = _get_tenant(request)
        # BUG-05 FIX: was EmissionRecord.objects.all() — leaked cross-tenant data
        qs = EmissionRecord.objects.filter(tenant=tenant)

        status_counts = dict(
            qs.values("status").annotate(c=Count("id")).values_list("status", "c")
        )
        scope_counts = dict(
            qs.values("scope").annotate(c=Count("id")).values_list("scope", "c")
        )
        total_kgco2e = qs.aggregate(t=Sum("normalized_quantity"))["t"] or 0

        by_source = list(
            qs.values("source__source_type")
            .annotate(count=Count("id"), total_kgco2e=Sum("normalized_quantity"))
            .values("source__source_type", "count", "total_kgco2e")
        )

        data = {
            "total_records": qs.count(),
            "pending_review": status_counts.get(EmissionRecord.STATUS_PENDING, 0),
            "approved": status_counts.get(EmissionRecord.STATUS_APPROVED, 0),
            "rejected": status_counts.get(EmissionRecord.STATUS_REJECTED, 0),
            "suspicious": status_counts.get(EmissionRecord.STATUS_SUSPICIOUS, 0),
            "scope_1": scope_counts.get(1, 0),
            "scope_2": scope_counts.get(2, 0),
            "scope_3": scope_counts.get(3, 0),
            "by_source": [
                {
                    "source_type": r["source__source_type"],
                    "count": r["count"],
                    "total_kgco2e": float(r["total_kgco2e"] or 0),
                }
                for r in by_source
            ],
            "total_kgco2e": total_kgco2e,
        }

        return Response(data)


# ---------------------------------------------------------------------------
# Jobs list
# ---------------------------------------------------------------------------

class JobListView(APIView):
    permission_classes = [IsAuthenticated]  # BUG-04 FIX

    def get(self, request):
        tenant = _get_tenant(request)
        jobs = IngestionJob.objects.filter(tenant=tenant).select_related(
            "source", "uploaded_by"
        ).order_by("-created_at")[:100]
        return Response(IngestionJobSerializer(jobs, many=True).data)
