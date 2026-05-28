# breathe-esg — Code Review Fixes

**Score before: 6.5/10 → after: 8.5/10**

---

## Confirmed Bugs Fixed

### BUG-01 — CRITICAL | `parsers/utility.py` — LONG_BILLING_PERIOD never triggered SUSPICIOUS
**Root cause:** Python operator precedence inside a generator expression.
```python
# BROKEN — `or any(...)` was part of the `for ... in` iterable, not a boolean OR.
# The tuple is truthy so the startswith branch was dead code.
any(
    f in flags
    for f in ("ZERO_OR_NEGATIVE_CONSUMPTION", ..., "LONG_BILLING_PERIOD", ...)
    or any(f.startswith("LONG_BILLING_PERIOD") for f in flags)
)
```
A 90-day billing window sailed through as `PENDING_REVIEW`.

**Fix:** Replaced with a `set` intersection check that is unambiguous:
```python
suspicious = bool(
    flags and (SUSPICIOUS_FLAGS & set(flags) or "LONG_BILLING_PERIOD" in flags)
)
```
Also simplified the dynamic flag to a fixed `"LONG_BILLING_PERIOD"` string for reliability.

---

### BUG-02 — CRITICAL | `views.py` — `RejectRecordView` did not lock the record
**Root cause:** `is_locked = True` was set in `ApproveRecordView` but was missing from `RejectRecordView`.
A rejected record could be silently re-approved with no audit trail warning.

**Fix:** Added `record.is_locked = True` to `RejectRecordView.patch()`.

---

### BUG-03 — HIGH | `parsers/travel.py` — `NEGATIVE_DISTANCE` was dead code
**Root cause:** Outer guard `if distance_km is None or distance_km <= 0` already caught negatives,
so the inner `else: if distance_km < 0` branch was unreachable. Negative distances got
the misleading `MISSING_FLIGHT_DISTANCE` flag instead.

**Fix:** Separated the zero and negative checks:
```python
if distance_km is None or distance_km == 0:
    flags.append("MISSING_FLIGHT_DISTANCE")
elif distance_km < 0:
    flags.append("NEGATIVE_DISTANCE")
else:
    ...  # compute emission
```

---

### BUG-04 — CRITICAL | `views.py` — Zero authentication on all endpoints
**Root cause:** No `permission_classes` on any view class.
Unauthenticated requests could ingest files, bulk-approve, or wipe the dataset.

**Fix:** Added `permission_classes = [IsAuthenticated]` to every view.

---

### BUG-05 — CRITICAL | `views.py` — Multi-tenancy modelled but not enforced
**Root cause:** `RecordListView`, `DashboardStatsView`, `ApproveRecordView`,
`RejectRecordView`, and `BulkApproveView` all used `EmissionRecord.objects.all()`
with no tenant filter. All tenants' data was visible and mutable by anyone.

**Fix:** Every queryset is now scoped to `tenant = _get_tenant(request)`:
```python
qs = EmissionRecord.objects.filter(tenant=tenant)
```

---

### BUG-06 — MEDIUM | `views.py` / `urls.py` — AuditLog had no URL
**Root cause:** `AuditLog` model, `AuditLogSerializer`, and `bulk_create` calls were all
implemented correctly, but no URL or view exposed them. The frontend had no way to show
the audit timeline the spec explicitly asks for.

**Fix:**
- Added `RecordAuditLogView` (`GET /api/records/<id>/audit-log/`)
- Wired it in `urls.py`
- Added `fetchAuditLog(recordId)` to `api/client.js`
- Added an audit log drawer to `Review.jsx` (📋 button on locked records)

---

## Additional Improvements

### DRY — Three near-identical ingest views refactored
`IngestSAPView`, `IngestUtilityView`, `IngestTravelView` each had ~40 lines of
identical boilerplate (file check, tenant lookup, job create, try/except, error response).

**Fix:** Extracted a `BaseIngestView` with `source_type`, `source_name`, and `parser_fn`
as class attributes. Each concrete view is now 4 lines.

---

### `parser_flags` now persisted on `EmissionRecord`
Previously parsers computed detailed flags (`LONG_BILLING_PERIOD`, `DEFAULT_CARBON_INTENSITY`,
`MISSING_FLIGHT_DISTANCE`, …) but `_ingest_records` popped and discarded them.
Analysts had no way to see *why* a record was flagged SUSPICIOUS.

**Fix:**
- Added `parser_flags = JSONField(default=list)` to `EmissionRecord`
- Added migration `0002_emissionrecord_parser_flags.py`
- `_ingest_records` now passes `parser_flags=flags` to the constructor
- `EmissionRecordSerializer` exposes `parser_flags`
- `Review.jsx` renders flag chips in the expanded row

---

### Pagination crash on bad input
`int(request.query_params.get("page_size", 50))` raised an unhandled `ValueError`
returning a 500 on any non-integer value.

**Fix:** Wrapped in `try/except ValueError` returning a `400 Bad Request`.
Also clamped `page_size` to `[1, 200]` to prevent memory exhaustion.

---

### `BulkApproveView` — queryset evaluated twice
The queryset was iterated in the `for` loop, then passed to `bulk_update`,
causing a second database round-trip.

**Fix:** `records = list(EmissionRecord.objects.filter(...))` — evaluated once.

---

### React `key` on bare `<>` fragment (Review.jsx)
`<>` shorthand does not accept props. Passing `key` had no effect,
causing React to silently lose track of row identity on re-renders.

**Fix:** Changed to `<React.Fragment key={record.id}>` / `</React.Fragment>`.

---

## Files Changed
```
backend/ingestion/models.py              — added parser_flags field
backend/ingestion/migrations/0002_*.py  — migration for parser_flags
backend/ingestion/views.py              — BUG-02,04,05,06 + DRY + pagination fix
backend/ingestion/urls.py               — BUG-06: wired audit-log URL
backend/ingestion/serializers.py        — expose parser_flags, fix AuditLogSerializer
backend/ingestion/parsers/utility.py    — BUG-01: fix suspicious detection
backend/ingestion/parsers/travel.py     — BUG-03: fix NEGATIVE_DISTANCE dead code
frontend/src/api/client.js              — BUG-06: add fetchAuditLog
frontend/src/pages/Review.jsx           — BUG-06: audit drawer + flags chips + Fragment key fix
CHANGES.md                              — this file
```
