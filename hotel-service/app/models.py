"""
Pydantic models for hotel request parameters and the normalized response.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class GuestsModel(BaseModel):
    adults: int
    children: int


class PriceModel(BaseModel):
    per_night: Optional[float] = None
    total: Optional[float] = None
    currency: str = "INR"


class HotelModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    hotel_class: Optional[int] = None
    price: PriceModel
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    amenities: list[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    website_url: Optional[str] = None
    nearby_places: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level response envelope
# ---------------------------------------------------------------------------

class HotelsResponse(BaseModel):
    city: str
    check_in: str
    check_out: str
    guests: GuestsModel
    count: int
    hotels: list[HotelModel]
