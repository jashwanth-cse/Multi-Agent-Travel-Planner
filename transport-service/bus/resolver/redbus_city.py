"""
resolver/redbus_city.py
-----------------------
Resolves human-readable city names to their RedBus numeric city IDs.

Strategy (confirmed by live probing):
  1. Build the slug URL:
       https://www.redbus.in/bus-tickets/{source_slug}-to-{destination_slug}
  2. Fetch the page using curl_cffi Chrome impersonation (consistent with
     the existing provider architecture).
  3. Extract fromCityId + toCityId from the HTML using the confirmed pattern:
       fromCityId=(\d+)   toCityId=(\d+)
     (These appear verbatim inside href/onclick attributes throughout the page.)
  4. Also extract the canonical city names (fromCityName / toCityName) for
     the response object.

Responsibilities — strictly limited to:
  - City name normalisation
  - Slug construction
  - HTTP fetch (curl_cffi, Chrome impersonation)
  - ID + name extraction from HTML
  - Raising typed resolver exceptions

Does NOT:
  - Know anything about the searchResults endpoint
  - Perform any bus searching
  - Cache results
"""

import re
import logging
from typing import Dict, Optional
from urllib.parse import quote

from curl_cffi import requests as cffi_requests

from resolver.exceptions import (
    CityResolutionError,
    InvalidRouteError,
    ResolverUnavailableError,
    ResolverTimeoutError,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_REDBUS_HOME    = "https://www.redbus.in"
_ROUTE_BASE_URL = "https://www.redbus.in/bus-tickets"
_FETCH_TIMEOUT  = 25  # seconds

# Patterns confirmed by live HTML inspection
_PATTERN_FROM_ID   = re.compile(r"fromCityId=(\d+)")
_PATTERN_TO_ID     = re.compile(r"toCityId=(\d+)")
_PATTERN_FROM_NAME = re.compile(r"fromCityName=([^&\"']+)")
_PATTERN_TO_NAME   = re.compile(r"toCityName=([^&\"']+)")

# ── Module-level persistent session ──────────────────────────────────────────
# Separate from the provider session so the two concerns are independent.
_session: Optional[cffi_requests.Session] = None


def _get_session() -> cffi_requests.Session:
    """
    Return the module-level resolver session, creating and warming it if needed.
    The session is reused across all resolution calls.
    """
    global _session
    if _session is None:
        logger.info("RedbusCityResolver: creating resolver session ...")
        _session = cffi_requests.Session(impersonate="chrome")
        try:
            _session.get(_REDBUS_HOME, timeout=20)
            logger.info("RedbusCityResolver: session warmed up.")
        except Exception as exc:
            logger.warning(f"RedbusCityResolver: warm-up failed (non-fatal) — {exc}")
    return _session


def _reset_session() -> None:
    """Discard the current session so the next call creates a fresh one."""
    global _session
    _session = None


# ── City name normalisation ───────────────────────────────────────────────────

def _to_slug(city_name: str) -> str:
    """
    Normalise a city name into a RedBus URL slug.

    Rules:
      - Strip surrounding whitespace
      - Lowercase
      - Replace internal spaces / underscores with hyphens
      - URL-encode the result (handles special characters safely)

    Examples:
      "Rajapalayam"  → "rajapalayam"
      "New Delhi"    → "new-delhi"
      "Bengaluru "   → "bengaluru"
    """
    slug = city_name.strip().lower()
    slug = re.sub(r"[\s_]+", "-", slug)   # spaces/underscores → hyphens
    slug = re.sub(r"-+", "-", slug)        # collapse consecutive hyphens
    return quote(slug, safe="-")


# ── HTML extraction helpers ───────────────────────────────────────────────────

def _first_match(pattern: re.Pattern, html: str) -> Optional[str]:
    """Return the first captured group of *pattern* in *html*, or None."""
    m = pattern.search(html)
    return m.group(1) if m else None


def _extract_city_ids(html: str) -> Dict[str, Optional[str]]:
    """
    Extract fromCityId, toCityId, fromCityName, toCityName from the page HTML.
    Returns a dict; values are None if not found.
    """
    return {
        "from_id":   _first_match(_PATTERN_FROM_ID,   html),
        "to_id":     _first_match(_PATTERN_TO_ID,     html),
        "from_name": _first_match(_PATTERN_FROM_NAME, html),
        "to_name":   _first_match(_PATTERN_TO_NAME,   html),
    }


# ── Public resolver class ─────────────────────────────────────────────────────

class RedbusCityResolver:
    """
    Resolves human-readable city names to RedBus numeric city IDs.

    Usage:
        resolver = RedbusCityResolver()
        result = resolver.resolve("Rajapalayam", "Chennai")
        # → {"source_name": "Rajapalayam", "source_id": 497,
        #    "destination_name": "Chennai", "destination_id": 123}
    """

    def resolve(self, source_name: str, destination_name: str) -> Dict:
        """
        Resolve source and destination city names to RedBus city IDs.

        Args:
            source_name:      Origin city name (e.g. 'Rajapalayam', 'Chennai').
            destination_name: Destination city name (e.g. 'Chennai', 'Bangalore').

        Returns:
            {
                "source_name":      str,   # Canonical name from RedBus
                "source_id":        int,   # RedBus numeric city ID
                "destination_name": str,   # Canonical name from RedBus
                "destination_id":   int,   # RedBus numeric city ID
            }

        Raises:
            ResolverTimeoutError:     Page request timed out.
            ResolverUnavailableError: Network failure reaching RedBus.
            InvalidRouteError:        Route page returned non-200 status.
            CityResolutionError:      Page loaded but city IDs could not be extracted.
        """
        source_slug = _to_slug(source_name)
        dest_slug   = _to_slug(destination_name)
        route_url   = f"{_ROUTE_BASE_URL}/{source_slug}-to-{dest_slug}"

        logger.info(
            f"RedbusCityResolver.resolve: '{source_name}' → '{destination_name}'  |  {route_url}"
        )

        html = self._fetch_page(route_url)
        ids  = _extract_city_ids(html)

        from_id   = ids["from_id"]
        to_id     = ids["to_id"]
        from_name = ids["from_name"] or source_name.title()
        to_name   = ids["to_name"]   or destination_name.title()

        if not from_id or not to_id:
            logger.error(
                f"RedbusCityResolver: failed to extract city IDs from {route_url}. "
                f"Extracted: from_id={from_id}  to_id={to_id}"
            )
            raise CityResolutionError(
                f"Could not resolve city IDs for '{source_name}' → '{destination_name}'. "
                f"Please verify the city names are valid RedBus cities."
            )

        result = {
            "source_name":      _decode_name(from_name),
            "source_id":        int(from_id),
            "destination_name": _decode_name(to_name),
            "destination_id":   int(to_id),
        }

        logger.info(
            f"RedbusCityResolver.resolve: resolved — "
            f"{result['source_name']}={result['source_id']}  "
            f"{result['destination_name']}={result['destination_id']}"
        )
        return result

    def _fetch_page(self, url: str) -> str:
        """
        Fetch the RedBus route page and return its HTML text.
        Handles session errors with a single automatic refresh + retry.
        """
        session = _get_session()

        try:
            response = session.get(url, timeout=_FETCH_TIMEOUT)
        except cffi_requests.exceptions.Timeout:
            raise ResolverTimeoutError(
                f"RedBus route page timed out after {_FETCH_TIMEOUT}s: {url}"
            )
        except cffi_requests.exceptions.ConnectionError as exc:
            raise ResolverUnavailableError(
                f"Cannot reach RedBus: {exc}"
            )
        except Exception as exc:
            raise ResolverUnavailableError(
                f"Unexpected network error fetching RedBus route page: {exc}"
            )

        if response.status_code in {401, 403, 429}:
            # Session blocked — reset and retry once
            logger.warning(
                f"Resolver session blocked ({response.status_code}). Refreshing ..."
            )
            _reset_session()
            session = _get_session()
            try:
                response = session.get(url, timeout=_FETCH_TIMEOUT)
            except Exception as exc:
                raise ResolverUnavailableError(
                    f"RedBus route page unavailable after session refresh: {exc}"
                )

        if response.status_code != 200:
            raise InvalidRouteError(
                f"RedBus returned HTTP {response.status_code} for route page: {url}. "
                f"The city name combination may not be a valid RedBus route."
            )

        return response.text


# ── URL-decoded city name ─────────────────────────────────────────────────────

def _decode_name(raw: str) -> str:
    """
    URL-decode and clean a city name extracted from the HTML attribute.
    e.g. 'Rajapalayam' → 'Rajapalayam', 'New%20Delhi' → 'New Delhi'
    """
    from urllib.parse import unquote_plus
    return unquote_plus(raw).strip()
