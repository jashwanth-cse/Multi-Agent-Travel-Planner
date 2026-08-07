"""
Bus Service — BusService

Sits between the router and the RedBus provider.

Responsibilities:
  - Call the RedBusProvider with the correct arguments.
  - Normalise duration (minutes → human-readable string).
  - Normalise amenity IDs → human-readable labels.
  - Map provider exceptions → service exceptions.
  - Return clean, fully typed BusSearchData.
  - Never expose raw provider dicts to the router.
"""

import logging
from typing import Any, Dict, List, Optional

from app.exceptions import (
    BusSearchError,
    BusProviderUnavailableError,
    BusNoResultsError,
)
from app.models.response_models import (
    Bus,
    BusMetadata,
    BusOffer,
    BusSearchData,
    FareBySeatType,
)

# Provider import — the only bridge to the network/parsing layer
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from provider.redbus import RedbusProvider
from provider.exceptions import (
    RedbusProviderError,
    RedbusConnectionError,
    RedbusTimeoutError,
    RedbusSessionExpiredError,
    RedbusEmptyResponseError,
    RedbusParseError,
)

logger = logging.getLogger(__name__)

# ── Amenity ID → Label mapping ────────────────────────────────────────────────
# Source: RedBus platform amenity codes (captured from live responses).
_AMENITY_LABELS: Dict[int, str] = {
    1:  "Live Tracking",
    2:  "M-Ticket",
    3:  "Blankets",
    4:  "Water Bottle",
    5:  "Snacks",
    6:  "Reading Light",
    7:  "Charging Point",
    8:  "Air Purifier",
    9:  "WiFi",
    10: "Movie",
    11: "Emergency Contact",
    12: "CCTV",
    13: "Fire Extinguisher",
    14: "GPS",
    15: "First Aid",
    16: "Toilet",
    17: "Hand Sanitiser",
    18: "Fever/Cold Supplies",
    19: "Mobile Charging",
    20: "Personal TV",
    21: "Newspaper",
    22: "Pillows",
    23: "Blanket & Pillow",
    24: "Hot Meals",
    25: "Cold Meals",
}


# ── Module-level singleton provider ───────────────────────────────────────────
_provider = RedbusProvider()


