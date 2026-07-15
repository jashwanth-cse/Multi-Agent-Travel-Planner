import requests
import logging
from typing import Dict, Any, List, Optional
import datetime

from app.config import config

logger = logging.getLogger(__name__)
_session = requests.Session()

class AvailabilityService:
    """
    Service class to handle live train availability checks.
    """

    def __init__(self) -> None:
        self.url = config.AVAILABILITY_API
        self.headers = config.TRAIN_HEADERS

    def _build_params(self, train_no: str, source: str, destination: str, travel_class: str, quota: str, date: str) -> Dict[str, Any]:
        """Builds query parameters for the POST request."""
        # The API likely expects camelCase for JSON body based on ixigo patterns.
        return {
            "trainNo": train_no,
            "sourceStationCode": source,
            "destinationStationCode": destination,
            "travelClass": travel_class,
            "quota": quota,
            "dateOfJourney": date
        }

    def _call_ixigo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Makes the POST request to the Ixigo Availability API."""
        try:
            logger.info(f"Ixigo API Request: POST {self.url} with params: {params}")
            response = _session.post(
                self.url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            logger.info(f"Ixigo API Response Status: {response.status_code}")
            if response.status_code != 200:
                logger.debug(f"Ixigo API Error Response Body: {response.text}")
            
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

    def _parse_booking_status(self, availability_str: str) -> str:
        """Parses raw availability string into standardized booking_status."""
        av_upper = str(availability_str).upper()
        if "CURR_AVBL" in av_upper or "AVAILABLE" in av_upper or "AVL" in av_upper:
            return "AVAILABLE"
        if "RAC" in av_upper:
            return "RAC"
        if "WL" in av_upper or "WAITLIST" in av_upper:
            return "WL"
        if "REGRET" in av_upper:
            return "REGRET"
        return "UNKNOWN"

    def fetch_availability(
        self,
        train_no: str,
        source: str,
        destination: str,
        travel_class: str,
        date: str,
        quota: str = "GN"
    ) -> Dict[str, Any]:
        """
        Fetches live availability and returns a clean response.
        """
        params = self._build_params(train_no, source, destination, travel_class, quota, date)
        
        try:
            raw_data = self._call_ixigo(params)
            
            # Extract data from raw response
            # Assuming raw_data contains the availability inside a `data` or similar key, or at the root.
            # Ixigo fetchAvailability often returns data directly or under 'data'.
            # The ixigo response encapsulates the actual availability inside data.avlDayList[0]
            data = raw_data.get("data", raw_data)
            avl_day_list = data.get("avlDayList", [])
            avl_info = avl_day_list[0] if avl_day_list and isinstance(avl_day_list, list) else {}
            
            # The exact display name e.g., 'AVL 282' or 'WL 12'
            availability_str = str(
                avl_info.get("availabilityDisplayName") or 
                avl_info.get("availablityStatus") or 
                ""
            )
            booking_status = self._parse_booking_status(availability_str)
            
            # Extract fares from fareInfo
            fare_info = data.get("fareInfo", {})
            
            fare_val = fare_info.get("baseFare", fare_info.get("totalFare", 0))
            try:
                fare = int(float(fare_val))
            except (ValueError, TypeError):
                fare = 0
                
            total_fare_val = fare_info.get("totalCollectibleAmount", fare_info.get("totalFare", fare))
            try:
                total_fare = int(float(total_fare_val))
            except (ValueError, TypeError):
                total_fare = fare
            
            # Prediction from avl_info
            prediction_val = avl_info.get("predictionPercentage", 0)
            try:
                prediction = int(prediction_val)
            except (ValueError, TypeError):
                prediction = 0
                
            booking_enabled = bool(avl_info.get("enableBookButton", True))
            last_updated = str(data.get("timeStamp", datetime.datetime.now().isoformat()))
            
            # Additional available dates in the list (if any)
            next_available_dates = []
            if len(avl_day_list) > 1:
                next_available_dates = [item.get("availablityDate") for item in avl_day_list[1:] if item.get("availablityDate")]


            return {
                "success": True,
                "message": "Live availability fetched",
                "data": {
                    "train_number": train_no,
                    "travel_class": travel_class,
                    "quota": quota,
                    "availability": availability_str,
                    "booking_status": booking_status,
                    "prediction": prediction,
                    "fare": fare,
                    "total_fare": total_fare,
                    "booking_enabled": booking_enabled,
                    "last_updated": last_updated,
                    "next_available_dates": next_available_dates
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "data": None
            }
