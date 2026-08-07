"""
Bus Service — Pydantic Response Models

Defines the strict, typed output contract for the bus search endpoint.
All fields are explicitly typed and documented for the OpenAPI schema.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# Sub-models
# ─────────────────────────────────────────────────────────────────────────────

class FareBySeatType(BaseModel):
    """Fare breakdown for a specific seat type (e.g. SEATER, SLEEPER)."""
    original_price:   Optional[float] = Field(None, description="Original price before discounts")
    discounted_price: Optional[float] = Field(None, description="Final discounted price")
    count:            Optional[int]   = Field(None, description="Number of seats at this price")


class BusOffer(BaseModel):
    """An operator-level discount or promotional offer."""
    discount_value: Optional[str]   = Field(None, description="Offer discount amount or percentage")
    discount_type:  Optional[int]   = Field(None, description="Type code: 1=flat, 2=percent")
    offer_type:     Optional[int]   = Field(None, description="Offer category code")
    validity_days:  Optional[int]   = Field(None, description="Days before departure for offer validity")


class BusMetadata(BaseModel):
    """Non-display fields useful for booking flows."""
    doj:                 Optional[str]                    = Field(None, description="Date of journey (YYYY-MM-DD)")
    cancellation_policy: Optional[str]                    = Field(None, description="Raw cancellation policy string")
    vendor_currency:     Optional[str]                    = Field(None, description="Currency code (e.g. INR)")
    max_seats_per_txn:   Optional[int]                    = Field(None, description="Max seats bookable per transaction")
    m_ticket_enabled:    bool                             = Field(False, description="Whether m-ticket is supported")
    is_non_ac:           bool                             = Field(False, description="True if bus is Non-AC")
    is_seater:           bool                             = Field(False, description="True if bus has seater seats")
    is_sleeper:          bool                             = Field(False, description="True if bus has sleeper seats")
    program_list:        List[int]                        = Field(default_factory=list)
    campaign_types:      List[int]                        = Field(default_factory=list)
    fare_by_seat_type:   Dict[str, FareBySeatType]        = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Primary bus model
# ─────────────────────────────────────────────────────────────────────────────

class Bus(BaseModel):
    """A single bus result with all display and booking fields."""

    # Operator
    operator_id:   Optional[int]  = Field(None, description="Unique RedBus operator ID")
    operator_name: Optional[str]  = Field(None, description="Operator / travels name")
    operator_logo: Optional[str]  = Field(None, description="Full URL to the operator logo image")

    # Service
    service_id:   Optional[str] = Field(None, description="Unique service/schedule identifier")
    service_name: Optional[str] = Field(None, description="Route display name (e.g. 'Alangulam - Coimbatore')")

    # Route
    route_id: Optional[int] = Field(None, description="Unique route identifier")

    # Bus type
    bus_type:    Optional[str] = Field(None, description="Full bus type description (e.g. 'Non A/C Seater / Sleeper (2+1)')")
    bus_type_id: Optional[int] = Field(None, description="Numeric bus type code")

    # Schedule
    departure_time:   Optional[str] = Field(None, description="Departure datetime (YYYY-MM-DD HH:MM:SS)")
    arrival_time:     Optional[str] = Field(None, description="Arrival datetime (YYYY-MM-DD HH:MM:SS)")
    duration_minutes: Optional[int] = Field(None, description="Journey duration in minutes")
    duration:         Optional[str] = Field(None, description="Human-readable duration (e.g. '6h 20m')")

    # Fares
    fare_list:   List[float]    = Field(default_factory=list, description="All available fare points (sorted)")
    minimum_fare: Optional[float] = Field(None, description="Lowest available fare")
    maximum_fare: Optional[float] = Field(None, description="Highest available fare")

    # Seats
    available_seats: Optional[int] = Field(None, description="Total seats currently available")
    window_seats:    Optional[int] = Field(None, description="Available window seats")
    single_seats:    Optional[int] = Field(None, description="Available single seats")
    upper_seats:     Optional[int] = Field(None, description="Available upper berths")
    lower_seats:     Optional[int] = Field(None, description="Available lower berths")

    # Boarding / Dropping
    boarding_point: Optional[str] = Field(None, description="Primary boarding point name")
    boarding_count: Optional[int] = Field(None, description="Total number of boarding points")
    dropping_point: Optional[str] = Field(None, description="Primary dropping point name")
    dropping_count: Optional[int] = Field(None, description="Total number of dropping points")

    # Amenities
    amenities: List[str] = Field(default_factory=list, description="List of amenity labels (e.g. 'WiFi', 'Charging Point')")

    # Offers
    offers: List[BusOffer] = Field(default_factory=list, description="Active operator offers/discounts")

    # Rating
    rating:       Optional[float] = Field(None, description="Operator rating (0–5)")
    review_count: Optional[int]   = Field(None, description="Number of user reviews")

    # Features
    live_tracking:          bool = Field(False, description="Whether live GPS tracking is available")
    seat_layout_available:  bool = Field(False, description="Whether interactive seat layout is available")
    partial_cancellation:   bool = Field(False, description="Whether partial ticket cancellation is allowed")

    # Booking metadata
    metadata: BusMetadata = Field(default_factory=BusMetadata)


# ─────────────────────────────────────────────────────────────────────────────
# Search response envelope
# ─────────────────────────────────────────────────────────────────────────────

class BusSearchData(BaseModel):
    source_id:      int = Field(..., description="RedBus city ID for origin")
    destination_id: int = Field(..., description="RedBus city ID for destination")
    journey_date:   str = Field(..., description="Date of journey as provided")
    total_buses:    int = Field(..., description="Total number of buses in this response page")
    limit:          int = Field(..., description="Page size limit applied")
    offset:         int = Field(..., description="Page offset applied")
    buses:          List[Bus] = Field(default_factory=list)


class BusSearchResponse(BaseModel):
    success: bool
    message: str
    data:    BusSearchData


# ─────────────────────────────────────────────────────────────────────────────
# Generic error response
# ─────────────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    success: bool
    message: str
