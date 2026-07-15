"""
Configuration for Transport Service

All API endpoints and headers are centralized here so they can
be reused throughout the project.
"""

from dataclasses import dataclass
import uuid


@dataclass
class IxigoConfig:

    # ----------------------------
    # API URLs
    # ----------------------------

    STATION_API = (
        "https://www.ixigo.com/action/content/trainstation"
    )

    TRAIN_API = (
        "https://ixigotrainsapi.confirmtkt.com/api/v1/trains/search"
    )

    AVAILABILITY_API = (
        "https://ixigotrainsapi.confirmtkt.com/api/v1/availability/fetchAvailability"
    )

    # ----------------------------
    # Headers
    # ----------------------------

    STATION_HEADERS = {
        "Accept": "*/*",
        "ApiKey": "ixiweb!2$",
        "ClientId": "ixiweb",
        "DeviceId": uuid.uuid4().hex,
        "Uuid": uuid.uuid4().hex,
        "IxiSrc": "ixiweb",
        "Referer": "https://www.ixigo.com/train-stations",
        "Origin": "https://www.ixigo.com",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest"
    }

    TRAIN_HEADERS = {
        "Accept": "*/*",
        "ApiKey": "iximweb!2$",
        "ClientId": "iximweb",
        "AppVersion": "200",
        "DeviceId": uuid.uuid4().hex,
        "Uuid": uuid.uuid4().hex,
        "IxiSrc": "iximweb",
        "Referer": "https://www.ixigo.com/",
        "Origin": "https://www.ixigo.com",
        "User-Agent": "Mozilla/5.0"
    }


config = IxigoConfig()