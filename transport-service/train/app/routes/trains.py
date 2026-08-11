from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.services.train_service import TrainService
from app.models.response_models import TrainSearchResponse, ErrorResponse

router = APIRouter()

train_service = TrainService()

def get_train_service():
    return train_service

@router.get(
    "/search",
    response_model=TrainSearchResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
def search_trains(
    from_station: str = Query(..., alias="from", description="Source station name"),
    to_station: str = Query(..., alias="to", description="Destination station name"),
    date: str = Query(..., description="Date in DD-MM-YYYY format"),
    travelClass: Optional[str] = Query(None, description="Travel class filter (e.g. 3A)"),
    sortBy: str = Query("departure", description="Sort by fare, departure, arrival, duration"),
    maxFare: Optional[int] = Query(None, description="Maximum fare filter"),
    minRating: Optional[float] = Query(None, description="Minimum rating filter"),
    pantry: Optional[bool] = Query(None, description="Pantry availability filter"),
    quota: str = Query("GN", description="Quota for live availability enrichment (default GN)"),
    train_service: TrainService = Depends(get_train_service)
):
    """
    Search for trains between two stations.
    """
    trains_data = train_service.search(
        source=from_station,
        destination=to_station,
        journey_date=date,
        travel_class=travelClass,
        sort_by=sortBy,
        max_fare=maxFare,
        min_rating=minRating,
        pantry=pantry,
        quota=quota,
    )
    
    return TrainSearchResponse(
        success=True,
        message="Train search successful",
        data=trains_data
    )