class BusService:
    """
    Stateless service class for bus searches.
    Instantiated once at import time by the router.
    """

    def search(
        self,
        source_id: int,
        destination_id: int,
        journey_date: str,
        limit: int = 10,
        offset: int = 0,
    ) -> BusSearchData:
        """
        Search for buses between two RedBus city IDs.

        Args:
            source_id:      RedBus numeric city ID for origin.
            destination_id: RedBus numeric city ID for destination.
            journey_date:   Date of journey in DD-Mon-YYYY format (e.g. '21-Aug-2026').
            limit:          Maximum number of results to return.
            offset:         Number of results to skip (for pagination).

        Returns:
            BusSearchData — fully normalised and typed.

        Raises:
            BusProviderUnavailableError: Provider timeout, connection, or session issue.
            BusSearchError:             Parsing or unexpected provider failure.
            BusNoResultsError:          Valid search but zero buses on this route/date.
        """
        logger.info(
            f"BusService.search: source_id={source_id} "
            f"destination_id={destination_id} date={journey_date} "
            f"limit={limit} offset={offset}"
        )

        # ── Call provider ──────────────────────────────────────────────────────
        try:
            raw = _provider.search(
                from_city=source_id,
                to_city=destination_id,
                doj=journey_date,
            )
        except (RedbusTimeoutError, RedbusConnectionError, RedbusSessionExpiredError) as exc:
            logger.warning(f"Provider unavailable: {exc}")
            raise BusProviderUnavailableError(str(exc)) from exc
        except (RedbusEmptyResponseError, RedbusParseError) as exc:
            logger.warning(f"Provider data issue: {exc}")
            raise BusSearchError(str(exc)) from exc
        except RedbusProviderError as exc:
            logger.error(f"Unexpected provider error: {exc}")
            raise BusSearchError(str(exc)) from exc

        # ── Normalise ─────────────────────────────────────────────────────────
        all_buses = raw.get("buses", [])

        if not all_buses:
            raise BusNoResultsError(
                f"No buses found from city {source_id} to city {destination_id} on {journey_date}."
            )

        # Apply offset + limit (provider returns up to `limit` already, but we
        # honour both params for explicit pagination control at service layer)
        paginated = all_buses[offset: offset + limit]

        normalised_buses = [self._normalise_bus(b) for b in paginated]

        return BusSearchData(
            source_id=source_id,
            destination_id=destination_id,
            journey_date=journey_date,
            total_buses=len(all_buses),
            limit=limit,
            offset=offset,
            buses=normalised_buses,
        )

    # ── Private normalisation helpers ─────────────────────────────────────────

    def _normalise_bus(self, raw: Dict[str, Any]) -> Bus:
        """Convert a raw provider bus dict into a typed Bus model."""
        return Bus(
            # Operator
            operator_id=raw.get("operator_id"),
            operator_name=raw.get("operator_name"),
            operator_logo=raw.get("operator_logo"),

            # Service
            service_id=raw.get("service_id"),
            service_name=raw.get("service_name"),

            # Route
            route_id=raw.get("route_id"),

            # Bus type
            bus_type=raw.get("bus_type"),
            bus_type_id=raw.get("bus_type_id"),

            # Schedule
            departure_time=raw.get("departure_time"),
            arrival_time=raw.get("arrival_time"),
            duration_minutes=raw.get("duration_minutes"),
            duration=self._format_duration(raw.get("duration_minutes")),

            # Fares
            fare_list=raw.get("fare_list", []),
            minimum_fare=raw.get("minimum_fare"),
            maximum_fare=raw.get("maximum_fare"),

            # Seats
            available_seats=raw.get("available_seats"),
            window_seats=raw.get("window_seats"),
            single_seats=raw.get("single_seats"),
            upper_seats=raw.get("upper_seats"),
            lower_seats=raw.get("lower_seats"),

            # Boarding / Dropping
            boarding_point=raw.get("boarding_point"),
            boarding_count=raw.get("boarding_count"),
            dropping_point=raw.get("dropping_point"),
            dropping_count=raw.get("dropping_count"),

            # Amenities — convert IDs to labels
            amenities=self._resolve_amenities(raw.get("amenities", [])),

            # Offers
            offers=self._normalise_offers(raw.get("offers", [])),

            # Rating
            rating=raw.get("rating"),
            review_count=raw.get("review_count"),

            # Features
            live_tracking=bool(raw.get("live_tracking")),
            seat_layout_available=bool(raw.get("seat_layout_available")),
            partial_cancellation=bool(raw.get("partial_cancellation")),

            # Metadata
            metadata=self._normalise_metadata(raw.get("metadata", {})),
        )

    @staticmethod
    def _format_duration(minutes: Optional[int]) -> Optional[str]:
        """Convert integer minutes to a human-readable string like '6h 20m'."""
        if minutes is None:
            return None
        hours = minutes // 60
        mins  = minutes % 60
        if hours and mins:
            return f"{hours}h {mins}m"
        if hours:
            return f"{hours}h"
        return f"{mins}m"

    @staticmethod
    def _resolve_amenities(ids: List[Any]) -> List[str]:
        """
        Convert a list of numeric amenity IDs to human-readable label strings.
        Unknown IDs are preserved as 'Amenity #<id>' so no data is silently lost.
        """
        resolved = []
        for item in ids:
            try:
                amenity_id = int(item)
                label = _AMENITY_LABELS.get(amenity_id, f"Amenity #{amenity_id}")
                resolved.append(label)
            except (TypeError, ValueError):
                resolved.append(str(item))
        return resolved

    @staticmethod
    def _normalise_offers(raw_offers: List[Dict[str, Any]]) -> List[BusOffer]:
        """Convert raw offer dicts into typed BusOffer models."""
        return [
            BusOffer(
                discount_value=o.get("discount_value"),
                discount_type=o.get("discount_type"),
                offer_type=o.get("offer_type"),
                validity_days=o.get("validity_days"),
            )
            for o in raw_offers
            if isinstance(o, dict)
        ]

    @staticmethod
    def _normalise_metadata(raw_meta: Dict[str, Any]) -> BusMetadata:
        """Convert raw metadata dict into a typed BusMetadata model."""
        fare_by_type: Dict[str, FareBySeatType] = {}
        for seat_type, details in (raw_meta.get("fare_by_seat_type") or {}).items():
            if isinstance(details, dict):
                fare_by_type[seat_type] = FareBySeatType(
                    original_price=details.get("original_price"),
                    discounted_price=details.get("discounted_price"),
                    count=details.get("count"),
                )

        return BusMetadata(
            doj=raw_meta.get("doj"),
            cancellation_policy=raw_meta.get("cancellation_policy"),
            vendor_currency=raw_meta.get("vendor_currency"),
            max_seats_per_txn=raw_meta.get("max_seats_per_txn"),
            m_ticket_enabled=bool(raw_meta.get("m_ticket_enabled")),
            is_non_ac=bool(raw_meta.get("is_non_ac")),
            is_seater=bool(raw_meta.get("is_seater")),
            is_sleeper=bool(raw_meta.get("is_sleeper")),
            program_list=list(raw_meta.get("program_list") or []),
            campaign_types=list(raw_meta.get("campaign_types") or []),
            fare_by_seat_type=fare_by_type,
        )
