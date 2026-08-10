"""
Bus Service — BusService

Sits between the router and the RedBus provider.

Responsibilities:
  - Resolve city names → city IDs via RedBusCityResolver.
  - Call the RedBusProvider with the resolved city IDs.
  - Normalise duration (minutes → human-readable string).
  - Normalise amenity IDs → human-readable labels.
  - Map provider/resolver exceptions → service exceptions.
  - Return clean, fully typed BusSearchData.
  - Never expose raw provider dicts to the router.

Flow:
    BusService.search(source, destination, journey_date)
        ↓
    RedBusCityResolver.resolve(source, destination)
        ↓  (source_id, destination_id)
    RedBusProvider.search(from_city, to_city, doj)
        ↓  (raw bus dicts)
    _normalise_bus(...)
        ↓
    BusSearchData
"""

import logging
import sys
import os
from typing import Any, Dict, List, Optional

# Make resolver and provider importable from the bus/ root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.exceptions import (
    BusSearchError,
    BusProviderUnavailableError,
    BusNoResultsError,
    CityNotFoundError,
    InvalidCityRouteError,
)
from app.models.response_models import (
    Bus,
    BusMetadata,
    BusOffer,
    BusSearchData,
    FareBySeatType,
)

# ── Resolver ──────────────────────────────────────────────────────────────────
from resolver.redbus_city import RedbusCityResolver
from resolver.exceptions import (
    ResolverError,
    CityResolutionError,
    InvalidRouteError,
    ResolverUnavailableError,
    ResolverTimeoutError,
)

# ── Provider ──────────────────────────────────────────────────────────────────
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

# ── Module-level singletons ───────────────────────────────────────────────────
_resolver = RedbusCityResolver()
_provider = RedbusProvider()


class BusService:
    """
    Stateless service class for bus searches.
    Instantiated once at import time by the router.
    """

    def search(
        self,
        source: str,
        destination: str,
        journey_date: str,
        limit: int = 10,
        offset: int = 0,
    ) -> BusSearchData:
        """
        Search for buses between two city names.

        Args:
            source:       Origin city name (e.g. 'Rajapalayam', 'Chennai').
            destination:  Destination city name (e.g. 'Chennai', 'Bangalore').
            journey_date: Date of journey in DD-Mon-YYYY format (e.g. '21-Aug-2026').
            limit:        Maximum number of results to return (applied after provider).
            offset:       Number of results to skip (for pagination).

        Returns:
            BusSearchData — fully normalised and typed.

        Raises:
            CityNotFoundError:          City name could not be resolved to a RedBus ID.
            InvalidCityRouteError:      No RedBus route page for this city combination.
            BusProviderUnavailableError: Provider timeout, connection, or session issue.
            BusSearchError:             Parsing or unexpected provider failure.
            BusNoResultsError:          Valid search but zero buses on this route/date.
        """
        logger.info(
            f"BusService.search: '{source}' → '{destination}'  "
            f"date={journey_date}  limit={limit}  offset={offset}"
        )

        # ── Step 1: Resolve city names → IDs ──────────────────────────────────
        resolved = self._resolve_cities(source, destination)

        source_id      = resolved["source_id"]
        destination_id = resolved["destination_id"]
        source_name    = resolved["source_name"]
        dest_name      = resolved["destination_name"]

        logger.info(
            f"BusService.search: resolved  "
            f"{source_name}={source_id}  {dest_name}={destination_id}"
        )

        # ── Step 2: Fetch buses from provider ─────────────────────────────────
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

        # ── Step 3: Normalise ─────────────────────────────────────────────────
        all_buses = raw.get("buses", [])

        if not all_buses:
            raise BusNoResultsError(
                f"No buses found from '{source_name}' to '{dest_name}' on {journey_date}."
            )

        paginated        = all_buses[offset: offset + limit]
        normalised_buses = [self._normalise_bus(b) for b in paginated]

        return BusSearchData(
            source=source_name,
            destination=dest_name,
            journey_date=journey_date,
            total_buses=len(all_buses),
            limit=limit,
            offset=offset,
            buses=normalised_buses,
        )

    # ── City resolution ───────────────────────────────────────────────────────

    @staticmethod
    def _resolve_cities(source: str, destination: str) -> Dict[str, Any]:
        """Delegate city name resolution to RedbusCityResolver, mapping exceptions."""
        try:
            return _resolver.resolve(source, destination)
        except (CityResolutionError,) as exc:
            raise CityNotFoundError(str(exc)) from exc
        except (InvalidRouteError,) as exc:
            raise InvalidCityRouteError(str(exc)) from exc
        except (ResolverTimeoutError, ResolverUnavailableError) as exc:
            raise BusProviderUnavailableError(str(exc)) from exc
        except ResolverError as exc:
            raise BusSearchError(str(exc)) from exc

    # ── Bus normalisation ─────────────────────────────────────────────────────

    def _normalise_bus(self, raw: Dict[str, Any]) -> Bus:
        """Convert a raw provider bus dict into a typed Bus model."""
        return Bus(
            operator_id=raw.get("operator_id"),
            operator_name=raw.get("operator_name"),
            operator_logo=raw.get("operator_logo"),
            service_id=raw.get("service_id"),
            service_name=raw.get("service_name"),
            route_id=raw.get("route_id"),
            bus_type=raw.get("bus_type"),
            bus_type_id=raw.get("bus_type_id"),
            departure_time=raw.get("departure_time"),
            arrival_time=raw.get("arrival_time"),
            duration_minutes=raw.get("duration_minutes"),
            duration=self._format_duration(raw.get("duration_minutes")),
            fare_list=raw.get("fare_list", []),
            minimum_fare=raw.get("minimum_fare"),
            maximum_fare=raw.get("maximum_fare"),
            available_seats=raw.get("available_seats"),
            window_seats=raw.get("window_seats"),
            single_seats=raw.get("single_seats"),
            upper_seats=raw.get("upper_seats"),
            lower_seats=raw.get("lower_seats"),
            boarding_point=raw.get("boarding_point"),
            boarding_count=raw.get("boarding_count"),
            dropping_point=raw.get("dropping_point"),
            dropping_count=raw.get("dropping_count"),
            amenities=self._resolve_amenities(raw.get("amenities", [])),
            offers=self._normalise_offers(raw.get("offers", [])),
            rating=raw.get("rating"),
            review_count=raw.get("review_count"),
            live_tracking=bool(raw.get("live_tracking")),
            seat_layout_available=bool(raw.get("seat_layout_available")),
            partial_cancellation=bool(raw.get("partial_cancellation")),
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
        """Convert numeric amenity IDs to human-readable labels."""
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
