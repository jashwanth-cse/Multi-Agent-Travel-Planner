"""
Attraction schema — mirrors tourism-service/models.py exactly.

Source service : tourism-service
Provider       : Google Places API (New)

Field mapping from Google Places API → this schema:
    displayName.text   → name
    formattedAddress   → address
    location.latitude  → latitude
    location.longitude → longitude
    rating             → rating
    userRatingCount    → review_count
    googleMapsUri      → google_maps_url
    photos[0] photoUri → image_url
    types              → types
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Attraction(BaseModel):
    """A single tourist attraction as returned by the Tourism Service."""

    name: str
    address: str
    rating: Optional[float] = None
    review_count: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_url: Optional[str] = Field(
        default=None,
        description="googleMapsUri from the Google Places API."
    )
    image_url: Optional[str] = Field(
        default=None,
        description="Direct photo URL (lh3.googleusercontent.com) — usable as <img src>."
    )
    types: list[str] = Field(
        default_factory=list,
        description="Google Places type tags, e.g. tourist_attraction, museum, park."
    )
