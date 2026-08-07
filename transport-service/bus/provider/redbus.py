"""
redbus.py
---------
The RedBus provider facade — the only file that service-layer code imports.

Responsibility:
  - Orchestrate client.fetch_inventory() → parser.parse_response()
  - Be the single public interface for this provider
  - Re-export provider exceptions so callers only need to import from here

Usage:
    from provider.redbus import RedbusProvider, RedbusProviderError

    provider = RedbusProvider()
    result   = provider.search(from_city=122455, to_city=122474, doj="21-Aug-2026")
"""

import logging
from typing import Any, Dict

from provider.client import fetch_inventory
from provider.parser import parse_response
from provider.exceptions import (          # re-export for callers
    RedbusProviderError,
    RedbusConnectionError,
    RedbusTimeoutError,
    RedbusSessionExpiredError,
    RedbusEmptyResponseError,
    RedbusParseError,
)

logger = logging.getLogger(__name__)

__all__ = [
    "RedbusProvider",
    "RedbusProviderError",
    "RedbusConnectionError",
    "RedbusTimeoutError",
    "RedbusSessionExpiredError",
    "RedbusEmptyResponseError",
    "RedbusParseError",
]


class RedbusProvider:
    """
    RedBus bus search provider.

    Stateless and thread-safe — the persistent session lives at module level
    inside client.py, not inside this class.

    Example:
        provider = RedbusProvider()
        result = provider.search(
            from_city=122455,
            to_city=122474,
            doj="21-Aug-2026",
        )
        print(result["total_buses"])
        for bus in result["buses"]:
            print(bus["operator_name"], bus["minimum_fare"])
    """

    def search(
        self,
        from_city: int,
        to_city: int,
        doj: str,
    ) -> Dict[str, Any]:
        """
        Search for buses between two RedBus city IDs on a given date.

        Args:
            from_city: RedBus numeric city ID for the origin.
                       Find it from the browser URL after searching:
                       redbus.in/bus-tickets/...?fromCityId=<ID>
            to_city:   RedBus numeric city ID for the destination.
            doj:       Date of journey in DD-Mon-YYYY format.
                       Examples: '21-Aug-2026', '05-Jan-2027'

        Returns:
            {
                "total_buses":   int,
                "logo_base_url": str,
                "buses": [
                    {
                        "operator_id":          int,
                        "operator_name":        str,
                        "operator_logo":        str,
                        "service_id":           str,
                        "service_name":         str,
                        "route_id":             int,
                        "bus_type":             str,
                        "bus_type_id":          int,
                        "departure_time":       str,
                        "arrival_time":         str,
                        "duration_minutes":     int,
                        "fare_list":            List[float],
                        "minimum_fare":         float,
                        "maximum_fare":         float,
                        "available_seats":      int,
                        "window_seats":         int,
                        "single_seats":         int,
                        "upper_seats":          int,
                        "lower_seats":          int,
                        "boarding_point":       str,
                        "boarding_count":       int,
                        "dropping_point":       str,
                        "dropping_count":       int,
                        "amenities":            List[int],
                        "offers":               List[dict],
                        "rating":               float,
                        "review_count":         int,
                        "live_tracking":        bool,
                        "seat_layout_available": bool,
                        "partial_cancellation": bool,
                        "metadata":             dict,
                    },
                    ...
                ]
            }

        Raises:
            RedbusTimeoutError:        Request exceeded timeout.
            RedbusConnectionError:     Network failure.
            RedbusSessionExpiredError: Session blocked even after refresh.
            RedbusEmptyResponseError:  No inventory in response.
            RedbusParseError:          Response JSON has unexpected structure.
        """
        logger.info(
            f"RedbusProvider.search: from_city={from_city} "
            f"to_city={to_city} doj={doj}"
        )

        raw    = fetch_inventory(from_city, to_city, doj)
        result = parse_response(raw)

        logger.info(
            f"RedbusProvider.search: complete — {result['total_buses']} buses"
        )
        return result
