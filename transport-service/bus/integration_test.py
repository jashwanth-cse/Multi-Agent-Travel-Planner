"""
integration_test.py
-------------------
Phase 4 integration test.

Verifies:
  Rajapalayam → Chennai  →  497 → 123  →  RedBus results  →  structured response

Run from bus/ directory:
    python integration_test.py
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

import requests

BASE = "http://localhost:8001"


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def check(label, r, expect_status=200):
    ok = r.status_code == expect_status
    mark = "✅" if ok else "❌"
    print(f"\n{mark} [{r.status_code}] {label}")
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:300]}

    if not ok:
        print(f"   Body: {json.dumps(body, indent=2)[:400]}")
    return body, ok


# ─── 1. Health ────────────────────────────────────────────────────────────────
separator("HEALTH CHECK")
r = requests.get(f"{BASE}/health")
print(f"  {r.json()}")

# ─── 2. Resolver unit verification ───────────────────────────────────────────
separator("RESOLVER UNIT — Rajapalayam → Chennai")
from resolver.redbus_city import RedbusCityResolver

resolver = RedbusCityResolver()
result = resolver.resolve("Rajapalayam", "Chennai")
print(f"  source_name      : {result['source_name']}")
print(f"  source_id        : {result['source_id']}")
print(f"  destination_name : {result['destination_name']}")
print(f"  destination_id   : {result['destination_id']}")

assert result["source_id"]      == 497, f"Expected 497, got {result['source_id']}"
assert result["destination_id"] == 123, f"Expected 123, got {result['destination_id']}"
print("\n  ✅  Rajapalayam=497  Chennai=123  CONFIRMED")

# ─── 3. Full pipeline via HTTP API ───────────────────────────────────────────
separator("FULL API PIPELINE — Rajapalayam → Chennai → 21-Aug-2026")
r = requests.get(f"{BASE}/api/v1/buses/search", params={
    "source":       "Rajapalayam",
    "destination":  "Chennai",
    "journey_date": "21-Aug-2026",
    "limit":        3,
    "offset":       0,
})
body, ok = check("GET /api/v1/buses/search  source=Rajapalayam&destination=Chennai", r)

if ok and body.get("success"):
    data = body["data"]
    print(f"\n  source       : {data.get('source')}")
    print(f"  destination  : {data.get('destination')}")
    print(f"  total_buses  : {data.get('total_buses')}")
    print(f"  returned     : {len(data.get('buses', []))}")

    if data.get("buses"):
        b = data["buses"][0]
        print(f"\n  First bus:")
        print(f"    operator     : {b.get('operator_name')}")
        print(f"    bus_type     : {b.get('bus_type')}")
        print(f"    departure    : {b.get('departure_time')}")
        print(f"    arrival      : {b.get('arrival_time')}")
        print(f"    duration     : {b.get('duration')}")
        print(f"    min_fare     : {b.get('minimum_fare')}")
        print(f"    avail_seats  : {b.get('available_seats')}")
        print(f"    amenities    : {b.get('amenities')}")

# ─── 4. Error cases ───────────────────────────────────────────────────────────
separator("ERROR CASES")

# Missing params → 422
r = requests.get(f"{BASE}/api/v1/buses/search", params={"source": "Rajapalayam"})
check("Missing destination → 400/422", r, expect_status=400)

# Invalid city → 404
r = requests.get(f"{BASE}/api/v1/buses/search", params={
    "source": "NotARealCity12345",
    "destination": "AlsoFake99999",
    "journey_date": "21-Aug-2026",
})
check("Invalid city names → 404", r, expect_status=404)

separator("DONE")
print("\n  Phase 4 integration test complete.")
