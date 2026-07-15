"""
Train Search Service

Responsible for resolving station names to codes, querying the Ixigo API,
and parsing the raw JSON response into a clean, strictly typed structure.
"""

import requests
from typing import Dict, List, Optional, Any

from app.config import config
from app.services.station_service import StationService

# Global session for connection pooling
_session = requests.Session()

class TrainService:
    """
    Service class to handle train searches between two stations.
    Stateless and thread-safe.
    """

    def __init__(self) -> None:
        self.url = config.TRAIN_API
        self.headers = config.TRAIN_HEADERS
        self.station_service = StationService()

    def _build_params(self, source_code: str, dest_code: str, journey_date: str) -> Dict[str, str]:
        """Builds query parameters for the Ixigo API request."""
        return {
            "sourceStationCode": source_code,
            "destinationStationCode": dest_code,
            "addAvailabilityCache": "true",
            "excludeMultiTicketAlternates": "false",
            "excludeBoostAlternates": "false",
            "sortBy": "DEFAULT",
            "dateOfJourney": journey_date,
            "enableNearby": "true",
            "enableTG": "true",
            "tGPlan": "ITG-A50",
            "showTGPrediction": "false",
            "tgColor": "DEFAULT",
            "showPredictionGlobal": "true",
            "showNewAlternates": "true",
            "showNewAltText": "true"
        }

    def _call_ixigo(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Makes the HTTP request to the Ixigo API."""
        try:
            response = _session.get(
                self.url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception("Ixigo API Timeout")
        except requests.exceptions.ConnectionError:
            raise Exception("Unable to connect to Ixigo")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error : {e}")
        except Exception as e:
            raise Exception(f"Unknown Error : {e}")

    # --------------------------------------------------------
    # Search & Parse
    # --------------------------------------------------------

    def search(
        self,
        source: str,
        destination: str,
        journey_date: str,
        travel_class: Optional[str] = None,
        sort_by: str = "departure",
        max_fare: Optional[int] = None,
        min_rating: Optional[float] = None,
        pantry: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Main entry point to search for trains.
        """
        source_station = self.station_service.get_station(source)
        dest_station = self.station_service.get_station(destination)

        params = self._build_params(source_station["station_code"], dest_station["station_code"], journey_date)
        raw_data = self._call_ixigo(params)
        
        payload = raw_data.get("data", {})
        trains_data = payload.get("trainList", [])
        result_type = "direct"

        if not trains_data:
            trains_data = payload.get("nearbyTrains", [])
            result_type = "nearby"

        parsed_trains = []
        for train in trains_data:
            parsed_train = self._parse_train(train, source_station, dest_station)
            
            # Filter classes
            parsed_train["classes"] = self._filter_classes(parsed_train["classes"], travel_class)
            
            # Re-evaluate lowest fare and recommendation after filtering
            parsed_train["recommended_class"] = self._recommend_class(parsed_train["classes"])
            parsed_train["lowest_fare"] = self._calculate_lowest_fare(parsed_train["classes"])
            
            # Apply optional filters
            if max_fare is not None and parsed_train["lowest_fare"] > max_fare:
                continue
            if min_rating is not None and parsed_train["rating"] < min_rating:
                continue
            if pantry is not None and parsed_train["has_pantry"] != pantry:
                continue
            
            # Only include trains that still have matching classes after filter
            if parsed_train["classes"]:
                parsed_trains.append(parsed_train)

        # Sort trains
        parsed_trains = self._sort_trains(parsed_trains, sort_by)

        return {
            "result_type": result_type,
            "source": payload.get("sourceStationName") or source_station["station_name"],
            "destination": payload.get("destinationStationName") or dest_station["station_name"],
            "total_trains": len(parsed_trains),
            "trains": parsed_trains
        }

    # --------------------------------------------------------
    # Private Parsing Helpers
    # --------------------------------------------------------

    def _parse_train(self, train: Dict[str, Any], source_station: Dict[str, str], dest_station: Dict[str, str]) -> Dict[str, Any]:
        """Extracts desired fields from a raw train object."""
        classes = self._parse_classes(train)
        
        from_code = train.get("fromStnCode", "")
        to_code = train.get("toStnCode", "")
        
        # If the train departs/arrives exactly at the queried station, use the resolved name.
        from_name = source_station["station_name"] if from_code == source_station["station_code"] else train.get("fromStnName", from_code)
        to_name = dest_station["station_name"] if to_code == dest_station["station_code"] else train.get("toStnName", to_code)
        
        duration_mins = train.get("duration", 0)

        return {
            "train_number": train.get("trainNumber", ""),
            "train_name": train.get("trainName", ""),
            "train_type": train.get("trainType", ""),
            "from": {
                "code": from_code,
                "name": from_name
            },
            "to": {
                "code": to_code,
                "name": to_name
            },
            "departure_time": train.get("departureTime", ""),
            "arrival_time": train.get("arrivalTime", ""),
            "duration_minutes": duration_mins,
            "duration": self._minutes_to_duration(duration_mins),
            "distance": train.get("distance", 0),
            "running_days": self._parse_running_days(train.get("runningDays", "")),
            "rating": train.get("trainRating", 0),
            "has_pantry": bool(train.get("hasPantry")),
            "lowest_fare": self._calculate_lowest_fare(classes),
            "recommended_class": self._recommend_class(classes) or {},
            "classes": classes
        }

    def _parse_classes(self, train: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parses the availabilityCache into a list of standardized class objects."""
        availability = train.get("availabilityCache", {})
        parsed = []
        for class_name, details in availability.items():
            parsed.append(self._parse_class(class_name, details))
        return parsed

    def _parse_class(self, class_name: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Parses an individual class detail object."""
        fare = int(details.get("fare") or 0)
        availability = details.get("availabilityDisplayName") or details.get("availability") or ""
        prediction = details.get("predictionPercentage") or 0
        
        is_bookable = "REGRET" not in str(availability).upper()

        return {
            "travel_class": class_name,
            "fare": fare,
            "availability": availability,
            "prediction": prediction,
            "bookable": is_bookable
        }

    # --------------------------------------------------------
    # Static Utility Helpers
    # --------------------------------------------------------

    @staticmethod
    def _calculate_lowest_fare(classes: List[Dict[str, Any]]) -> int:
        fares = [c["fare"] for c in classes if c["fare"] > 0]
        return min(fares) if fares else 0

    @staticmethod
    def _minutes_to_duration(minutes: int) -> str:
        if not minutes:
            return "0h 0m"
        hrs = minutes // 60
        mins = minutes % 60
        return f"{hrs}h {mins}m"

    @staticmethod
    def _parse_running_days(days: str) -> List[str]:
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if not days or len(days) != 7:
            return []
        return [names[i] for i, val in enumerate(days) if val == "1"]

    @staticmethod
    def _recommend_class(classes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Recommendations priority:
        1. AVAILABLE / AVL
        2. RAC
        3. Highest prediction percentage
        Never recommend REGRET.
        """
        if not classes:
            return None
            
        valid_classes = [c for c in classes if "REGRET" not in str(c.get("availability", "")).upper()]
        if not valid_classes:
            return None
            
        avl_classes = [
            c for c in valid_classes 
            if "AVL" in str(c.get("availability", "")).upper() 
            or "AVAILABLE" in str(c.get("availability", "")).upper()
        ]
        if avl_classes:
            return min(avl_classes, key=lambda x: x.get("fare", float('inf')))
            
        rac_classes = [
            c for c in valid_classes 
            if "RAC" in str(c.get("availability", "")).upper()
        ]
        if rac_classes:
            return min(rac_classes, key=lambda x: x.get("fare", float('inf')))
            
        return max(valid_classes, key=lambda x: (x.get("prediction", 0), -x.get("fare", 0)))

    @staticmethod
    def _filter_classes(classes: List[Dict[str, Any]], travel_class: Optional[str]) -> List[Dict[str, Any]]:
        if not travel_class:
            return classes
        travel_class = travel_class.upper()
        return [c for c in classes if c.get("travel_class") == travel_class]

    @staticmethod
    def _sort_trains(trains: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        sort_by = sort_by.lower()
        if sort_by == "departure":
            return sorted(trains, key=lambda x: x.get("departure_time", ""))
        elif sort_by == "arrival":
            return sorted(trains, key=lambda x: x.get("arrival_time", ""))
        elif sort_by == "duration":
            return sorted(trains, key=lambda x: x.get("duration_minutes", float('inf')))
        elif sort_by == "fare":
            return sorted(trains, key=lambda x: x.get("lowest_fare", float('inf')))
        return trains