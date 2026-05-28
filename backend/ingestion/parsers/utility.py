"""
Utility (Electricity) CSV Parser
----------------------------------
Handles UK/US utility portal CSV exports.
Columns: account_number, billing_period_start, billing_period_end,
         meter_id, consumption_kwh, tariff_rate, total_amount_gbp,
         carbon_intensity_gco2_per_kwh

Scope 2 — market-based or location-based electricity.
Conversion: kgCO2e = consumption_kwh * (carbon_intensity_gco2_per_kwh / 1000)
Default carbon intensity: 233 gCO2/kWh (UK 2023 average)

SUSPICIOUS if:
  - billing_period > 45 days (likely meter read error or missed bill)
  - consumption_kwh <= 0
  - carbon_intensity_gco2_per_kwh is missing or zero (using default, flag for review)
"""

import csv
import hashlib
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Generator

logger = logging.getLogger("ingestion")

DEFAULT_CARBON_INTENSITY_GCO2_KWH = Decimal("233")  # gCO2/kWh → /1000 → kgCO2e/kWh
MAX_BILLING_DAYS = 45

SUSPICIOUS_FLAGS = {
    "ZERO_OR_NEGATIVE_CONSUMPTION",
    "END_BEFORE_START",
    "INVALID_CONSUMPTION",
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


def _row_hash(row: dict) -> str:
    canonical = "|".join(f"{k}={v}" for k, v in sorted(row.items()))
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


def parse_utility_csv(file_content: bytes) -> Generator[dict, None, None]:
    """
    Parse utility electricity CSV and yield normalised record dicts.
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

        # Parse consumption
        kwh_raw = (raw.get("consumption_kwh") or "").strip().replace(",", "")
        try:
            consumption_kwh = Decimal(kwh_raw)
        except (InvalidOperation, ValueError):
            consumption_kwh = None
            flags.append("INVALID_CONSUMPTION")

        if consumption_kwh is not None and consumption_kwh <= 0:
            flags.append("ZERO_OR_NEGATIVE_CONSUMPTION")

        # Parse carbon intensity
        ci_raw = (raw.get("carbon_intensity_gco2_per_kwh") or "").strip()
        try:
            carbon_intensity = Decimal(ci_raw) if ci_raw else None
        except (InvalidOperation, ValueError):
            carbon_intensity = None

        using_default_ci = False
        if not carbon_intensity or carbon_intensity <= 0:
            carbon_intensity = DEFAULT_CARBON_INTENSITY_GCO2_KWH
            using_default_ci = True
            flags.append("DEFAULT_CARBON_INTENSITY")

        # Compute kgCO2e
        if consumption_kwh is not None and consumption_kwh > 0:
            normalized_qty = consumption_kwh * (carbon_intensity / Decimal("1000"))
        else:
            normalized_qty = None

        # Parse billing period
        start_date = _parse_date(raw.get("billing_period_start", ""))
        end_date = _parse_date(raw.get("billing_period_end", ""))

        billing_days = None
        if start_date and end_date:
            billing_days = (end_date - start_date).days
            if billing_days < 0:
                flags.append("END_BEFORE_START")
            elif billing_days > MAX_BILLING_DAYS:
                # BUG FIX: was using a dynamic flag string like "LONG_BILLING_PERIOD_90_DAYS"
                # which was never matched by the old suspicious check. Now using a fixed
                # flag name + separate metadata field so the check is reliable.
                flags.append("LONG_BILLING_PERIOD")

        # FIX: previously the suspicious check had a Python precedence bug —
        # the `or any(f.startswith(...))` was part of the `for ... in` iterable,
        # not an `or` at the boolean level, so LONG_BILLING_PERIOD was never detected.
        suspicious = bool(
            flags
            and (
                SUSPICIOUS_FLAGS & set(flags)
                or "LONG_BILLING_PERIOD" in flags
            )
        )

        if is_duplicate:
            status = "DUPLICATE"
        elif suspicious:
            status = "SUSPICIOUS"
        else:
            status = "PENDING_REVIEW"

        account = raw.get("account_number", "")
        meter = raw.get("meter_id", "")

        yield {
            "raw_data": raw,
            "source_hash": h,
            "normalized_quantity": normalized_qty,
            "normalized_unit": "kgCO2e",
            "scope": 2,
            "category": "electricity",
            "activity_date": start_date,
            "location": f"Account {account} | Meter {meter}",
            "description": (
                f"Electricity bill: {raw.get('billing_period_start', '')} → "
                f"{raw.get('billing_period_end', '')} | "
                f"{consumption_kwh} kWh | "
                f"CI: {carbon_intensity} gCO2/kWh"
                + (" [DEFAULT CI]" if using_default_ci else "")
                + (f" | {billing_days}d billing period" if billing_days is not None else "")
            ),
            "status": status,
            "flags": flags,
            "row_num": row_num,
        }
