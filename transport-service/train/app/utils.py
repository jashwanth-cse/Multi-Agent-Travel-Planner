"""
Utility functions for the Transport Service.

Contains reusable helper functions for parsing.
"""

import re
from typing import Dict, Optional


# ---------------------------------------------------
# Station Helpers
# ---------------------------------------------------

def parse_station(station_text: str) -> Optional[Dict[str, str]]:
    """
    Converts 'Rajapalayam (RJPM)' into:
    {
        "station_name": "Rajapalayam",
        "station_code": "RJPM"
    }
    """
    match = re.match(r"^(.*?)\s*\((.*?)\)$", station_text)

    if not match:
        return None

    return {
        "station_name": match.group(1).strip(),
        "station_code": match.group(2).strip()
    }