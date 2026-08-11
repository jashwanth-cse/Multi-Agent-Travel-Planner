"""
tests/test_availability_enrichment.py
---------------------------------------
Tests for the live availability enrichment layer in TrainService.

Run from transport-service/train/:
    python -m pytest tests/test_availability_enrichment.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from app.services.train_service import TrainService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_class(name: str, availability: str = "", fare: int = 150) -> dict:
    """Build a minimal parsed class dict."""
    return {
        "travel_class": name,
        "fare": fare,
        "availability": availability,
        "prediction": 0,
        "bookable": True,
        "availability_source": "cached" if availability.strip() else "pending",
    }


def _make_train(train_no: str, from_code: str, to_code: str, classes: list) -> dict:
    """Build a minimal parsed train dict."""
    return {
        "train_number": train_no,
        "train_name": f"Train {train_no}",
        "train_type": "EXP",
        "from": {"code": from_code, "name": "Source"},
        "to": {"code": to_code, "name": "Dest"},
        "departure_time": "08:00",
        "arrival_time": "12:00",
        "duration_minutes": 240,
        "duration": "4h 0m",
        "distance": 300,
        "running_days": ["Mon", "Wed", "Fri"],
        "rating": 4.0,
        "has_pantry": False,
        "lowest_fare": 150,
        "recommended_class": None,
        "classes": classes,
    }


LIVE_SUCCESS = {
    "success": True,
    "message": "Live availability fetched",
    "data": {
        "train_number": "16102",
        "travel_class": "SL",
        "quota": "GN",
        "availability": "AVL 15",
        "booking_status": "AVAILABLE",
        "prediction": 95,
        "fare": 130,
        "total_fare": 167,
        "booking_enabled": True,
        "last_updated": "2026-08-11T22:17:48.735",
        "next_available_dates": [],
    },
}

LIVE_FAILURE = {"success": False, "message": "Timeout", "data": None}


# ── Test 1: Cached availability exists → live NOT called ─────────────────────

def test_cached_availability_skips_live():
    """If availability is non-empty, live endpoint must NOT be called."""
    trains = [_make_train("16102", "RJPM", "SVKS", [
        _make_class("SL", "AVL 22"),
    ])]
    svc = TrainService.__new__(TrainService)

    with patch("app.services.train_service._availability_service") as mock_avl:
        svc._enrich_availability(trains, "26-08-2026", "GN", None)
        mock_avl.fetch_availability.assert_not_called()

    assert trains[0]["classes"][0]["availability"] == "AVL 22"
    assert trains[0]["classes"][0]["availability_source"] == "cached"


# ── Test 2: Empty availability → live IS called with correct params ──────────

def test_empty_availability_calls_live_with_correct_params():
    """If availability is empty, live must be called with the correct params."""
    trains = [_make_train("16102", "RJPM", "SVKS", [
        _make_class("SL", ""),
    ])]
    svc = TrainService.__new__(TrainService)

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.return_value = LIVE_SUCCESS
        svc._enrich_availability(trains, "26-08-2026", "GN", None)
        mock_avl.fetch_availability.assert_called_once_with(
            train_no="16102",
            source="RJPM",
            destination="SVKS",
            travel_class="SL",
            date="26-08-2026",
            quota="GN",
        )

    assert trains[0]["classes"][0]["availability"] == "AVL 15"
    assert trains[0]["classes"][0]["availability_source"] == "live"
    assert trains[0]["classes"][0]["prediction"] == 95
    assert trains[0]["classes"][0]["bookable"] is True


# ── Test 3: Multiple classes with empty availability ─────────────────────────

def test_multiple_missing_classes_each_get_live_request():
    """Each class with missing availability gets its own live request."""
    trains = [_make_train("16102", "RJPM", "SVKS", [
        _make_class("SL", ""),
        _make_class("3A", ""),
        _make_class("2A", "AVL 5"),  # Already cached — should NOT call live
    ])]
    svc = TrainService.__new__(TrainService)

    sl_result = {**LIVE_SUCCESS, "data": {**LIVE_SUCCESS["data"], "travel_class": "SL"}}
    thr_a_result = {**LIVE_SUCCESS, "data": {**LIVE_SUCCESS["data"], "travel_class": "3A", "availability": "WL 3"}}

    def side_effect(train_no, source, destination, travel_class, date, quota):
        if travel_class == "SL":
            return sl_result
        if travel_class == "3A":
            return thr_a_result
        return LIVE_FAILURE

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.side_effect = side_effect
        svc._enrich_availability(trains, "26-08-2026", "GN", None)
        assert mock_avl.fetch_availability.call_count == 2

    classes = {c["travel_class"]: c for c in trains[0]["classes"]}
    assert classes["SL"]["availability_source"] == "live"
    assert classes["3A"]["availability_source"] == "live"
    assert classes["3A"]["availability"] == "WL 3"
    assert classes["2A"]["availability_source"] == "cached"
    assert classes["2A"]["availability"] == "AVL 5"


# ── Test 4: Live API fails → search still succeeds ───────────────────────────

def test_live_api_failure_does_not_abort_search():
    """A live fetch failure marks availability_source='unavailable' but search continues."""
    trains = [_make_train("16102", "RJPM", "SVKS", [
        _make_class("SL", ""),
    ])]
    svc = TrainService.__new__(TrainService)

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.return_value = LIVE_FAILURE
        svc._enrich_availability(trains, "26-08-2026", "GN", None)

    cls = trains[0]["classes"][0]
    assert cls["availability_source"] == "unavailable"
    assert cls["bookable"] is False


# ── Test 5: travel_class=SL → only SL enriched ───────────────────────────────

def test_class_filter_limits_enrichment_to_target_class():
    """With travel_class=SL, only SL gets enriched; other classes skipped."""
    trains = [_make_train("16102", "RJPM", "SVKS", [
        _make_class("SL", ""),
        _make_class("3A", ""),
    ])]
    svc = TrainService.__new__(TrainService)

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.return_value = LIVE_SUCCESS
        svc._enrich_availability(trains, "26-08-2026", "GN", "SL")
        assert mock_avl.fetch_availability.call_count == 1
        call_kwargs = mock_avl.fetch_availability.call_args
        assert call_kwargs.kwargs.get("travel_class") == "SL"


# ── Test 6: Recommendation runs AFTER enrichment ─────────────────────────────

def test_recommendation_uses_enriched_availability():
    """
    recommended_class must reflect the live availability, not the pre-enrichment state.
    """
    svc = TrainService.__new__(TrainService)

    # SL starts empty → will get AVL 15 from live
    # 3A starts with REGRET → stays REGRET
    classes_before = [
        _make_class("SL", ""),
        _make_class("3A", "REGRET"),
    ]

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.return_value = LIVE_SUCCESS
        trains = [_make_train("16102", "RJPM", "SVKS", classes_before)]
        svc._enrich_availability(trains, "26-08-2026", "GN", None)

    # Now compute recommendation AFTER enrichment (as the service does)
    enriched_classes = trains[0]["classes"]
    recommended = TrainService._recommend_class(enriched_classes)

    # SL has AVL 15 — should be recommended over REGRET 3A
    assert recommended is not None
    assert recommended["travel_class"] == "SL"
    assert recommended["availability_source"] == "live"


# ── Test 7: Station codes — from/to code used, NOT station name ──────────────

def test_enrichment_uses_from_to_code_not_name():
    """Verify that source/destination are taken from train['from']['code'] / train['to']['code']."""
    trains = [_make_train("16102", "RJPM", "SVKS", [
        _make_class("SL", ""),
    ])]
    # Deliberately set different name to catch any name-based bug
    trains[0]["from"]["name"] = "Rajapalayam"
    trains[0]["to"]["name"]   = "Shencottai"

    svc = TrainService.__new__(TrainService)

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.return_value = LIVE_SUCCESS
        svc._enrich_availability(trains, "26-08-2026", "GN", None)
        call_kwargs = mock_avl.fetch_availability.call_args.kwargs
        assert call_kwargs["source"]      == "RJPM"      # code, not name
        assert call_kwargs["destination"] == "SVKS"      # code, not name


# ── Test 8: Original journey date passed unchanged ───────────────────────────

def test_original_journey_date_passed_to_availability():
    """The journey date must be forwarded to the availability call exactly as given."""
    trains = [_make_train("16102", "RJPM", "SVKS", [_make_class("SL", "")])]
    svc = TrainService.__new__(TrainService)

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.return_value = LIVE_SUCCESS
        svc._enrich_availability(trains, "26-08-2026", "GN", None)
        assert mock_avl.fetch_availability.call_args.kwargs["date"] == "26-08-2026"


# ── Test 9: Deduplication — same key not fetched twice ───────────────────────

def test_duplicate_key_not_fetched_twice():
    """Two trains with the same number+codes+class should result in only 1 live call."""
    cls_a = _make_class("SL", "")
    cls_b = _make_class("SL", "")
    trains = [
        _make_train("16102", "RJPM", "SVKS", [cls_a]),
        _make_train("16102", "RJPM", "SVKS", [cls_b]),
    ]
    svc = TrainService.__new__(TrainService)

    with patch("app.services.train_service._availability_service") as mock_avl:
        mock_avl.fetch_availability.return_value = LIVE_SUCCESS
        svc._enrich_availability(trains, "26-08-2026", "GN", None)
        assert mock_avl.fetch_availability.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
