"""
Trip request schema — the traveler's intent.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BudgetLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TravelPace(str, Enum):
    relaxed = "relaxed"
    moderate = "moderate"
    intensive = "intensive"


class TransportPreference(str, Enum):
    flight = "flight"
    train = "train"
    bus = "bus"
    any = "any"


class HotelPreference(str, Enum):
    budget = "budget"
    mid_range = "mid_range"
    luxury = "luxury"
    any = "any"


class TripRequest(BaseModel):
    """
    Top-level input describing what the traveler wants.
    Consumed by the Trip Planner to orchestrate all downstream services.
    """

    origin: str = Field(..., description="Departure city or location.")
    destination: str = Field(..., description="Destination city or location.")
    start_date: date = Field(..., description="Trip start date (YYYY-MM-DD).")
    end_date: date = Field(..., description="Trip end date (YYYY-MM-DD).")
    travelers: int = Field(
        default=1, ge=1, le=20,
        description="Number of travelers."
    )
    budget: BudgetLevel = Field(
        default=BudgetLevel.medium,
        description="Budget level: low | medium | high."
    )
    transport_preference: TransportPreference = Field(
        default=TransportPreference.any,
        description="Preferred mode of transport."
    )
    hotel_preference: HotelPreference = Field(
        default=HotelPreference.any,
        description="Preferred hotel category."
    )
    pace: TravelPace = Field(
        default=TravelPace.moderate,
        description="Travel pace: relaxed | moderate | intensive."
    )

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v
