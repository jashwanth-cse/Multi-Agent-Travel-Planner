"""
SerpApi Google Hotels integration.

Mirrors the logic in ../../hotel.py (the reference implementation) but:
  - Uses async httpx instead of requests
  - Normalizes the raw SerpApi response into our clean schema
  - Never exposes the API key or raw SerpApi internals

Reference fields used (from hotel.py):
    hotel["name"]
    hotel["overall_rating"]
    hotel["reviews"]
    hotel["extracted_hotel_class"]
    hotel["gps_coordinates"]["latitude"] / ["longitude"]
    hotel["rate_per_night"]["extracted_lowest"]
    hotel["images"][0]["original_image"]
    hotel["link"]
    hotel["property_token"]          ← used as stable id
    hotel["description"]
    hotel["check_in_time"] / ["check_out_time"]
    hotel["amenities"]
    hotel["nearby_places"][*]["name"]
"""

import hashlib
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"
REQUEST_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_hotel_id(hotel: dict) -> str:
    """
    Return a stable identifier for a hotel property.
    Prefer SerpApi's property_token; fall back to an MD5 of the hotel name.
    """
    token = hotel.get("property_token")
    if token:
        return str(token)
    # Deterministic fallback
    raw = hotel.get("name", "unknown")
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _extract_amenities(hotel: dict) -> list[str]:
    """
    SerpApi returns amenities as a list of dicts with a "name" key, or
    sometimes as plain strings. Normalize to a flat list of strings.
    """
    raw = hotel.get("amenities", [])
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            name = item.get("name") or item.get("amenity")
            if name:
                result.append(str(name))
    return result


def _extract_nearby_places(hotel: dict) -> list[str]:
    """Return nearby place names as a flat list."""
    raw = hotel.get("nearby_places", [])
    names: list[str] = []
    for place in raw:
        if isinstance(place, dict):
            name = place.get("name")
            if name:
                names.append(str(name))
        elif isinstance(place, str):
            names.append(place)
    return names


def _normalize_hotel(hotel: dict) -> dict:
    """
    Convert one raw SerpApi hotel property dict into our clean schema.
    Missing fields → None or [] — never raises, never invents values.
    """
    coordinates = hotel.get("gps_coordinates") or {}
    rate = hotel.get("rate_per_night") or {}

    # Price
    per_night: Optional[float] = rate.get("extracted_lowest")  # numeric
    # SerpApi sometimes exposes a total_rate block
    total_rate = hotel.get("total_rate") or {}
    total: Optional[float] = total_rate.get("extracted_lowest")

    # Image
    images = hotel.get("images") or []
    image_url: Optional[str] = images[0].get("original_image") if images else None

    return {
        "id": _make_hotel_id(hotel),
        "name": hotel.get("name", "N/A"),
        "description": hotel.get("description"),
        "latitude": coordinates.get("latitude"),
        "longitude": coordinates.get("longitude"),
        "rating": hotel.get("overall_rating"),
        "review_count": hotel.get("reviews"),
        "hotel_class": hotel.get("extracted_hotel_class"),
        "price": {
            "per_night": per_night,
            "total": total,
            "currency": "INR",
        },
        "check_in_time": hotel.get("check_in_time"),
        "check_out_time": hotel.get("check_out_time"),
        "amenities": _extract_amenities(hotel),
        "image_url": image_url,
        "website_url": hotel.get("link"),
        "nearby_places": _extract_nearby_places(hotel),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_hotels(
    city: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int,
) -> list[dict]:
    """
    Call SerpApi Google Hotels and return a list of normalized hotel dicts.

    Raises RuntimeError on configuration errors or upstream failures so
    the route layer can convert them into appropriate HTTP responses.
    """
    api_key = settings.serpapi_api_key
    if not api_key:
        raise RuntimeError(
            "SERPAPI_API_KEY is not set. Add it to the .env file."
        )

    params = {
        "engine": "google_hotels",
        "q": city,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": adults,
        "children": children,
        "currency": "INR",
        "gl": "in",
        "hl": "en",
        "api_key": api_key,
    }

    logger.info(
        "SerpApi request → city=%s check_in=%s check_out=%s adults=%d children=%d",
        city, check_in, check_out, adults, children,
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                SERPAPI_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
    except httpx.RequestError as exc:
        raise RuntimeError(f"SerpApi network error: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"SerpApi returned HTTP {response.status_code}. "
            "Check your API key and quota."
        )

    data = response.json()

    # SerpApi wraps results under "properties"
    raw_properties: list[dict] = data.get("properties") or []

    if not raw_properties:
        logger.info("SerpApi returned 0 properties for city=%s", city)

    return [_normalize_hotel(h) for h in raw_properties]
