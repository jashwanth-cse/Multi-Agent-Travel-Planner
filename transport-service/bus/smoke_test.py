"""
smoke_test.py
-------------
Smoke test for the Phase 2 RedBus provider.
Run from the bus/ directory:
    python smoke_test.py <from_city_id> <to_city_id> <doj>

Example:
    python smoke_test.py 122455 122474 21-Aug-2026
"""
import sys
import json
import logging
import os

# Make provider importable from bus/ root
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

from provider.redbus import RedbusProvider, RedbusProviderError

def main():
    if len(sys.argv) < 4:
        print("Usage: python smoke_test.py <from_city> <to_city> <doj>")
        print("Eg:    python smoke_test.py 122455 122474 21-Aug-2026")
        sys.exit(1)

    from_city = int(sys.argv[1])
    to_city   = int(sys.argv[2])
    doj       = sys.argv[3]

    print(f"\nSmoke test: {from_city} -> {to_city}  {doj}\n")

    provider = RedbusProvider()

    try:
        result = provider.search(from_city=from_city, to_city=to_city, doj=doj)
    except RedbusProviderError as exc:
        print(f"PROVIDER ERROR: {exc}")
        sys.exit(1)

    print(f"total_buses : {result['total_buses']}")

    if result["buses"]:
        first = result["buses"][0]
        print(f"\nFirst bus:")
        print(f"  operator      : {first['operator_name']}")
        print(f"  service       : {first['service_name']}")
        print(f"  bus_type      : {first['bus_type']}")
        print(f"  departure     : {first['departure_time']}")
        print(f"  arrival       : {first['arrival_time']}")
        print(f"  duration_min  : {first['duration_minutes']}")
        print(f"  min_fare      : {first['minimum_fare']}")
        print(f"  avail_seats   : {first['available_seats']}")
        print(f"  rating        : {first['rating']}")
        print(f"  live_tracking : {first['live_tracking']}")
        print(f"  boarding_pt   : {first['boarding_point']}")
        print(f"  dropping_pt   : {first['dropping_point']}")

        # Save parsed output
        with open("smoke_parsed.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("\nFull parsed output saved to smoke_parsed.json")
    else:
        print("No buses found for this route/date.")

if __name__ == "__main__":
    main()
