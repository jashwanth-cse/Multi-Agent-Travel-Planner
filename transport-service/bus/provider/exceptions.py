"""
exceptions.py
-------------
Provider-specific exceptions for the RedBus bus search provider.

Rules:
  - Never return None on failure.
  - Never swallow exceptions silently.
  - Always include a meaningful, human-readable message.
"""


class RedbusProviderError(Exception):
    """Base class for all RedBus provider errors."""


class RedbusConnectionError(RedbusProviderError):
    """Raised when the network connection to RedBus fails."""


class RedbusTimeoutError(RedbusProviderError):
    """Raised when a request to RedBus exceeds the configured timeout."""


class RedbusSessionExpiredError(RedbusProviderError):
    """Raised when the session is blocked or expired (401 / 403 / 429)."""


class RedbusEmptyResponseError(RedbusProviderError):
    """Raised when RedBus returns a 200 but with no usable inventory."""


class RedbusParseError(RedbusProviderError):
    """Raised when the response JSON cannot be parsed into the expected shape."""
