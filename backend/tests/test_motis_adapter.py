from app.adapters.motis import MotisJourneySource

# Real (trimmed) response shape captured from a live api.transitous.org call
# for a Hannover Hbf -> Hamburg Hbf search.
ITINERARY = {
    "duration": 5280,
    "transfers": 0,
    "startTime": "2026-09-21T08:12:00Z",
    "endTime": "2026-09-21T09:40:00Z",
    "legs": [
        {
            "mode": "WALK",
            "from": {"name": "START"},
            "to": {"name": "Hannover Hauptbahnhof"},
            "startTime": "2026-09-21T08:12:00Z",
            "endTime": "2026-09-21T08:18:00Z",
        },
        {
            "mode": "HIGHSPEED_RAIL",
            "from": {"name": "Hannover Hauptbahnhof"},
            "to": {"name": "Hamburg Hbf"},
            "startTime": "2026-09-21T08:18:00Z",
            "endTime": "2026-09-21T09:38:00Z",
            "routeShortName": "ICE 76",
            "headsign": "Hamburg Hbf",
            "agencyName": "DB Fernverkehr AG",
        },
    ],
}


def test_to_record_maps_real_motis_shape():
    record = MotisJourneySource._to_record(ITINERARY)

    assert record.duration_minutes == 88
    assert record.transfers == 0
    assert record.price_amount is None  # transitous has no fare feed loaded
    assert record.price_currency is None
    assert len(record.legs) == 2

    walk, transit = record.legs
    assert walk.mode == "WALK"
    assert transit.mode == "HIGHSPEED_RAIL"
    assert transit.line_name == "ICE 76"
    assert transit.operator == "DB Fernverkehr AG"
    assert transit.origin_name == "Hannover Hauptbahnhof"
    assert transit.destination_name == "Hamburg Hbf"


def test_to_leg_falls_back_to_display_name_when_no_route_short_name():
    leg = {
        "mode": "REGIONAL_RAIL",
        "from": {"name": "A"},
        "to": {"name": "B"},
        "startTime": "2026-09-21T08:00:00Z",
        "endTime": "2026-09-21T08:30:00Z",
        "displayName": "RE 4",
    }
    result = MotisJourneySource._to_leg(leg)
    assert result.line_name == "RE 4"
