# BreatheESG — Architecture & Design Decisions

## Data Source Format Choices

### SAP: Flat File CSV instead of IDoc / OData

SAP offers several integration patterns for data extraction:
- **IDoc (Intermediate Document)** — EDI-style structured messages, complex to parse,
  requires an ALE/EDI middleware layer.
- **OData API (SAP Fiori / Gateway)** — REST-like, requires SAP Gateway configuration
  and a service account with BAPI access, often blocked by corporate firewalls.
- **BAPI RFC calls** — Real-time via RFC, requires SAP JCo connector and network access.
- **Flat file / ABAP report export** — A scheduled ABAP job or transaction SE16/MB51
  exports a CSV or delimited text file. This is the most common way data actually
  leaves SAP in mid-market and even large enterprise contexts.

**Decision: Flat file CSV.**

Reasoning:
1. The vast majority of ESG data requests to finance/procurement teams result in
   an emailed CSV, not a live API connection.
2. Flat file requires zero SAP system configuration from the client.
3. The MB51 (material document list) and ME2M (purchase orders by material)
   standard transactions produce the exact column set we parse.
4. For a prototype, this unblocks development immediately — no SAP sandbox needed.

**What we handle:** Procurement/fuel data from MM (Materials Management) module —
specifically fuel purchases via purchase orders (MB51 format). We do **not** handle:
- HR module (employee travel expense reports — that's Concur's domain)
- FI-GL (general ledger postings — too aggregated for activity-based accounting)
- PP (production orders — out of scope for a fuel-only Scope 1 implementation)

---

### Utility: CSV instead of PDF invoice

Utility suppliers issue PDF invoices. Some also offer CSV exports from their
online portal or via a data feed.

**Decision: CSV from utility portal.**

Reasoning:
1. All major UK suppliers (EDF, British Gas, Eon, OVO) provide CSV exports from
   their business portals with structured consumption and carbon intensity data.
2. PDF parsing requires OCR or `pdfplumber` — fragile, font-dependent, and each
   supplier uses a different invoice layout (see TRADEOFFS.md).
3. The CSV format we handle matches the ESOS (Energy Savings Opportunity Scheme)
   reporting format, making it familiar to energy managers.

The `carbon_intensity_gco2_per_kwh` column uses Elexon/National Grid data that
UK suppliers are now required to provide on bills. For sites without this column,
we fall back to the DEFRA national grid average (233 gCO₂/kWh for 2023).

---

### Travel: Concur CSV instead of Concur API

Concur (SAP Concur) offers a TripLink API and an Expense API with OAuth 2.0 flows.

**Decision: Concur report export CSV.**

Reasoning:
1. Concur API OAuth requires: company OAuth app registration, admin approval, and
   a service account — a multi-week procurement process for a prototype.
2. Expense approvers routinely export "Trip Report" or "Expense Report" CSVs from
   the Concur UI for finance reconciliation. This is a known, stable format.
3. Our column set (`employee_id`, `trip_date`, `travel_type`, `origin`,
   `destination`, `distance_km`, etc.) maps directly to the standard Concur
   Travel Detail Report columns available without customisation.

For production, we would replace this with the Concur Travel Request API
(`/travelrequest/v4/requests`) which provides structured JSON with distance
and emission estimates directly from SAP Concur's own carbon module.

---

## Questions We Would Ask the PM Before Production

### 1. Tenant Setup
- How are tenants onboarded — self-service or admin-provisioned?
- Is there a hierarchy (e.g., subsidiary companies under a parent)?
- Should emission factors be configurable per tenant or global?

### 2. Emission Factor Source
- Which official factor set takes precedence: DEFRA, EPA, IPCC AR6, or custom?
- How often should factors be updated, and who approves factor changes?
- Should records be re-normalised automatically when factors change, or preserved
  at the historical factor with a flag?

### 3. Approval Workflow
- Is single-analyst approval sufficient, or is a 4-eyes (dual approval) required
  for high-value records?
- Should approved records ever be unlockable (e.g., for year-end corrections)?
- Who has authority to bulk approve — any analyst, or only senior reviewers?

### 4. Reporting Scope
- Are we reporting to GHG Protocol, ISO 14064, TCFD, or a custom framework?
- Which boundary applies — operational control, equity share, or financial control?
- Do we need to split Scope 2 into market-based vs location-based?

### 5. Integration Timeline
- When does SAP OData integration become a priority vs continued flat file?
- Is there a requirement to integrate with the client's existing CSRD/ESG reporting
  tool (e.g., Workiva, Watershed, Persefoni)?
