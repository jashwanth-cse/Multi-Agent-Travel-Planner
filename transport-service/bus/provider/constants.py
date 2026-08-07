"""
constants.py
------------
All static values for the RedBus provider.

Nothing is hardcoded anywhere else. If you need to change an endpoint,
a header, or a default parameter, this is the only file to edit.
"""

# ── Endpoints ─────────────────────────────────────────────────────────────────
REDBUS_HOME_URL   = "https://www.redbus.in"
REDBUS_SEARCH_URL = "https://www.redbus.in/rpw/api/searchResults"

# ── Logo base URL (prepend to operatorLogoPath) ───────────────────────────────
LOGO_BASE_URL = "https://origin-st.redbus.in/buslogos/country/"

# ── Default query parameters ──────────────────────────────────────────────────
# These are appended to the URL for every search request.
DEFAULT_QUERY_PARAMS: dict = {
    "limit":           10,
    "offset":          0,
    "meta":            "true",
    "groupId":         0,
    "sectionId":       0,
    "sort":            0,
    "sortOrder":       0,
    "from":            "initialLoad",
    "getUuid":         "true",
    "bT":              1,
    "clearLMBFilter":  "undefined",
    "isFilterApplied": "false",
}

# ── Payload template ──────────────────────────────────────────────────────────
# Sent as the JSON body with every POST request.
DEFAULT_PAYLOAD: dict = {
    "appliedFilterCount": 0,
    "onlyShow":           [],
    "dt":                 [],
    "SeaterType":         [],
    "AcType":             [],
    "travelsList":        [],
    "amtList":            [],
    "bpList":             [],
    "dpList":             [],
    "CampaignFilter":     [],
    "at":                 [],
    "persuasionList":     [],
    "bpIdentifier":       [],
    "dpIdentifier":       [],
    "bcf":                [],
    "opBusTypeFilterList":[],
    "priceRange":         [],
    "RouteIds":           [],
    "bpKeys":             [],
    "dpKeys":             [],
    "streaksFilter":      [],
    "preRouteFilters":    None,
}

# ── Request headers ───────────────────────────────────────────────────────────
# curl_cffi handles TLS fingerprinting; we only override the application headers.
REQUEST_HEADERS: dict = {
    "accept":           "application/json, text/plain, */*",
    "accept-language":  "en-IN,en;q=0.9",
    "content-type":     "application/json",
    "origin":           "https://www.redbus.in",
    "referer":          "https://www.redbus.in/",
    "x-requested-with": "XMLHttpRequest",
}

# ── Timeouts (seconds) ────────────────────────────────────────────────────────
WARMUP_TIMEOUT = 20   # Homepage warm-up
SEARCH_TIMEOUT = 30   # Search request

# ── Session refresh triggers ──────────────────────────────────────────────────
# HTTP status codes that indicate an expired or invalid session.
SESSION_EXPIRED_CODES = {401, 403, 429}
