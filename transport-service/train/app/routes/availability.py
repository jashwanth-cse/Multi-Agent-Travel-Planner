from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.availability_service import AvailabilityService

router = APIRouter()
availability_service = AvailabilityService()

@router.post(
    "",
    summary="Get Live Train Availability",
    description="Fetch live availability for a specific train and travel class."
)
async def get_availability(
    trainNo: str = Query(..., description="Train Number"),
    source: str = Query(..., description="Source Station Code"),
    destination: str = Query(..., description="Destination Station Code"),
    travelClass: str = Query(..., description="Travel Class (e.g., 3A, SL)"),
    date: str = Query(..., description="Date of Journey (DD-MM-YYYY)"),
    quota: str = Query("GN", description="Quota (default GN)")
):
    result = availability_service.fetch_availability(
        train_no=trainNo,
        source=source,
        destination=destination,
        travel_class=travelClass,
        date=date,
        quota=quota
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to fetch availability"))
        
    return result
