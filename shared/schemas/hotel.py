"""
Hotel schema — mirrors hotel-service/app/models.py exactly.

Source service : hotel-service
Provider       : SerpApi Google Hotels engine

Field mapping from SerpApi → this schema:
    property_token / md5(name)   → id
    name                         → name
    description                  → description
    gps_coordinates.latitude     → latitude
    gps_coordinates.longitude    → longitude
    overall_rating               → rating
    reviews                      → review_count
    extracted_hotel_class        → hotel_class
    rate_per_night.extracted_lowest → price.per_night
    total_rate.extracted_lowest  → price.total
    check_in_time                → check_in_time
    check_out_time               → check_out_time
    amenities[*]                 → amenities  (flat list of strings)
    images[0].original_image     → image_url
    link                         → website_url
    nearby_places[*].name        → nearby_places  (flat list of strings)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HotelPrice(BaseModel):
    """Pricing block — sourced from SerpApi rate_per_night / total_rate."""

    per_night: Optional[float] = Field(
        default=None,
        description="rate_per_night.extracted_lowest from SerpApi."
    )
    total: Optional[float] = Field(
        default=None,
        description="total_rate.extracted_lowest from SerpApi."
    )
    currency: str = Field(default="INR")


class Hotel(BaseModel):
    """A single hotel listing as returned by the Hotel Service."""

    id: str = Field(..., description="property_token when available, else md5(name)[:16].")
    name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = Field(
        default=None,
        description="overall_rating from SerpApi."
    )
    review_count: Optional[int] = Field(
        default=None,
        description="reviews count from SerpApi."
    )
    hotel_class: Optional[int] = Field(
        default=None,
        description="extracted_hotel_class (star rating)."
    )
    price: HotelPrice = Field(default_factory=HotelPrice)
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    amenities: list[str] = Field(default_factory=list)
    image_url: Optional[str] = Field(
        default=None,
        description="images[0].original_image from SerpApi."
    )
    website_url: Optional[str] = Field(
        default=None,
        description="link field from SerpApi."
    )
    nearby_places: list[str] = Field(
        default_factory=list,
        description="Flat list of nearby place names."
    )
