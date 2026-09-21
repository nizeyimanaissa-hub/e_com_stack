from app.adapters.stada import StaDaStationSource

# Real (trimmed) response shape captured from a live StaDa call. Frozen here
# as a regression test: the docs said "riL100Identifiers"/"geographicCoordinate",
# the live API actually returns "ril100Identifiers"/"geographicCoordinates" --
# this exact drift broke the adapter once (see README's Phase 2 notes).
FRANKFURT_HBF = {
    "number": 1866,
    "name": "Frankfurt (Main) Hbf",
    "federalState": "Hessen",
    "evaNumbers": [
        {
            "number": 8000105,
            "geographicCoordinates": {"type": "Point", "coordinates": [8.66282825, 50.1066819]},
            "isMain": True,
        },
        {
            "number": 8098105,
            "geographicCoordinates": {"type": "Point", "coordinates": [8.6625612, 50.1071101]},
            "isMain": False,
        },
    ],
    "ril100Identifiers": [
        {"rilIdentifier": "FF", "isMain": True},
        {"rilIdentifier": "FFT", "isMain": False},
    ],
}


def test_to_record_maps_real_stada_shape():
    record = StaDaStationSource._to_record(FRANKFURT_HBF)

    assert record.eva_id == 8000105  # the isMain=True eva number, not just the first one
    assert record.name == "Frankfurt (Main) Hbf"
    assert record.ds100 == "FF"  # the isMain=True ril100 identifier
    assert record.lat == 50.1066819
    assert record.lon == 8.66282825
    assert record.federal_state == "Hessen"


def test_to_record_falls_back_when_nothing_flagged_as_main():
    item = {
        "number": 123,
        "name": "Some Station",
        "federalState": "Bayern",
        "evaNumbers": [{"number": 8000999, "geographicCoordinates": {"coordinates": [11.0, 48.0]}}],
        "ril100Identifiers": [{"rilIdentifier": "XYZ"}],
    }
    record = StaDaStationSource._to_record(item)
    assert record.eva_id == 8000999
    assert record.ds100 == "XYZ"


def test_to_record_handles_missing_coordinates_and_ril100():
    item = {"number": 456, "name": "No Extras", "federalState": None, "evaNumbers": [], "ril100Identifiers": []}
    record = StaDaStationSource._to_record(item)
    assert record.eva_id == 456
    assert record.lat is None
    assert record.lon is None
    assert record.ds100 is None
