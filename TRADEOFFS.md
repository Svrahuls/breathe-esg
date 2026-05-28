# BreatheESG — Known Tradeoffs & Not-Built Features

## Three Things Deliberately Not Built

### 1. PDF Utility Bill Parsing

**What it would enable:** Most utility suppliers still send PDF invoices as the
primary document. Parsing PDFs directly would eliminate the need for the analyst
to log into the supplier portal and export a CSV manually — reducing ingestion
friction and enabling processing of historical bills stored as PDFs.

**Why it was not built:**
PDF parsing for utility bills is significantly more complex than CSV ingestion:

- **Layout fragility:** Every supplier uses a different invoice template. EDF,
  British Gas, Eon, and OVO all have distinct layouts, and templates change with
  rebrands. A parser for one supplier breaks silently on another.
- **Tooling overhead:** `pdfplumber`, `camelot`, or `tabula-py` can extract tables
  from structured PDFs, but scanned PDFs (common for older bills) require OCR via
  `pytesseract` or a cloud Vision API, adding latency, cost, and a dependency on
  Google Cloud or AWS Textract.
- **Data quality:** OCR introduces character substitution errors (e.g., `l` vs `1`,
  `O` vs `0`) that are particularly harmful in consumption figures.
- **Regulatory exposure:** Parsing and storing PDF invoices may trigger data
  retention requirements under UK GDPR that don't apply to structured CSV exports.

**How it would be built when prioritised:**
- Use `pdfplumber` for structured PDFs with embedded text.
- Use supplier-specific template matchers (regex on known label positions) rather
  than general-purpose table extraction.
- Fall back to `pytesseract` for scanned images.
- Run extraction in a Celery task queue, not synchronously in the HTTP request.
- Return a confidence score alongside extracted values, surfacing low-confidence
  rows as `SUSPICIOUS` automatically.

---

### 2. Real SAP OData / RFC API Integration

**What it would enable:** Direct pull from a live SAP system via the SAP Gateway
OData service or RFC/BAPI calls would eliminate manual file exports, enable
near-real-time ingestion, and remove the analyst from the data pipeline for
routine uploads.

**Why it was not built:**
- **No SAP sandbox available:** Testing requires a live SAP environment or an
  SAP Cloud Appliance Library instance (~$150/month). This is not justified for
  a prototype.
- **Configuration complexity:** SAP Gateway requires activating OData services
  in transaction `/IWFND/MAINT_SERVICE`, creating a communication user, and
  opening RFC firewall ports — all requiring SAP Basis team involvement that
  cannot be self-served.
- **Authentication:** SAP uses Basic Auth over RFC or OAuth 2.0 SAML Bearer
  Assertion for OData — both require client-specific credentials that cannot be
  abstracted away without a customer implementation project.
- **Schema variability:** SAP material documents (table MSEG/MKPF) vary by
  client configuration. Field-level mapping would need to be validated against
  each client's SAP system individually.

**How it would be built when prioritised:**
- Use `pyrfc` (SAP PyRFC) to call `BAPI_GOODSMVT_GETDETAIL` or query MSEG/MKPF
  directly via RFC.
- Alternatively, use `python-zeep` against the SAP SOAP web service
  `MaterialDocument.ReadMultiple`.
- Schedule via Celery Beat to pull delta records since last run using the
  `BUDAT` (posting date) filter.
- Store the SAP connection credentials in Django Vault or AWS Secrets Manager,
  never in environment variables.

---

### 3. Multi-User Authentication with Role-Based Access Control

**What it would enable:** In a production ESG platform, different users have
different permissions:
- **Analyst** — can view and review records, cannot approve locked records
- **Senior Analyst / Manager** — can approve and bulk approve
- **Auditor** — read-only access to records and audit logs
- **Admin** — tenant configuration, user management
- **API Service Account** — machine-to-machine ingestion

**Why it was not built:**
- The prototype uses a single "default" tenant and treats all API calls as
  having analyst-level permissions. Adding RBAC adds significant complexity
  (middleware, permission classes, UI role guards) that would obscure the
  core data ingestion and normalisation logic — which is the primary
  demonstrable value.
- JWT or session authentication requires frontend auth flows (login page,
  token refresh, protected routes) that are boilerplate and do not differentiate
  the product.
- For the prototype review, the data pipeline is more important to evaluate than
  the auth system.

**How it would be built when prioritised:**
- Use `djangorestframework-simplejwt` for stateless JWT authentication.
- Define permission classes (`IsAnalyst`, `IsSeniorAnalyst`, `IsAuditor`) using
  DRF's `BasePermission`.
- Add a `UserProfile` model linking `auth.User` to a `Tenant` and a `role` field.
- On the frontend, use React Context + protected `<Route>` wrappers to gate
  pages and action buttons by role.
- For the bulk approve endpoint, require `IsSeniorAnalyst` or above.

---

## Additional Known Limitations

| Area | Limitation | Mitigation in prototype |
|---|---|---|
| Async processing | File ingestion is synchronous in the HTTP request | Acceptable for CSV files <5 MB; Celery would be needed for large files |
| Emission factor versioning | Factors are hardcoded in parsers | Moving to a `EmissionFactor` model with `valid_from`/`valid_to` dates is the first production upgrade |
| Currency normalisation | Travel amounts stored as-is in source currency | Not needed until financial reporting is added |
| Timezone handling | All dates stored as UTC | Activity dates (not datetimes) avoid most tz issues |
| Test coverage | Unit tests not included in prototype | Parsers are pure functions — straightforward to test with `pytest` |
