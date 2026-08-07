"""
parser.py
---------
Extracts only useful provider data from the raw RedBus JSON response.

Rules:
  - DO NOT expose raw RedBus keys in the output.
  - DO NOT normalize or transform values beyond safe type coercions.
  - Every field uses a typed, intentional extraction.
  - Raises RedbusParseError on unrecoverable structural issues.

Raw JSON shape:
  {
    "success": true,
    "data": {
      "metaData": { "totalCount": N, "busLogoBaseUrl": "...", ... },
      "inventories": [ { ...per-bus fields... }, ... ]
    }
  }
"""

import logging
from typing import Any, Dict, List, Optional

from provider.constants import LOGO_BASE_URL
from provider.exceptions import RedbusParseError

logger = logging.getLogger(__name__)


# ── Public entry point ────────────────────────────────────────────────────────

def parse_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the full RedBus response into a clean provider dictionary.

    Args:
        raw: The decoded JSON dict returned by the RedBus API.

    Returns:
        {
            "total_buses":   int,
            "logo_base_url": str,
            "buses":         List[Dict],
        }

    Raises:
        RedbusParseError: If the top-level structure is missing.
    """
    try:
        data        = raw["data"]
        meta        = data.get("metaData", {})
        inventories = data.get("inventories", [])
    except (KeyError, TypeError) as exc:
        raise RedbusParseError(
            f"Unexpected RedBus response structure: {exc}"
        ) from exc

    # Prefer the logo base URL that comes from the response itself.
    logo_base = str(meta.get("busLogoBaseUrl") or LOGO_BASE_URL).rstrip("/") + "/"

    buses = []
    for idx, item in enumerate(inventories):
        if not isinstance(item, dict):
            logger.warning(f"Skipping non-dict inventory item at index {idx}")
            continue
        buses.append(_parse_inventory(item, logo_base))

    return {
        "total_buses":   len(buses),
        "logo_base_url": logo_base,
        "buses":         buses,
    }


# ── Per-inventory extractor ───────────────────────────────────────────────────

def _parse_inventory(item: Dict[str, Any], logo_base: str) -> Dict[str, Any]:
    """Extract all specified fields from a single inventory object."""

    # ── Operator ──────────────────────────────────────────────────────────────
    logo_path    = _s(item.get("operatorLogoPath"))
    operator_logo = (logo_base + logo_path) if logo_path else None

    # ── Fares ─────────────────────────────────────────────────────────────────
    fare_list    = _parse_fare_list(item)
    min_fare     = min(fare_list) if fare_list else None
    max_fare     = max(fare_list) if fare_list else None

    # ── Seat breakdown by type ────────────────────────────────────────────────
    fare_by_type = _parse_fare_by_seat_type(item)

    # ── Boarding / Dropping ───────────────────────────────────────────────────
    location     = item.get("locationSearchParams") or {}

    # ── Offers ────────────────────────────────────────────────────────────────
    offers       = _parse_offers(item)

    # ── Metadata (fields useful for booking but not primary display) ──────────
    metadata = {
        "doj":                  _s(item.get("doj")),
        "cancellation_policy":  _s(item.get("cancellationPolicy")),
        "vendor_currency":      _s(item.get("vendorCurrency")),
        "max_seats_per_txn":    _i(item.get("maxSeatsPerTransaction")),
        "m_ticket_enabled":     bool(item.get("isMticketEnabled")),
        "is_non_ac":            bool(item.get("isNonAc")),
        "is_seater":            bool(item.get("isSeater")),
        "is_sleeper":           bool(item.get("isSleeper")),
        "program_list":         list(item.get("programList") or []),
        "campaign_types":       list(item.get("campaignType") or []),
        "fare_by_seat_type":    fare_by_type,
    }

    return {
        # ── Operator ──────────────────────────────────────────────────────────
        "operator_id":    _i(item.get("operatorId")),
        "operator_name":  _s(item.get("travelsName")),
        "operator_logo":  operator_logo,

        # ── Service ───────────────────────────────────────────────────────────
        "service_id":     _s(item.get("serviceId")),
        "service_name":   _s(item.get("serviceName")),

        # ── Route ─────────────────────────────────────────────────────────────
        "route_id":       _i(item.get("routeId")),

        # ── Bus ───────────────────────────────────────────────────────────────
        "bus_type":       _s(item.get("busType")),
        "bus_type_id":    _i(item.get("busTypeId")),

        # ── Schedule ──────────────────────────────────────────────────────────
        "departure_time":    _s(item.get("departureTime")),
        "arrival_time":      _s(item.get("arrivalTime")),
        "duration_minutes":  _i(item.get("journeyDurationMin")),

        # ── Fares ─────────────────────────────────────────────────────────────
        "fare_list":     fare_list,
        "minimum_fare":  min_fare,
        "maximum_fare":  max_fare,

        # ── Seats ─────────────────────────────────────────────────────────────
        "available_seats":  _i(item.get("availableSeats")),
        "window_seats":     _i(item.get("availableWindowSeats")),
        "single_seats":     _i(item.get("availableSingleSeats")),
        "upper_seats":      _i(item.get("availableUpperSeats")),
        "lower_seats":      _i(item.get("availableLowerSeats")),

        # ── Boarding ──────────────────────────────────────────────────────────
        "boarding_point":   _s(item.get("standardBpName") or location.get("sourceBp")),
        "boarding_count":   _i(item.get("bpCount")),

        # ── Dropping ──────────────────────────────────────────────────────────
        "dropping_point":   _s(item.get("standardDpName") or location.get("destinationDp")),
        "dropping_count":   _i(item.get("dpCount")),

        # ── Amenities ─────────────────────────────────────────────────────────
        # Raw amenity IDs — Phase 3 will map these to human-readable labels.
        "amenities":        list(item.get("amenities") or []),

        # ── Offers ────────────────────────────────────────────────────────────
        "offers":           offers,

        # ── Rating ────────────────────────────────────────────────────────────
        "rating":           _f(item.get("totalRatings")),
        "review_count":     _i_from_str(item.get("numberOfReviews")),

        # ── Features ──────────────────────────────────────────────────────────
        "live_tracking":          bool(item.get("isLiveTrackingAvailable")),
        "seat_layout_available":  bool(item.get("isSeatLayoutAvailable")),
        "partial_cancellation":   bool(item.get("isPartialCancellationAllowed")),

        # ── Metadata ──────────────────────────────────────────────────────────
        "metadata": metadata,
    }


# ── Sub-parsers ───────────────────────────────────────────────────────────────

def _parse_fare_list(item: Dict[str, Any]) -> List[float]:
    """Return a sorted list of fares from fareList, skipping non-numeric values."""
    raw = item.get("fareList") or []
    fares = []
    for v in raw:
        f = _f(v)
        if f is not None:
            fares.append(f)
    return sorted(fares)


def _parse_fare_by_seat_type(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract fareDetailsBySeatType into a clean dict keyed by seat type name.

    Raw shape:  { "SEATER": [{"originalPrice": 1000, "count": 20}], ... }
    Output:     { "SEATER": {"original_price": 1000, "count": 20}, ... }
    """
    raw = item.get("fareDetailsBySeatType") or {}
    result: Dict[str, Any] = {}
    for seat_type, entries in raw.items():
        if isinstance(entries, list) and entries:
            first = entries[0]
            result[seat_type] = {
                "original_price":   _f(first.get("originalPrice")),
                "discounted_price":  _f(first.get("discountedPrice")),
                "count":             _i(first.get("count")),
            }
    return result


def _parse_offers(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract the operator offer campaign into a clean list of offer dicts.

    Raw shape:
      "operatorOfferCampaign": {
          "Vld": true,
          "CmpgList": [
              { "RTOOffer": "10", "RTODiscountType": 1, "oType": 1, "RTODays": 15, ... }
          ]
      }
    """
    campaign = item.get("operatorOfferCampaign") or {}
    if not campaign.get("Vld") and not campaign.get("RTVld"):
        return []

    raw_list = campaign.get("CmpgList") or []
    offers   = []
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        offers.append({
            "discount_value":  _s(entry.get("RTOOffer")),
            "discount_type":   _i(entry.get("RTODiscountType")),
            "offer_type":      _i(entry.get("oType")),
            "validity_days":   _i(entry.get("RTODays")),
        })
    return offers


# ── Type-safe coercions ───────────────────────────────────────────────────────

def _s(val: Any) -> Optional[str]:
    """Return a stripped string or None."""
    return str(val).strip() if val is not None else None


def _i(val: Any) -> Optional[int]:
    """Return an int or None."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _f(val: Any) -> Optional[float]:
    """Return a float or None."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _i_from_str(val: Any) -> Optional[int]:
    """Parse review count which arrives as a string e.g. '133'."""
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        return None
