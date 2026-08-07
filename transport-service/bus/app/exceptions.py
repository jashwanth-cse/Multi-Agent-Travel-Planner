"""
Bus Service — Application Exceptions

Service-layer exceptions separate from the provider-layer exceptions.
The router catches these and maps them to appropriate HTTP status codes.
"""


class BusServiceError(Exception):
    """Base exception for all bus service errors."""


class BusSearchError(BusServiceError):
    """Raised when a bus search fails due to a provider or network issue."""


class BusProviderUnavailableError(BusServiceError):
    """Raised when the bus provider is unreachable or returns a session error."""


class BusNoResultsError(BusServiceError):
    """Raised when no buses are found for the requested route and date."""
