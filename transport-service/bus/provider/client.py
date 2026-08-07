"""
client.py
---------
Responsible ONLY for:
  1. Maintaining the persistent curl_cffi session.
  2. Warming the session via the RedBus homepage.
  3. Making the POST request to the searchResults endpoint.
  4. Detecting session expiry and retrying exactly once.
  5. Raising typed provider exceptions on all failure modes.

No parsing logic lives here.
"""

import logging
from typing import Any, Dict

from curl_cffi import requests as cffi_requests

from provider.constants import (
    REDBUS_SEARCH_URL,
    DEFAULT_QUERY_PARAMS,
    DEFAULT_PAYLOAD,
    REQUEST_HEADERS,
    SEARCH_TIMEOUT,
    SESSION_EXPIRED_CODES,
)
from provider.exceptions import (
    RedbusConnectionError,
    RedbusTimeoutError,
    RedbusSessionExpiredError,
    RedbusEmptyResponseError,
    RedbusParseError,
)
from provider.session import create_and_warm_session

logger = logging.getLogger(__name__)

# ── Module-level persistent session ──────────────────────────────────────────
# Initialised once; reused for every search.  Replaced only on session error.
_session: cffi_requests.Session = create_and_warm_session()


def _build_params(from_city: int, to_city: int, doj: str) -> Dict[str, Any]:
    """Merge per-request params with the static defaults."""
    return {
        **DEFAULT_QUERY_PARAMS,
        "fromCity": from_city,
        "toCity":   to_city,
        "DOJ":      doj,
    }


def _do_post(
    session: cffi_requests.Session,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute the POST request and return the parsed JSON.
    Raises typed exceptions on every failure mode.
    """
    logger.info(
        f"RedBus POST {REDBUS_SEARCH_URL} | "
        f"fromCity={params['fromCity']} toCity={params['toCity']} DOJ={params['DOJ']}"
    )

    try:
        response = session.post(
            REDBUS_SEARCH_URL,
            params=params,
            json=DEFAULT_PAYLOAD,
            headers=REQUEST_HEADERS,
            timeout=SEARCH_TIMEOUT,
        )
    except cffi_requests.exceptions.Timeout:
        raise RedbusTimeoutError(
            f"RedBus API timed out after {SEARCH_TIMEOUT}s"
        )
    except cffi_requests.exceptions.ConnectionError as exc:
        raise RedbusConnectionError(
            f"Unable to connect to RedBus: {exc}"
        )
    except Exception as exc:
        raise RedbusConnectionError(
            f"Unexpected network error reaching RedBus: {exc}"
        )

    logger.info(f"RedBus response: status={response.status_code}  size={len(response.content)} bytes")

    # ── Session expiry detection ───────────────────────────────────────────────
    if response.status_code in SESSION_EXPIRED_CODES:
        raise RedbusSessionExpiredError(
            f"RedBus returned {response.status_code} — session expired or blocked"
        )

    # ── HTTP errors ───────────────────────────────────────────────────────────
    if response.status_code != 200:
        logger.debug(f"RedBus error body: {response.text[:400]}")
        raise RedbusConnectionError(
            f"RedBus returned HTTP {response.status_code}"
        )

    # ── Parse JSON ────────────────────────────────────────────────────────────
    try:
        data = response.json()
    except Exception as exc:
        logger.debug(f"RedBus non-JSON body: {response.text[:400]}")
        raise RedbusParseError(
            f"RedBus response is not valid JSON: {exc}"
        )

    # ── Sanity-check the top-level structure ──────────────────────────────────
    if not isinstance(data, dict):
        raise RedbusParseError("RedBus response root is not a JSON object")

    return data


def fetch_inventory(from_city: int, to_city: int, doj: str) -> Dict[str, Any]:
    """
    Public entry point.  Fetches the raw inventory JSON from RedBus.

    Implements the automatic session-refresh retry:
      - On the first attempt, use the existing persistent session.
      - If a session-expiry error is detected (401/403/429 or empty body),
        dispose the old session, create and warm a fresh one, then retry once.
      - If the retry also fails, the exception propagates to the caller.

    Args:
        from_city: RedBus city ID for origin.
        to_city:   RedBus city ID for destination.
        doj:       Date of journey in DD-Mon-YYYY format (e.g. '30-Jul-2026').

    Returns:
        Raw response dict (the full JSON body from RedBus).

    Raises:
        RedbusTimeoutError
        RedbusConnectionError
        RedbusSessionExpiredError   (only if retry also fails)
        RedbusEmptyResponseError
        RedbusParseError
    """
    global _session

    params = _build_params(from_city, to_city, doj)

    # ── First attempt ─────────────────────────────────────────────────────────
    try:
        raw = _do_post(_session, params)
        _validate_inventory(raw)
        return raw

    except RedbusSessionExpiredError as exc:
        logger.warning(f"Session expired on first attempt ({exc}). Refreshing ...")

    except RedbusEmptyResponseError:
        # An empty 200 can also mean a dead session — refresh and retry.
        logger.warning("Empty inventory on first attempt. Refreshing session ...")

    # ── Session refresh ───────────────────────────────────────────────────────
    logger.info("Creating and warming a fresh RedBus session ...")
    _session = create_and_warm_session()

    # ── Retry (once) ──────────────────────────────────────────────────────────
    logger.info("Retrying search with fresh session ...")
    raw = _do_post(_session, params)
    _validate_inventory(raw)
    return raw


def _validate_inventory(data: Dict[str, Any]) -> None:
    """
    Raise RedbusEmptyResponseError if the response carries no inventory.
    An empty 200 is treated as a session or data issue, not a normal result.
    """
    inventories = data.get("data", {}).get("inventories")
    if inventories is None:
        raise RedbusEmptyResponseError(
            "RedBus response has no 'data.inventories' key — "
            "possible session or structural issue"
        )
