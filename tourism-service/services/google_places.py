"""
Google Places API service layer.

Mirrors the logic in ../places.py (the reference implementation) but uses
async httpx for non-blocking I/O and fetches photo URLs concurrently.
"""

import asyncio
import os
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PHOTO_MEDIA_URL = "https://places.googleapis.com/v1/{resource_name}/media"

FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.rating,"
    "places.userRatingCount,"
    "places.googleMapsUri,"
    "places.photos,"
    "places.types"
)

MAX_PHOTO_WIDTH_PX = 800
REQUEST_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api_key() -> str:
    """Return the Google Maps API key from the environment."""
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GOOGLE_MAPS_API_KEY is not set. "
            "Add it to the .env file in tourism_service/."
        )
    return key


async def _fetch_photo_url(
    client: httpx.AsyncClient,
    photo_resource_name: str,
    api_key: str,
) -> Optional[str]:
    """
    Convert a Google photo resource name into an actual image URL.

    Equivalent to get_photo_url() in places.py but async.
    Uses skipHttpRedirect=true so the API returns the URL as JSON
    rather than issuing a redirect — giving us a stable URL we can
    hand directly to the frontend as <img src="...">.
    """
    url = PHOTO_MEDIA_URL.format(resource_name=photo_resource_name)
    params = {
        "key": api_key,
        "maxWidthPx": MAX_PHOTO_WIDTH_PX,
        "skipHttpRedirect": "true",
    }

    try:
        response = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            return data.get("photoUri")
    except httpx.RequestError:
        pass  # silently return None — image is optional

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_tourist_attractions(
    city_name: str,
    max_results: int = 10,
) -> list[dict]:
    """
    Search Google Places for tourist attractions in *city_name* and
    return a list of attraction dicts ready to be consumed by the
    Pydantic response model.

    Photo URLs are resolved concurrently to keep total latency low.
    """
    api_key = _api_key()

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    payload = {
        "textQuery": f"tourist attractions in {city_name}",
        "maxResultCount": min(max_results, 20),
    }

    async with httpx.AsyncClient() as client:

        # ----------------------------------------------------------------
        # 1. Text search — identical to the requests.post() in places.py
        # ----------------------------------------------------------------
        try:
            search_response = await client.post(
                SEARCH_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Google Places search request failed: {exc}"
            ) from exc

        if search_response.status_code != 200:
            raise RuntimeError(
                f"Google Places API error {search_response.status_code}: "
                f"{search_response.text}"
            )

        places_data = search_response.json().get("places", [])

        # ----------------------------------------------------------------
        # 2. Resolve photo resource names → actual URLs **concurrently**
        # ----------------------------------------------------------------
        photo_tasks = []
        for place in places_data:
            photos = place.get("photos", [])
            resource_name = photos[0].get("name") if photos else None
            if resource_name:
                photo_tasks.append(
                    _fetch_photo_url(client, resource_name, api_key)
                )
            else:
                # Use a resolved coroutine that immediately returns None
                photo_tasks.append(_noop())

        photo_urls: list[Optional[str]] = await asyncio.gather(*photo_tasks)

        # ----------------------------------------------------------------
        # 3. Build result list — same field mapping as places.py
        # ----------------------------------------------------------------
        results: list[dict] = []

        for place, image_url in zip(places_data, photo_urls):
            location = place.get("location", {})

            attraction = {
                "name": place.get("displayName", {}).get("text", "N/A"),
                "address": place.get("formattedAddress", "N/A"),
                "rating": place.get("rating"),
                "review_count": place.get("userRatingCount", 0),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "google_maps_url": place.get("googleMapsUri"),
                "image_url": image_url,
                "types": place.get("types", []),
            }

            results.append(attraction)

        return results


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _noop() -> None:
    """Awaitable that resolves immediately to None."""
    return None
