from django.urls import path
from .views import (
    IngestSAPView,
    IngestUtilityView,
    IngestTravelView,
    RecordListView,
    ApproveRecordView,
    RejectRecordView,
    BulkApproveView,
    RecordAuditLogView,   # BUG-06 FIX: was never wired up
    DashboardStatsView,
    JobListView,
)

urlpatterns = [
    # Ingestion
    path("ingest/sap/", IngestSAPView.as_view()),
    path("ingest/utility/", IngestUtilityView.as_view()),
    path("ingest/travel/", IngestTravelView.as_view()),

    # Records
    path("records/", RecordListView.as_view()),
    path("records/<uuid:pk>/approve/", ApproveRecordView.as_view()),
    path("records/<uuid:pk>/reject/", RejectRecordView.as_view()),
    path("records/<uuid:pk>/audit-log/", RecordAuditLogView.as_view()),  # BUG-06 FIX
    path("records/bulk-approve/", BulkApproveView.as_view()),

    # Dashboard & jobs
    path("dashboard/stats/", DashboardStatsView.as_view()),
    path("jobs/", JobListView.as_view()),
]
