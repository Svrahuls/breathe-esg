"""
SAP Flat File Parser
--------------------
Handles the common SAP procurement/fuel CSV export format.
Columns: MANDT, BUKRS, BELNR, BLDAT, MATNR, MENGE, MEINS, WERKS, LIFNR, DMBTR, WAERS

Scope 1 — direct fuel combustion.
Emission factors (kgCO2e per unit):
  - L   (Liter)       → diesel 2.68, petrol 2.31  — material code determines fuel type
  - M3  (cubic metre) → natural gas 2.04
  - KG  (kilogram)    → LPG 1.51
  - KWH (kWh)         → treated as Scope 1 on-site generation → 0.233 kgCO2e/kWh

If unit not recognised, quantity is stored with normalized_quantity=None and
status set to SUSPICIOUS so an analyst can review.
"""

import csv
import hashlib
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Generator

logger = logging.getLogger("ingestion")

# Map SAP material codes (MATNR prefix) to fuel type
MATNR_FUEL_MAP = {
    "DSL": "diesel",
    "DIES": "diesel",
    "PTL": "petrol",
    "PETR": "petrol",
    "GAS": "natural_gas",
    "NGAS": "natural_gas",
    "LPG": "lpg",
}

EMISSION_FACTORS = {
    # unit → {fuel_type → kgCO2e}
    "L": {"diesel": Decimal("2.68"), "petrol": Decimal("2.31"), "default": Decimal("2.68")},
    "LTR": {"diesel": Decimal("2.68"), "petrol": Decimal("2.31"), "default": Decimal("2.68")},
    "KL": {"diesel": Decimal("2680"), "petrol": Decimal("2310"), "default": Decimal("2680")},  # kilolitre
    "M3": {"natural_gas": Decimal("2.04"), "default": Decimal("2.04")},
    "KG": {"lpg": Decimal("1.51"), "default": Decimal("1.51")},
    "KWH": {"default": Decimal("0.233")},
}


def _detect_fuel(matnr: str) -> str:
    """Guess fuel type from SAP material code."""
    matnr_upper = (matnr or "").upper()
    for prefix, fuel in MATNR_FUEL_MAP.items():
        if matnr_upper.startswith(prefix):
            return fuel
    return "diesel"  # conservative default


def _parse_date(date_str: str):
    """Parse SAP date format DD.MM.YYYY, also handle YYYY-MM-DD."""
    if not date_str or not date_str.strip():
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _row_hash(row: dict) -> str:
    """MD5 hash of raw row dict for deduplication."""
    canonical = "|".join(f"{k}={v}" for k, v in sorted(row.items()))
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


def parse_sap_csv(file_content: bytes) -> Generator[dict, None, None]:
    """
    Parse SAP flat file CSV and yield normalised record dicts.

    Each yielded dict has keys matching the fields expected by the ingestion
    view: raw_data, source_hash, normalized_quantity, normalized_unit,
    scope, category, activity_date, location, description, status, flags.
    """
    text = file_content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    required_cols = {"MANDT", "BUKRS", "BELNR", "BLDAT", "MATNR", "MENGE", "MEINS", "WERKS"}

    headers = set(reader.fieldnames or [])
    missing = required_cols - headers
    if missing:
        logger.warning("SAP CSV missing expected columns: %s", missing)

    seen_hashes: set[str] = set()

    for row_num, row in enumerate(reader, start=2):
        raw = dict(row)
        h = _row_hash(raw)

        flags = []
        is_duplicate = h in seen_hashes
        if is_duplicate:
            flags.append("DUPLICATE")
        seen_hashes.add(h)

        # Parse quantity
        menge_raw = raw.get("MENGE", "").strip().replace(",", ".")
        try:
            menge = Decimal(menge_raw)
        except (InvalidOperation, ValueError):
            menge = None
            flags.append("INVALID_QUANTITY")

        if menge is not None and menge <= 0:
            flags.append("ZERO_OR_NEGATIVE")

        # Parse unit and compute emission factor
        meins = (raw.get("MEINS") or "").strip().upper()
        matnr = (raw.get("MATNR") or "").strip()
        fuel = _detect_fuel(matnr)

        ef_map = EMISSION_FACTORS.get(meins)
        if ef_map is None:
            emission_factor = None
            flags.append("UNKNOWN_UNIT")
        else:
            emission_factor = ef_map.get(fuel) or ef_map.get("default")

        # Compute normalized quantity
        if menge is not None and emission_factor is not None:
            normalized_qty = menge * emission_factor
        else:
            normalized_qty = None
            flags.append("CANNOT_NORMALIZE")

        # Parse date
        bldat = _parse_date(raw.get("BLDAT", ""))

        # Status
        suspicious = bool(
            flags
            and any(f in flags for f in ("ZERO_OR_NEGATIVE", "UNKNOWN_UNIT", "CANNOT_NORMALIZE"))
        )
        if is_duplicate:
            status = "DUPLICATE"
        elif suspicious:
            status = "SUSPICIOUS"
        else:
            status = "PENDING_REVIEW"

        yield {
            "raw_data": raw,
            "source_hash": h,
            "normalized_quantity": normalized_qty,
            "normalized_unit": "kgCO2e",
            "scope": 1,
            "category": "fuel",
            "activity_date": bldat,
            "location": raw.get("WERKS", ""),
            "description": (
                f"SAP doc {raw.get('BELNR', '')} | "
                f"Material: {matnr} | "
                f"Amount: {raw.get('DMBTR', '')} {raw.get('WAERS', '')}"
            ),
            "status": status,
            "flags": flags,
            "row_num": row_num,
        }
