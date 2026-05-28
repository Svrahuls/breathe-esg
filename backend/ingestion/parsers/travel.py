"""
Travel (Concur-style) CSV Parser
----------------------------------
Handles Concur TripLink / expense report CSV exports.
Columns: employee_id, trip_date, travel_type, origin, destination,
         distance_km, nights, transport_class, amount_usd, currency

Scope 3, Category 6 (Business Travel) per GHG Protocol.

Emission factors (kgCO2e):
  - short_haul_flight (<1500 km):  0.255 kgCO2e/km
  - long_haul_flight  (>=1500 km): 0.195 kgCO2e/km
  - hotel:                         31.0  kgCO2e/night
  - ground transport:              0.171 kgCO2e/km  (car/rail average)

Class multipliers (DEFRA 2023):
  - economy / standard: ×1.0
  - business:           ×1.54
  - first:              ×2.40

SUSPICIOUS if:
  - flight with no distance_km (zero or missing)
  - negative distance
  - hotel with nights <= 0
  - unknown travel_type
"""

import csv
import hashlib
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Generator

logger = logging.getLogger("ingestion")

SHORT_HAUL_KM = Decimal("1500")

FLIGHT_FACTORS = {
    "short": Decimal("0.255"),
    "long": Decimal("0.195"),
}

HOTEL_FACTOR = Decimal("31.0")
GROUND_FACTOR = Decimal("0.171")

CLASS_MULTIPLIERS = {
    "economy": Decimal("1.0"),
    "standard": Decimal("1.0"),
    "coach": Decimal("1.0"),
    "business": Decimal("1.54"),
    "first": Decimal("2.40"),
    "premium": Decimal("1.26"),
}

TRAVEL_TYPES = {"flight", "hotel", "ground"}

SUSPICIOUS_FLAGS = {
    "MISSING_FLIGHT_DISTANCE",
    "MISSING_GROUND_DISTANCE",
    "MISSING_OR_ZERO_NIGHTS",
    "NEGATIVE_DISTANCE",
    "UNKNOWN_TRAVEL_TYPE",
}


def _parse_date(date_str: str):
    if not date_str or not date_str.strip():
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(val: str):
    try:
        return Decimal(val.strip().replace(",", "")) if val and val.strip() else None
    except (InvalidOperation, AttributeError):
        return None


def _row_hash(row: dict) -> str:
    canonical = "|".join(f"{k}={v}" for k, v in sorted(row.items()))
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


def parse_travel_csv(file_content: bytes) -> Generator[dict, None, None]:
    """
    Parse Concur-style travel CSV and yield normalised record dicts.
    """
    text = file_content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    seen_hashes: set[str] = set()

    for row_num, row in enumerate(reader, start=2):
        raw = dict(row)
        h = _row_hash(raw)

        flags = []
        is_duplicate = h in seen_hashes
        if is_duplicate:
            flags.append("DUPLICATE")
        seen_hashes.add(h)

        travel_type = (raw.get("travel_type") or "").strip().lower()
        if travel_type not in TRAVEL_TYPES:
            flags.append("UNKNOWN_TRAVEL_TYPE")

        distance_km = _parse_decimal(raw.get("distance_km", ""))
        nights_raw = _parse_decimal(raw.get("nights", ""))

        transport_class = (raw.get("transport_class") or "economy").strip().lower()
        class_multiplier = CLASS_MULTIPLIERS.get(transport_class, Decimal("1.0"))

        normalized_qty = None
        category = "flight"

        if travel_type == "flight":
            category = "flight"
            if distance_km is None or distance_km == 0:
                flags.append("MISSING_FLIGHT_DISTANCE")
            elif distance_km < 0:
                # BUG FIX: previously this branch was unreachable because the outer
                # condition checked `<= 0`, so negative values were already caught
                # by MISSING_FLIGHT_DISTANCE and NEGATIVE_DISTANCE was never set.
                # Now we check zero and negative separately for accurate flagging.
                flags.append("NEGATIVE_DISTANCE")
            else:
                factor = (
                    FLIGHT_FACTORS["short"]
                    if distance_km < SHORT_HAUL_KM
                    else FLIGHT_FACTORS["long"]
                )
                normalized_qty = distance_km * factor * class_multiplier

        elif travel_type == "hotel":
            category = "hotel"
            if nights_raw is None or nights_raw <= 0:
                flags.append("MISSING_OR_ZERO_NIGHTS")
            else:
                normalized_qty = nights_raw * HOTEL_FACTOR

        elif travel_type == "ground":
            category = "ground"
            if distance_km is None or distance_km == 0:
                flags.append("MISSING_GROUND_DISTANCE")
            elif distance_km < 0:
                flags.append("NEGATIVE_DISTANCE")
            else:
                normalized_qty = distance_km * GROUND_FACTOR * class_multiplier

        trip_date = _parse_date(raw.get("trip_date", ""))
        origin = raw.get("origin", "")
        destination = raw.get("destination", "")

        suspicious = bool(flags and SUSPICIOUS_FLAGS & set(flags))

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
            "scope": 3,
            "category": category,
            "activity_date": trip_date,
            "location": f"{origin} → {destination}" if origin or destination else "",
            "description": (
                f"Employee {raw.get('employee_id', '')} | "
                f"{travel_type.title()} | "
                f"Class: {transport_class} | "
                f"Amount: {raw.get('amount_usd', '')} {raw.get('currency', 'USD')}"
            ),
            "status": status,
            "flags": flags,
            "row_num": row_num,
        }
