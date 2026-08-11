"""
Bus Service — FastAPI Router

Responsibilities:
  - Declare and validate query parameters.
  - Call BusService.
  - Wrap response in the standard envelope.
  - No business logic.
"""

from fastapi import APIRouter, Depends, Query
from app.services.bus_service import BusService
from app.models.response_models import BusSearchResponse, ErrorResponse

router = APIRouter()

# Module-level singleton — shared across all requests
_bus_service = BusService()


def get_bus_service() -> BusService:
    return _bus_service


@router.get(
    "/search",
    response_model=BusSearchResponse,
    summary="Search for buses",
    description=(
        "Search for available buses between two Indian cities on a given date.\n\n"
        "City names are automatically resolved to their internal RedBus IDs — "
        "no need to look up numeric IDs.\n\n"
        "**Date formats accepted:**\n"
        "- `DD-MM-YYYY` — e.g. `26-08-2026` (auto-converted)\n"
        "- `YYYY-MM-DD` — e.g. `2026-08-26` (auto-converted)\n"
        "- `DD-Mon-YYYY` — e.g. `26-Aug-2026` (RedBus native)\n\n"
        "**Tip:** Use the standard English city name as it appears on RedBus "
        "(e.g. `Chennai`, `Bangalore`, `Rajapalayam`)."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "City not found or no buses on this route/date"},
        400: {"model": ErrorResponse, "description": "Invalid city combination"},
        503: {"model": ErrorResponse, "description": "Bus provider temporarily unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def search_buses(
    source: str = Query(
        ...,
        description="Origin city name (e.g. 'Rajapalayam', 'Chennai', 'Mumbai')",
        examples=["Rajapalayam"],
    ),
    destination: str = Query(
        ...,
        description="Destination city name (e.g. 'Chennai', 'Bangalore', 'Pune')",
        examples=["Chennai"],
    ),
    journey_date: str = Query(
        ...,
        description=(
            "Date of journey. Accepted formats:\n"
            "- `DD-MM-YYYY` (e.g. `26-08-2026`) — auto-converted\n"
            "- `YYYY-MM-DD` (e.g. `2026-08-26`) — auto-converted\n"
            "- `DD-Mon-YYYY` (e.g. `26-Aug-2026`) — RedBus native"
        ),
        examples=["26-08-2026"],
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of buses to return (1–50)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of results to skip for pagination",
    ),
    sortBy: str = Query(
        default="departure",
        description="Sort order: 'fare' | 'departure' (default) | 'arrival' | 'duration'",
    ),
    bus_service: BusService = Depends(get_bus_service),
):
    """
    Search for buses between two cities.

    - **source**: Origin city name
    - **destination**: Destination city name
    - **journey_date**: Date in `DD-MM-YYYY`, `YYYY-MM-DD`, or `DD-Mon-YYYY` format
    - **limit**: Page size (max 50)
    - **offset**: Pagination offset
    - **sortBy**: Sort order — `fare`, `departure` (default), `arrival`, `duration`
    """
    data = bus_service.search(
        source=source,
        destination=destination,
        journey_date=journey_date,
        limit=limit,
        offset=offset,
        sort_by=sortBy,
    )

    return BusSearchResponse(
        success=True,
        message="Bus search successful",
        data=data,
    )
