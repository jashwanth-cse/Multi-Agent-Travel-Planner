from fastapi import APIRouter, Depends, Query
from app.services.station_service import StationService
from app.models.response_models import StationSearchResponse, ErrorResponse

router = APIRouter()

station_service = StationService()

def get_station_service():
    return station_service

@router.get(
    "/search",
    response_model=StationSearchResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
def search_stations(
    q: str = Query(..., description="The name of the station to search for"),
    station_service: StationService = Depends(get_station_service)
):
    """
    Search for a railway station by name.
    """
    stations = station_service.search(q)
    return StationSearchResponse(
        success=True,
        message="Stations found",
        data=stations
    )
