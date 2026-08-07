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
        "Search for available buses between two RedBus city IDs on a given date. "
        "Internally powered by the RedBus provider via curl_cffi Chrome impersonation.\n\n"
        "**How to find city IDs:**\n"
        "Open redbus.in → search a route → the URL will contain "
        "`fromCityId=<ID>&toCityId=<ID>`. Use those values here."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "No buses found for this route / date"},
        503: {"model": ErrorResponse, "description": "Bus provider temporarily unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def search_buses(
    source_id: int = Query(
        ...,
        description="RedBus numeric city ID for the origin (e.g. 497 for Rajapalayam)",
        examples=[497],
    ),
    destination_id: int = Query(
        ...,
        description="RedBus numeric city ID for the destination (e.g. 141 for Coimbatore)",
        examples=[141],
    ),
    journey_date: str = Query(
        ...,
        description="Date of journey in DD-Mon-YYYY format (e.g. 21-Aug-2026)",
        examples=["21-Aug-2026"],
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
    bus_service: BusService = Depends(get_bus_service),
):
    """
    Search for buses between two cities.

    - **source_id**: RedBus city ID for the origin
    - **destination_id**: RedBus city ID for the destination
    - **journey_date**: Date in `DD-Mon-YYYY` format
    - **limit**: Page size (max 50)
    - **offset**: Pagination offset
    """
    data = bus_service.search(
        source_id=source_id,
        destination_id=destination_id,
        journey_date=journey_date,
        limit=limit,
        offset=offset,
    )

    return BusSearchResponse(
        success=True,
        message="Bus search successful",
        data=data,
    )
