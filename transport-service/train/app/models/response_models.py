from pydantic import BaseModel, Field
from typing import List, Optional, Any


# ---------------------------------------------------------
# Station Models
# ---------------------------------------------------------

class Station(BaseModel):
    station_name: str
    station_code: str
    latitude: float
    longitude: float

class StationSearchResponse(BaseModel):
    success: bool
    message: str
    data: List[Station]

# ---------------------------------------------------------
# Train Models
# ---------------------------------------------------------

class StationSimple(BaseModel):
    code: str
    name: str

class TravelClass(BaseModel):
    travel_class: str
    fare: int
    availability: str
    prediction: int
    bookable: bool

class Train(BaseModel):
    train_number: str
    train_name: str
    train_type: str
    from_: StationSimple = Field(alias="from")
    to: StationSimple
    departure_time: str
    arrival_time: str
    duration_minutes: int
    duration: str
    distance: int
    running_days: List[str]
    rating: float
    has_pantry: bool
    lowest_fare: int
    recommended_class: Optional[TravelClass] = None
    classes: List[TravelClass]

class TrainSearchData(BaseModel):
    result_type: str
    source: str
    destination: str
    total_trains: int
    trains: List[Train]

class TrainSearchResponse(BaseModel):
    success: bool
    message: str
    data: TrainSearchData

# ---------------------------------------------------------
# Generic Models
# ---------------------------------------------------------

class ErrorResponse(BaseModel):
    success: bool
    message: str
