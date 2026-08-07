"""
session.py
----------
Manages the persistent curl_cffi browser-impersonation session for the
RedBus provider.

Design decisions:
  - One session is created at import time and reused for all requests.
  - The session is "warmed" by visiting the RedBus homepage so that
    Akamai/PerimeterX can set their required cookies automatically.
  - create_and_warm_session() is the only public function.
    Call it once at startup and again after any session error.
"""

import logging
from curl_cffi import requests as cffi_requests

from provider.constants import REDBUS_HOME_URL, WARMUP_TIMEOUT

logger = logging.getLogger(__name__)


def create_and_warm_session() -> cffi_requests.Session:
    """
    Create a new curl_cffi Session with Chrome impersonation and warm it
    by requesting the RedBus homepage.

    The homepage visit allows Akamai Bot Manager to set its tracking cookies
    (_abck, bm_sz, bm_sv, etc.) in the session jar automatically — exactly
    as a real browser would behave.

    Returns:
        A ready-to-use, warmed curl_cffi Session.

    Raises:
        Exception: Propagated if the warm-up request fails critically.
                   The caller (client.py) handles retry logic.
    """
    session = cffi_requests.Session(impersonate="chrome")

    logger.info("RedBus session: warming up via homepage ...")
    try:
        resp = session.get(REDBUS_HOME_URL, timeout=WARMUP_TIMEOUT)
        logger.info(
            "RedBus session: warm-up complete. "
            f"status={resp.status_code}  cookies={len(session.cookies)}"
        )
    except Exception as exc:
        logger.warning(f"RedBus session: warm-up request failed — {exc}")
        # Non-fatal: let the search attempt proceed; it may still work.

    return session
