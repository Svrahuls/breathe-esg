# BreatheESG — Data Model Documentation

## Overview

The data model is designed around three concerns:
1. **Source fidelity** — never mutate the original data
2. **Audit correctness** — every change is traceable
3. **Multi-tenancy** — multiple organisations share one deployment safely

---

## Models

### `Tenant`

The root of the ownership hierarchy. Every other model is scoped to a tenant,
ensuring data is never visible across organisation boundaries.

```
id          UUID PK
name        "Acme Corp"
slug        "acme-corp"  (URL-safe identifier)
created_at
```

**Why multi-tenancy?** ESG platforms are almost always sold as SaaS to multiple
corporate clients. Adding tenancy from day one is far cheaper than retrofitting
it later. The `tenant` FK on every model means a simple `filter(tenant=request.tenant)`
in every query is sufficient to enforce isolation — no row-level security
policies or separate schemas needed for the prototype.

---

### `DataSource`

Represents a configured data feed (e.g. "Site A SAP export", "Office electricity account").

```
id          UUID PK
tenant      FK → Tenant
source_type ENUM  SAP | UTILITY | TRAVEL
name        Human-readable label
created_at
```

The `source_type` drives which parser is invoked and which GHG scope is
assigned to resulting records. One tenant can have multiple sources of the
same type (e.g., separate SAP mandants for UK and Germany).

---

### `IngestionJob`

One job = one file upload. Acts as the provenance anchor for a batch of
`EmissionRecord` rows.

```
id              UUID PK
tenant          FK → Tenant
source          FK → DataSource (nullable, preserved if source deleted)
uploaded_by     FK → auth.User (nullable)
file_name       Original filename
status          PENDING | PROCESSING | DONE | FAILED
total_rows      Count of rows in file
success_rows    Rows that parsed and normalised cleanly
failed_rows     Rows that could not be parsed at all
suspicious_rows Rows parsed but flagged for analyst review
duplicate_rows  Rows skipped as MD5 duplicates
error_message   Top-level error if status=FAILED
created_at
completed_at
```

Jobs are immutable once completed. Re-uploading the same file creates a new job;
duplicate rows are detected by `source_hash` and skipped, so re-uploading is
idempotent with respect to the record store.

---

### `EmissionRecord`

The core entity. Holds both the original row (for audit) and the normalised
emission quantity (for reporting).

#### Source-of-Truth Fields

| Field | Purpose |
|---|---|
| `raw_data` | Full original CSV row as JSON — never modified after write |
| `source_hash` | MD5 of the canonical string of `raw_data` — used for deduplication |

These two fields together mean an analyst can always trace a normalised number
back to the exact byte sequence in the source file. `raw_data` is stored as
PostgreSQL `jsonb`, which supports indexed queries on specific fields.

The `source_hash` dedup check operates at two levels:
- **Intra-file**: within a single parse run, a `seen_hashes` set prevents
  duplicate rows in the same file from being written.
- **Cross-file**: before writing, existing hashes for the tenant are loaded
  and checked, so re-uploading a file or uploading overlapping exports is safe.

#### Normalised Fields

| Field | Description |
|---|---|
| `normalized_quantity` | Emission value in kgCO₂e |
| `normalized_unit` | Always `"kgCO2e"` for comparability |

Normalisation formulas are in the parsers (see `ingestion/parsers/`). The raw
unit and quantity are preserved in `raw_data`, so the formula can be audited
or re-run if emission factors are updated.

#### GHG Scope Classification

| Scope | Assignment | Rationale |
|---|---|---|
| **Scope 1** | SAP fuel records | Direct combustion — company owns the source |
| **Scope 2** | Utility electricity records | Purchased energy, indirect at point of use |
| **Scope 3** | Travel records | Value-chain activity (GHG Protocol Cat. 6) |

Scope is set by the parser, not the analyst, because it is determined by the
physical nature of the emission source rather than any business judgement.

#### Category

Fine-grained activity type within a scope:
- `fuel` — combustion of diesel, petrol, natural gas, LPG
- `electricity` — grid electricity consumption
- `flight` — air travel (short or long haul)
- `hotel` — accommodation nights
- `ground` — road or rail transport

#### Review Workflow

```
PENDING_REVIEW → APPROVED  (analyst signs off)
PENDING_REVIEW → REJECTED  (analyst rejects with mandatory note)
SUSPICIOUS     → APPROVED  (analyst reviews anomaly and approves)
SUSPICIOUS     → REJECTED  (analyst rejects anomalous record)
```

`SUSPICIOUS` is set by the parser when a data quality rule fires (see parser
docs). Analysts can approve suspicious records if they have supporting
context (e.g., a long billing period due to a meter read backlog).

#### Audit Lock

When a record is `APPROVED`, `is_locked = True` is set atomically. Locked
records cannot be modified via the API. This enforces an audit trail:
once a number enters the verified dataset it cannot silently change. If a
correction is needed, the correct approach is to reject the record and create
a new one from a corrected source file.

---

### `AuditLog`

An append-only log of every status change on an `EmissionRecord`.

```
id          UUID PK
record      FK → EmissionRecord
action      "APPROVED" | "REJECTED" | "BULK_APPROVED"
changed_by  FK → auth.User
changed_at  Timestamp (auto)
before_data JSON snapshot of fields before change
after_data  JSON snapshot of fields after change
```

`before_data` and `after_data` capture `status` and `review_note` so a
compliance auditor can reconstruct the full review history of any record
without relying on the live model state.

---

## Unit Normalisation

All records are converted to **kgCO₂e** (kilograms of CO₂ equivalent) using
published emission factors from DEFRA (UK) and the GHG Protocol.

### SAP (Scope 1 Fuel)

| MEINS | Fuel | Factor | Source |
|---|---|---|---|
| L / LTR | Diesel | 2.68 kgCO₂e/litre | DEFRA 2023 |
| L / LTR | Petrol | 2.31 kgCO₂e/litre | DEFRA 2023 |
| M3 | Natural gas | 2.04 kgCO₂e/m³ | DEFRA 2023 |
| KG | LPG | 1.51 kgCO₂e/kg | DEFRA 2023 |
| KL | Diesel | 2,680 kgCO₂e/kilolitre | Derived |

Fuel type is inferred from the SAP material code prefix (e.g., `DSL*` → diesel).

### Utility (Scope 2 Electricity)

```
kgCO₂e = consumption_kWh × (carbon_intensity_gCO₂_per_kWh / 1000)
```

If `carbon_intensity_gco2_per_kwh` is missing or zero, the UK 2023 grid
average of **233 gCO₂/kWh** is used and the record is flagged with
`DEFAULT_CARBON_INTENSITY` for analyst review.

### Travel (Scope 3 — GHG Protocol Category 6)

| Type | Factor | Class Multiplier |
|---|---|---|
| Short-haul flight (<1,500 km) | 0.255 kgCO₂e/km | ×1.0 economy, ×1.54 business, ×2.40 first |
| Long-haul flight (≥1,500 km) | 0.195 kgCO₂e/km | same multipliers |
| Hotel | 31.0 kgCO₂e/night | — |
| Ground transport | 0.171 kgCO₂e/km | ×1.0 standard |

Factors from DEFRA 2023 and the GHG Protocol Scope 3 Evaluator.
