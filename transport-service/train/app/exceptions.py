class StationNotFoundError(Exception):
    """Raised when a requested station cannot be found."""
    pass

class InvalidRequestError(Exception):
    """Raised when the request parameters are invalid."""
    pass
