"""
shared/schemas — public re-exports.

Any service or planner can import from this single entry point:

    from shared.schemas import (
        TripRequest, BudgetLevel, TravelPace,
        TransportPreference, HotelPreference,
        Attraction,
        Hotel, HotelPrice,
        Bus, BusOffer, Train, TravelClass, StationSimple, RouteOption,
        TripContext,
    )
"""

from shared.schemas.trip import (
    TripRequest,
    BudgetLevel,
    TravelPace,
    TransportPreference,
    HotelPreference,
)

from shared.schemas.attraction import Attraction

from shared.schemas.hotel import Hotel, HotelPrice

from shared.schemas.transport import (
    Bus,
    BusOffer,
    Train,
    TravelClass,
    StationSimple,
    RouteOption,
)

from shared.schemas.context import TripContext

__all__ = [
    # Trip
    "TripRequest",
    "BudgetLevel",
    "TravelPace",
    "TransportPreference",
    "HotelPreference",
    # Attraction
    "Attraction",
    # Hotel
    "Hotel",
    "HotelPrice",
    # Transport
    "Bus",
    "BusOffer",
    "Train",
    "TravelClass",
    "StationSimple",
    "RouteOption",
    # Context
    "TripContext",
]
