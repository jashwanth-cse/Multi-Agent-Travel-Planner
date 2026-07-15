"""
Station Search Service

Converts

Rajapalayam

↓

RJPM
"""

import requests
from app.config import config
from app.utils import parse_station
from app.exceptions import StationNotFoundError

# Global session for connection pooling
_session = requests.Session()

class StationService:

    def __init__(self):

        self.url = config.STATION_API
        self.headers = config.STATION_HEADERS

    def search(self, station_name: str):

        params = {
            "searchFor": "trainstationsLatLon",
            "anchor": "false",
            "value": station_name
        }

        try:
            response = _session.get(
                self.url,
                params=params,
                headers=self.headers,
                timeout=20
            )

            response.raise_for_status()

            data = response.json()

        except requests.exceptions.RequestException as e:

            raise Exception(
                f"Station API Error : {e}"
            )

        stations = []

        for item in data:

            station = parse_station(item["e"])

            if station is None:
                continue

            station["latitude"] = float(item["lat"])
            station["longitude"] = float(item["lon"])

            stations.append(station)

        return stations

    # ------------------------------------

    def get_station_code(
        self,
        station_name: str
    ):

        stations = self.search(station_name)

        if len(stations) == 0:
            raise StationNotFoundError(f"No station found for '{station_name}'")

        return stations[0]["station_code"]

    # ------------------------------------

    def get_station(
        self,
        station_name: str
    ):

        stations = self.search(station_name)

        if len(stations) == 0:
            raise StationNotFoundError(f"No station found for '{station_name}'")

        return stations[0]


# ----------------------------------------

if __name__ == "__main__":

    service = StationService()

    stations = service.search("rajapalayam")

    print()

    print("Available Stations")

    print("-" * 50)

    for station in stations:

        print(station)

    print()

    print(
        "Selected Code :",
        service.get_station_code("rajapalayam")
    )