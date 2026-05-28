# BreatheESG — Real-World Research & Source References

## SAP Flat File Format

### SAP MM Document Structure
The SAP Materials Management (MM) module records fuel procurement through
purchase orders (ME21N) and goods receipts (MIGO). The resulting material
documents are stored across two tables:

- **MKPF** — Material document header (posting date `BUDAT`, document date
  `BLDAT`, company code `BUKRS`, plant `WERKS`)
- **MSEG** — Material document line items (material `MATNR`, quantity `MENGE`,
  unit `MEINS`, vendor `LIFNR`, amount `DMBTR`, currency `WAERS`)

Transaction **MB51** (Material Documents List) joins these tables and produces
exactly the column set we parse. Finance teams routinely export MB51 as a
spreadsheet for fuel cost reconciliation.

### SAP Unit of Measure Codes (MEINS)
SAP stores units in ISO UNIT codes from table T006/T006A:
- `L` — Litre (ISO: LTR)
- `M3` — Cubic metre
- `KG` — Kilogram  
- `KL` — Kilolitre (1,000 litres)
- `GAL` — US gallon (3.785 litres)
- `ST` — Each (piece) — not a volume unit; triggers `UNKNOWN_UNIT` flag

Reference: SAP Help Portal — [Units of Measurement](https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/7b5e4e98c3234e7b9da1bc543be7fced/3b7c5e5a5a0b4fafb08cae8ef2b4d7e2.html)

### SAP Material Code Conventions
Material numbers (MATNR) are client-defined (up to 40 chars, alphanumeric).
In practice, most organisations follow naming conventions that embed the
material type in the prefix. Common conventions for fuels:
- `DSL-*` or `DIES-*` — Diesel
- `PTL-*` or `PETR-*` — Petrol/Gasoline
- `GAS-*` or `NGAS-*` — Natural gas
- `LPG-*` — Liquefied petroleum gas

Our parser reads these prefixes. If the convention differs, the `MATNR_FUEL_MAP`
in `ingestion/parsers/sap.py` can be extended without changing the parser logic.

### DEFRA Greenhouse Gas Conversion Factors (2023)
The emission factors for fuel combustion are taken from:
> Department for Environment, Food & Rural Affairs (DEFRA).
> *Greenhouse gas reporting: conversion factors 2023.*
> Published June 2023.
> https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023

Relevant figures (kgCO₂e per unit, gross calorific value):
- Diesel: 2.68 kgCO₂e/litre
- Petrol: 2.31 kgCO₂e/litre
- Natural gas: 2.04 kgCO₂e/m³
- LPG: 1.51 kgCO₂e/kg

---

## Utility / Electricity Format

### UK Utility Portal CSV Formats
Major UK business electricity suppliers offer CSV data exports from their
online portals. The column set varies slightly but consistently includes:
- Account/meter identifiers
- Billing period start and end dates
- Consumption in kWh
- Tariff unit rate
- Total charge in GBP

**EDF Energy Business Portal** — exports "Consumption History" CSV with columns
`Site Reference`, `Meter Serial`, `Read Date From`, `Read Date To`, `kWh`.

**British Gas Business** — "Usage Data" export with `Account Number`,
`Meter Point Reference Number (MPRN)`, `Supply Start`, `Supply End`, `Units`.

**Octopus Energy / Eon** — Similar formats following the RECo (Retail Energy
Code) data sharing standard.

### Carbon Intensity Data
The `carbon_intensity_gco2_per_kwh` column uses data from:

**National Grid ESO / Elexon Carbon Intensity API**
> https://carbonintensity.org.uk
> Real-time and forecast carbon intensity for the UK National Grid.
> Regional and national figures in gCO₂/kWh.

UK suppliers are increasingly required under ESOS Phase 3 to include carbon
intensity on invoices. The national average for 2023 was approximately
**233 gCO₂/kWh** (down from 281 in 2020, reflecting renewable growth).

**DEFRA 2023 — Scope 2 Electricity:**
- UK grid average (location-based): 0.21233 kgCO₂e/kWh = 212.33 gCO₂/kWh
- We use 233 gCO₂/kWh as a conservative default (DEFRA T&D losses included).

Reference: DEFRA 2023 Conversion Factors, Table: Electricity — UK.

---

## Travel / Concur CSV Format

### SAP Concur TripLink Format
Concur's standard **Travel Detail Report** (accessible via Reports > Standard
Reports > Travel > Travel Detail) exports columns including:
- `Employee ID`, `Employee Name`
- `Trip Start Date`, `Trip End Date`
- `Transportation Type` (Air, Hotel, Car, Rail)
- `Origin City/Airport`, `Destination City/Airport`
- `Distance` (miles or km, depending on locale setting)
- `Booking Class` (Economy, Business, First)
- `Total Amount`, `Currency`

Our parser uses a simplified version of this schema, mapping:
- `travel_type` ← `Transportation Type` normalised to `flight`/`hotel`/`ground`
- `transport_class` ← `Booking Class` lowercased

For distance, Concur can calculate it automatically from airport codes using
the Haversine formula if the `Display Trip Mileage` setting is enabled in
the company configuration. When this is disabled, `distance_km` will be empty
— which is why we flag missing distances as `SUSPICIOUS` rather than failing.

Reference: SAP Concur — [Standard Report Definitions](https://www.concurtraining.com/customers/tech_pubs/Docs/_Current/UG_Std/UG_Std_Rpt_Travel.pdf)

### GHG Protocol — Scope 3 Category 6: Business Travel
The GHG Protocol Scope 3 Evaluator and the Corporate Value Chain Standard
define business travel emissions under Category 6 of Scope 3.

Recommended approach: **Activity-based** method using distance and emission
factors by transport mode and class.

> GHG Protocol. *Technical Guidance for Calculating Scope 3 Emissions.*
> Version 1.0, 2013. Category 6: Business Travel.
> https://ghgprotocol.org/scope-3-technical-guidance

### DEFRA 2023 — Travel Emission Factors

**Aviation (passenger, per km, including radiative forcing):**
- Domestic (≤ 463 km): 0.24476 kgCO₂e/passenger-km (economy)
- Short-haul international (≤ 3,700 km): 0.15353 kgCO₂e/pkm (economy)
- Long-haul (> 3,700 km): 0.19085 kgCO₂e/pkm (economy)
- Business class multiplier: ×1.54
- First class multiplier: ×2.40

We use a simplified two-band model (short < 1,500 km, long ≥ 1,500 km) with
factors 0.255 and 0.195 respectively — conservative estimates that include
radiative forcing (a 1.9× uplift on CO₂ alone, per DEFRA methodology).

**Accommodation:**
- Hotel (UK average): 31.0 kgCO₂e/room-night
  Source: DEFRA 2023, Table: Hotels.

**Ground Transport:**
- Average car (unknown fuel): 0.17138 kgCO₂e/km
  Source: DEFRA 2023, Table: Business travel — land.
- We use 0.171 kgCO₂e/km as representative for ground transport.

### Class Multipliers
Source: DEFRA 2023 Passenger Transport Methodology Paper, Section 5.3.
Economy/standard = baseline (×1.0). Business = ×1.54. First = ×2.40.
These account for the larger seat pitch and floor area per passenger,
meaning fewer passengers per aircraft for the same fuel burn.
