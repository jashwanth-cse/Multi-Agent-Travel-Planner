"""
resolver/exceptions.py
-----------------------
Resolver-specific exceptions for city name → RedBus city ID resolution.
"""


class ResolverError(Exception):
    """Base class for all resolver errors."""


class CityResolutionError(ResolverError):
    """Raised when city IDs cannot be extracted from the RedBus route page."""


class InvalidRouteError(ResolverError):
    """Raised when the source/destination combination yields no valid RedBus route page."""


class ResolverUnavailableError(ResolverError):
    """Raised when the RedBus page cannot be reached (network / connection error)."""


class ResolverTimeoutError(ResolverError):
    """Raised when the RedBus page request exceeds the configured timeout."""
