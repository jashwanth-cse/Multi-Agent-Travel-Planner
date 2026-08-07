# RedBus Bus Search — Phase 1

Standalone Python scripts for endpoint verification, reverse engineering, and parsing.

**No FastAPI. No Pydantic. No API routes.**

---

## Folder Structure

```
bus/
├── config.py          Endpoint URL, query param defaults, constants
├── headers.py         Browser-exact request headers
├── cookies.py         Browser cookies (populate before first run)
├── filters.py         Request body (filter JSON)
├── client.py          HTTP client — makes the request
├── parser.py          Extracts useful fields from the raw response
├── test_search.py     CLI test runner
└── README.md          This file
```

---

## Prerequisites

```bash
pip install requests
```

---

## Quick Start

```bash
cd transport-service/bus

python test_search.py <from_city_id> <to_city_id> <journey_date>
```

### Example

```bash
python test_search.py 122455 122474 28-Jul-2026
```

> `journey_date` must be in `DD-Mon-YYYY` format (e.g. `28-Jul-2026`).

---

## Output

| File | Contents |
|---|---|
| `response_raw.json` | Full unmodified API response (for debugging) |
| `response_parsed.json` | Clean extracted fields only (for inspection) |

The terminal also prints:

```
  ✓  Request successful
  Status       : HTTP 200
  Response size: 142,312 bytes
  Time taken   : 843.21 ms
  Total buses  : 38

  Operator                      Bus Type               Departure    Arrival      Duration    Min Fare    Seats    Rating
  ────────────────────────────  ─────────────────────  ───────────  ───────────  ──────────  ──────────  ───────  ───────
  Orange Travels                AC Sleeper (2+1)       22:00        06:30        510         850.0       24       4.2
  ...
```

---

## Updating Cookies

1. Open `https://www.redbus.in` in Chrome → **DevTools → Network** tab.
2. Perform a bus search.
3. Click the `searchResults` request → **Headers → Request Headers → Cookie**.
4. Copy the full cookie string and paste into `cookies.py`.

---

## Updating Headers

Edit `headers.py` directly. The file contains every header as a plain dict key.

---

## How to Find City IDs

City IDs can be discovered by inspecting the `/rpw/api/search/city` autocomplete endpoint in DevTools while typing a city name in the RedBus search box. The `id` field in the response is the `fromCity` / `toCity` value.

---

## Phase 1 Goals

- [x] Working Python client
- [x] Successful request to the RedBus endpoint
- [x] Parser extracting only useful fields
- [x] `response_raw.json` for debugging
- [x] `response_parsed.json` for inspection
